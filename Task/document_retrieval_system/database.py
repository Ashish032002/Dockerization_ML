from pymongo import MongoClient, TEXT
from datetime import datetime
import redis
import json
import torch
from transformers import BertTokenizer, BertModel

# Initialize Redis connection for caching
redis_cache = redis.Redis(host='localhost', port=6379, db=0)

# Initialize BERT tokenizer and model for embedding generation
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

class Database:
    def __init__(self):
        # Connect to the MongoDB server
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["document_retrieval_system"]

        # Collections for documents and users
        self.documents = self.db["documents"]
        self.users = self.db["users"]

        # Ensure indexes are created for optimized search
        self.documents.create_index([("content", TEXT), ("title", TEXT), ("date", 1)])

    def insert_document(self, title, content):
        """Insert a document into MongoDB with BERT embeddings"""
        # Generate embeddings for the document content
        embedding = self.get_bert_embedding(content)

        # Insert the document along with the embedding and current date
        self.documents.insert_one({
            "title": title,
            "content": content,
            "embedding": embedding.tolist(),  # Store embedding as a list
            "date": datetime.now()
        })

    def get_bert_embedding(self, text):
        """Generate BERT embedding for a given text"""
        inputs = tokenizer(text, return_tensors="pt")
        outputs = model(**inputs)
        return outputs.last_hidden_state.mean(dim=1)

    def update_user_frequency(self, user_id):
        """Update API request frequency for a user"""
        user = self.users.find_one({"user_id": user_id})
        if user:
            self.users.update_one({"user_id": user_id}, {"$inc": {"request_count": 1}})
        else:
            self.users.insert_one({"user_id": user_id, "request_count": 1})

    def is_rate_limited(self, user_id):
        """Check if a user has exceeded the request limit"""
        user = self.users.find_one({"user_id": user_id})
        return user and user["request_count"] >= 5

    def search_documents(self, text, top_k=5, threshold=0.7, search_by="content", date_filter=None):
        """Perform advanced search with optional filters and re-ranking"""

        # Construct query
        query = {}
        if search_by == "full-text":
            query["$text"] = {"$search": text}
        else:
            query[search_by] = {"$regex": text, "$options": "i"}  # Case-insensitive regex

        # Apply date filter if present
        if date_filter:
            query["date"] = {"$gte": date_filter['start_date'], "$lte": date_filter['end_date']}

        # Fetch documents from MongoDB
        results = self.documents.find(query)

        # If embeddings are stored, perform similarity-based filtering
        embedding = self.get_bert_embedding(text)
        ranked_results = []
        for doc in results:
            doc_embedding = torch.tensor(doc["embedding"])
            similarity_score = torch.nn.functional.cosine_similarity(embedding, doc_embedding).item()
            if similarity_score >= threshold:
                doc["relevance_score"] = similarity_score
                ranked_results.append(doc)

        # Sort documents by relevance score and limit the result to top_k
        ranked_results = sorted(ranked_results, key=lambda x: x["relevance_score"], reverse=True)

        return ranked_results[:top_k]

    def cache_result(self, cache_key, results):
        """Cache search results in Redis"""
        redis_cache.set(cache_key, json.dumps(results), ex=3600)  # Cache with 1-hour expiration

    def get_cached_result(self, cache_key):
        """Retrieve cached search results from Redis"""
        cached_data = redis_cache.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        return None
