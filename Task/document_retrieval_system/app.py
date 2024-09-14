from fastapi import FastAPI, HTTPException, Request, Query, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import time
import logging
from database import Database
from cache import cache_results, get_cached_result
from news_scraper import scrape_news
import redis
import json
import torch
from transformers import BertTokenizer, BertModel

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Database and Redis
db = Database()
redis_cache = redis.Redis(host='localhost', port=6379, db=0)

# Initialize BERT
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

# Background task for scraping news articles on startup
@app.on_event("startup")
async def start_scraping():
    scrape_news()

@app.get("/health")
async def health_check():
    return {"status": "active"}

@app.get("/search")
async def search(
    request: Request, 
    text: str, 
    search_by: str = Query("title", enum=["title", "content", "full-text"]),
    top_k: int = 5, 
    threshold: float = 0.7,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    page_size: int = 10,
    re_rank: bool = False
):
    start_time = time.time()
    user_id = request.headers.get('user_id')

    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id header")

    # Check user rate limit
    if db.is_rate_limited(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        raise HTTPException(status_code=429, detail="Too many requests")

    # Check if the result is cached
    cached_result = get_cached_result(text)
    if cached_result:
        db.update_user_frequency(user_id)
        return {"results": cached_result, "inference_time": time.time() - start_time}

    # Prepare date range filtering
    date_filter = None
    if start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            date_filter = {'start_date': start_date_obj, 'end_date': end_date_obj}
        except ValueError:
            logger.error("Invalid date format provided")
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Perform search in MongoDB
    results = db.search_documents(text, top_k, threshold, search_by, date_filter)

    # Re-rank results using a custom algorithm (optional)
    if re_rank:
        results = re_rank_documents(results)

    # Cache the result for future queries
    cache_results(text, str(results))

    # Pagination: Return only results for the requested page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_results = results[start_idx:end_idx]

    # Update user frequency
    db.update_user_frequency(user_id)

    return {
        "results": paginated_results,
        "page": page,
        "total_results": len(results),
        "inference_time": time.time() - start_time
    }

def re_rank_documents(results):
    """Re-rank documents based on a custom algorithm"""
    return sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)

def get_bert_embedding(text):
    """Generate BERT embedding for a given text"""
    inputs = tokenizer(text, return_tensors='pt')
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1)

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Shutting down application")
