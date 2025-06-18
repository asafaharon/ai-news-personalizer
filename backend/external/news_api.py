import httpx
from backend.core.config import NEWS_API_KEY

async def fetch_news_by_topics(topics: list[str]):
    articles = []

    async with httpx.AsyncClient() as client:
        for topic in topics:
            url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={NEWS_API_KEY}"
            response = await client.get(url)
            data = response.json()
            articles += data.get("articles", [])

    return articles
