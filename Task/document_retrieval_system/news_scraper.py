import requests
from bs4 import BeautifulSoup
from database import Database

db = Database()

def scrape_news():
    url = "https://news.ycombinator.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    articles = soup.find_all("a", class_="storylink")
    for article in articles[:10]:  # Limit to top 10 articles
        content = article.get_text()
        db.insert_document(content)
