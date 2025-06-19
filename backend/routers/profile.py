from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.schemas.profile import ProfilePreferences
from backend.schemas.news import FilteredNewsResult, NewsArticle, NewsSource
from backend.routers.auth import get_current_user
from backend.db.mongo import db
from backend.models.user import user_helper
from datetime import datetime
from pathlib import Path
import requests
import openai
import os
from backend.auth.security import verify_password, get_password_hash

from typing import List               # <-- ודא שהייבוא הזה נמצא בראש הקובץ
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Annotated   # למעלה בקובץ
from typing import List               # <-- ודא שהייבוא הזה נמצא בראש הקובץ
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
# ... שאר הייבוא כפי שהיה ...
router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"
openai.api_key = OPENAI_API_KEY

def get_openai_summary(text: str, lang: str = "en") -> str:
    system_prompt = {
        "he": "אתה מסכם חדשות בעברית בפשטות ובאופן מעניין.",
        "fr": "Tu résumes les actualités en français de manière claire et intéressante.",
        "es": "Resumes las noticias en español de forma clara y atractiva.",
        "en": "You summarize news articles in clear and engaging English.",
    }.get(lang, "You summarize news articles in clear and engaging English.")

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Summarize this article:\n\n{text}"},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Error in summary with AI" if lang == "he" else "AI summary error"


# backend/routers/profile.py
@router.post("/me/preferences")
async def update_my_preferences(
    preferences: ProfilePreferences,
    current_user: dict = Depends(get_current_user),
):
    # Force English (or drop the field entirely)
    preferences.language = "en"

    result = db["users"].update_one(
        {"email": current_user["email"]},
        {"$set": {"preferences": preferences.dict()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Preferences updated", "data": preferences}

# backend/routers/profile.py
@router.post("/profile", response_class=HTMLResponse)
async def save_preferences(
    request: Request,
    topics: Annotated[list[str] | None, Form()] = None,
    article_count: Annotated[int, Form(...)] = ...,
    user = Depends(get_current_user),
):
    """Stores topics + article_count; language is hard-coded to 'en'."""
    if not topics:
        return templates.TemplateResponse(
            "profile.html",
            {"request": request,
             "user": user,
             "error": "Please select at least one topic."},
            status_code=400,
        )

    if isinstance(topics, str):
        topics = [topics]

    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "preferences": {
                "topics": topics,
                "article_count": article_count,
            },
            "preferred_language": "en",     # <- קבוע
            "article_count": article_count,
        }},
    )

    return RedirectResponse("/loading", status_code=302)
# backend/routers/profile.py
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(get_current_user)):
    print("🔍 dashboard(): התחלנו")

    user_doc = await db["users"].find_one({"_id": user["_id"]})
    if not user_doc:
        print("❌ לא נמצא משתמש")
        return RedirectResponse("/login")

    print("👤 user_doc:", user_doc)

    prefs = user_doc.get("preferences", {})
    if not prefs or not prefs.get("topics"):
        print("⚠️ אין העדפות שמורות")
        return RedirectResponse("/profile")

    query = " OR ".join(prefs["topics"])
    page_size = int(prefs.get("article_count", 10))

    if not NEWS_API_KEY:
        print("❌ חסר NEWS_API_KEY")
        raise HTTPException(500, detail="Missing NEWS_API_KEY")

    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": page_size,
    }

    try:
        resp = requests.get(NEWS_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print("❌ שגיאה ב-NewsAPI:", e)
        raise HTTPException(502, detail=f"News API error: {str(e)}")

    articles = []
    for a in data.get("articles", []):
        full_text = a.get("content") or a.get("description") or a.get("title", "")
        try:
            summary = get_openai_summary(full_text)
        except Exception as e:
            print("❌ שגיאה בתקציר עם OpenAI:", e)
            summary = "תקציר לא זמין"

        articles.append({
            "title": a.get("title", "No Title"),
            "source": a.get("source", {}).get("name", "Unknown"),
            "published": a.get("publishedAt", ""),
            "url": a.get("url", "#"),
            "summary": summary,
        })

    print("✅ מציגים תבנית dashboard")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user_doc,
        "summaries": articles,
        "preferences": prefs,
    })


@router.get("/profile/edit", response_class=HTMLResponse)
async def edit_profile_form(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("edit_profile.html", {
        "request": request,
        "user": user
    })


@router.post("/profile/edit", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    full_name: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...),
    user=Depends(get_current_user)
):
    user_doc = await db["users"].find_one({"_id": user["_id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(current_password, user_doc["password"]):
        return templates.TemplateResponse("edit_profile.html", {
            "request": request,
            "user": user,
            "error": "Current password is incorrect."
        })

    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "full_name": full_name,
            "password": get_password_hash(new_password)
        }}
    )

    return RedirectResponse("/dashboard", status_code=302)
@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user = Depends(get_current_user)):
    # שולפים את המשתמש המלא (כבר יש לכם קוד דומה)
    user_doc = await db["users"].find_one({"_id": user["_id"]})

    # מכינים רשימת topics שכבר שמורים (ריק אם אין)
    selected_topics = user_doc.get("preferences", {}).get("topics", [])

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user_doc,
            "selected_topics": selected_topics,   # ← נשלח לתבנית
        },
    )