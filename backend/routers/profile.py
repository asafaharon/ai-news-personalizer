from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.schemas.profile import ProfilePreferences
from backend.schemas.news import FilteredNewsResult, NewsArticle, NewsSource
from backend.routers.auth import get_current_user
from backend.db.mongo import db
from backend.models.user import user_helper
from datetime import datetime
from pathlib import Path
from typing import List, Annotated
import requests
import os
from backend.auth.security import verify_password, get_password_hash
from openai import OpenAI

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_URL = "https://newsdata.io/api/1/news"

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def get_openai_summary(text: str, lang: str = "en") -> str:
    if not openai_client:
        return "OpenAI not configured"
    
    # Check if content is meaningful
    if len(text.strip()) < 30:
        return "Not enough content to summarize"
    
    # Check for limited content indicators
    if "paid plans" in text.lower() or "premium content" in text.lower():
        return "Full content requires premium access - check original article"
    
    system_prompt = {
        "he": "אתה מסכם חדשות בעברית בפשטות ובאופן מעניין.",
        "fr": "Tu résumes les actualités en français de manière claire et intéressante.", 
        "es": "Resumes las noticias en español de forma clara y atractiva.",
        "en": "You are a news summarizer. Create a clear, engaging summary in 2-3 sentences. If the content is limited or incomplete, say 'Limited preview available - visit article for full details' instead of making up information.",
    }.get(lang, "You are a news summarizer. Create a clear, engaging summary in 2-3 sentences. If the content is limited or incomplete, say 'Limited preview available - visit article for full details' instead of making up information.")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Summarize this news content:\n\n{text[:1000]}"},
            ],
            temperature=0.3,  # Lower temperature for more factual summaries
            max_tokens=100,
        )
        summary = response.choices[0].message.content.strip()
        
        # Filter out unhelpful responses
        if "cannot provide" in summary.lower() or "sorry" in summary.lower():
            return "Limited preview available - visit article for full details"
            
        return summary
    except Exception as e:
        print(f"[ERROR] OpenAI Error: {e}")
        return "Summary unavailable - visit article for full details"


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
            "preferred_language": "en",
            "article_count": article_count,
        }},
    )

    # Build loading URL with parameters based on user preferences
    topics_str = ",".join(topics) if topics else ""
    loading_url = f"/loading?article_count={article_count}&topics={topics_str}"
    return RedirectResponse(loading_url, status_code=302)
# backend/routers/profile.py
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(get_current_user)):
    try:
        print("[DEBUG] Dashboard function started")
        print(f"[DEBUG] User object: {user}")

        # Check if user has email key
        if not user or "email" not in user:
            print("[ERROR] User object missing or no email")
            return RedirectResponse("/login")

        # Get user document from database
        user_doc = await db["users"].find_one({"_id": user["_id"]})
        if not user_doc:
            print("[ERROR] User not found in database")
            return RedirectResponse("/login")

        print("[DEBUG] user_doc:", user_doc)

        prefs = user_doc.get("preferences", {})
        if not prefs or not prefs.get("topics"):
            print("[WARNING] No preferences saved")
            return RedirectResponse("/profile")

        query = " OR ".join(prefs["topics"])
        page_size = int(prefs.get("article_count", 10))

        if not NEWS_API_KEY:
            print("[ERROR] Missing NEWS_API_KEY")
            raise HTTPException(500, detail="Missing NEWS_API_KEY")

        # NewsData.io API parameters
        params = {
            "q": query,
            "apikey": NEWS_API_KEY,  # NewsData.io uses 'apikey' not 'apiKey'
            "language": "en",
            "size": min(page_size, 10),  # NewsData.io uses 'size' not 'pageSize', max 10 for free tier
        }

        try:
            resp = requests.get(NEWS_API_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print("[ERROR] NewsAPI error:", e)
            raise HTTPException(502, detail=f"News API error: {str(e)}")

        articles = []
        # NewsData.io returns results in 'results' field, not 'articles'
        for a in data.get("results", []):
            # Get the best available text content
            title = a.get("title", "")
            description = a.get("description", "")
            content = a.get("content", "")
            
            # Combine available text, prioritizing description over content for free tier
            full_text = ""
            if description and len(description) > 50:
                full_text = f"{title}. {description}"
            elif content and len(content) > 50:
                full_text = f"{title}. {content}"
            else:
                full_text = title
                
            # Generate summary
            try:
                if len(full_text) > 30:  # Only summarize if we have enough content
                    summary = get_openai_summary(full_text)
                else:
                    summary = "Limited content available - visit link for full article"
            except Exception as e:
                print("[ERROR] OpenAI summary error:", e)
                summary = description[:200] + "..." if description else "Summary not available"

            articles.append({
                "title": title,
                "source": a.get("source_id", "Unknown"),  # NewsData.io uses 'source_id'
                "published": a.get("pubDate", ""),  # NewsData.io uses 'pubDate'
                "url": a.get("link", "#"),  # NewsData.io uses 'link'
                "summary": summary,
            })

        print("[OK] Rendering dashboard template")
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user_doc,
            "summaries": articles,
            "preferences": prefs,
            "favorites_count": len(user_doc.get("favorites", [])),  # Add favorites count
        })
    
    except Exception as e:
        print(f"[ERROR] Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


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