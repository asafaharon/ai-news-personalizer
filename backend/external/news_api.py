import httpx
from backend.core.config import NEWS_API_KEY

async def fetch_news_by_topics(topics: list[str]):
    articles = []

    async with httpx.AsyncClient() as client:
        for topic in topics:
            # Using NewsData.io API instead of NewsAPI.org
            url = f"https://newsdata.io/api/1/news?apikey={NEWS_API_KEY}&q={topic}&language=en"
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                # NewsData.io returns results in 'results' field, not 'articles'
                newsdata_articles = data.get("results", [])
                
                # Convert NewsData.io format to match our expected format
                for article in newsdata_articles:
                    articles.append({
                        "title": article.get("title", ""),
                        "url": article.get("link", ""),
                        "source": {"name": article.get("source_id", "Unknown")},
                        "publishedAt": article.get("pubDate", ""),
                        "description": article.get("description", "")
                    })
            except Exception as e:
                print(f"❌ שגיאה בטעינת חדשות עבור {topic}: {e}")
                continue

    return articles
