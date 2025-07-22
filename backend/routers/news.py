from typing import List
from datetime import datetime
import asyncio, os, httpx, re
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.auth.security import get_current_user
from backend.schemas.user import UserOut
from backend.schemas.news import (
    FilteredNewsResult, NewsArticle, NewsSource,
    SummarizedArticle, SummarizedNewsResponse
)
from backend.core.config import NEWS_API_KEY
from backend.utils.openai_client import get_openai_summary

router = APIRouter(prefix="/news", tags=["News"])
http_client = httpx.AsyncClient(timeout=10.0)

# --- סינון אם טקסט הוא באנגלית בלבד ---
def _looks_english(text: str) -> bool:
    return re.fullmatch(r"[a-zA-Z0-9\s\.,!?\"'\-:;()/@]+", text.strip()) is not None

# --- סינון כתבה לפי תחומי עניין ---
def _relevant_to_user(article: NewsArticle, interests: list[str]) -> bool:
    combined = f"{article.title} {article.description or ''} {article.content or ''}".lower()
    return any(term.lower() in combined for term in interests)

# --- המרה של raw dict מ-NewsAPI לכתבות ---
def _parse_articles(raw: dict, interests: list[str]) -> List[NewsArticle]:
    try:
        articles = []
        for a in raw.get("articles", []):
            combined = f"{a.get('title', '')} {a.get('description', '')}"
            if not _looks_english(combined):
                continue
            parsed = NewsArticle(
                source=NewsSource(**a["source"]),
                author=a.get("author"),
                title=a["title"],
                description=a.get("description"),
                url=a["url"],
                urlToImage=a.get("urlToImage"),
                publishedAt=datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00")),
                content=a.get("content"),
            )
            if _relevant_to_user(parsed, interests):
                articles.append(parsed)
        return articles
    except Exception:
        raise HTTPException(500, "Failed to parse news data")

# --- שליפת כתבות מה־API (ללא Cache) ---
async def _fetch_from_newsapi(query: str, language: str = "en", page_size: int = 10):
    url = (
        f"https://newsapi.org/v2/everything?"
        f"qInTitle={query}&language={language}&pageSize={page_size}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    )
    resp = await http_client.get(url)
    if resp.status_code != 200:
        raise HTTPException(502, "News API error")
    return resp.json()

# --- נקודת קצה לשליפת כתבות מותאמות אישית ---
@router.get("/", response_model=FilteredNewsResult)
async def fetch_news(
    topics: List[str] = Query(...),
    page_size: int = 10,
    current_user: UserOut = Depends(get_current_user)
):
    if not NEWS_API_KEY:
        raise HTTPException(500, "Missing News API key")

    language = current_user.get("preferred_language", "en")
    query = " OR ".join(topics)
    raw = await _fetch_from_newsapi(query, language, page_size)
    articles = _parse_articles(raw, topics)
    return FilteredNewsResult(total=len(articles), articles=articles)

# --- נקודת קצה לסיכום AI של כתבות ---
@router.get("/ai-summarized", response_model=SummarizedNewsResponse)
async def ai_summarize_news(
    topics: List[str] = Query(...),
    current_user: UserOut = Depends(get_current_user),
):
    language = current_user.get("preferred_language", "en")
    query = " OR ".join(topics)
    page_size = current_user.get("preferences", {}).get("num_articles", 10)

    raw = await _fetch_from_newsapi(query, language, page_size)
    articles = _parse_articles(raw, topics)
    top_articles = articles[:page_size]

    async def summarize(article: NewsArticle):
        summary = await get_openai_summary(
            article.title,
            article.description or article.content or "",
            lang=language
        )
        return SummarizedArticle(original=article, summary=summary)

    summaries = await asyncio.gather(*(summarize(a) for a in top_articles))
    return SummarizedNewsResponse(summaries=summaries)
