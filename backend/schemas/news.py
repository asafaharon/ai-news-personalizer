from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime


class NewsSource(BaseModel):
    id: Optional[str]
    name: str


class NewsArticle(BaseModel):
    source: NewsSource
    author: Optional[str]
    title: str
    description: Optional[str]
    url: HttpUrl
    urlToImage: Optional[HttpUrl]
    publishedAt: datetime
    content: Optional[str]
    summary: Optional[str]  # ✅ נדרש עבור dashboard + /me/news


class FilteredNewsResult(BaseModel):
    total: int
    articles: List[NewsArticle]


class SummarizedArticle(BaseModel):
    original: NewsArticle
    summary: str


class SummarizedNewsResponse(BaseModel):
    summaries: List[SummarizedArticle]
