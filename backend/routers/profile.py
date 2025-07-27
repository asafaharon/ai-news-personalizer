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
from bson import ObjectId
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
    """
    Generate AI-powered article summary using OpenAI GPT-3.5.
    
    Args:
        text (str): Article content to summarize
        lang (str): Target language for summary (default: "en")
        
    Returns:
        str: Generated summary or fallback message if processing fails
        
    Note:
        Falls back to standard messages if content is insufficient or API fails
    """
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
        
        # Filter out unhelpful AI responses
        if "cannot provide" in summary.lower() or "sorry" in summary.lower():
            return "Limited preview available - visit article for full details"
            
        return summary
    except Exception as e:
        print(f"[ERROR] OpenAI Error: {e}")
        return "Summary unavailable - visit article for full details"


@router.post("/me/preferences")
async def update_my_preferences(
    preferences: ProfilePreferences,
    current_user: dict = Depends(get_current_user),
):
    """
    Update user preferences via API endpoint.
    
    Args:
        preferences (ProfilePreferences): User preference data
        current_user (dict): Current authenticated user from dependency injection
        
    Returns:
        dict: Success message with updated preferences
        
    Raises:
        HTTPException: 404 if user not found in database
    """
    # Enforce English language setting
    preferences.language = "en"

    result = db["users"].update_one(
        {"email": current_user["email"]},
        {"$set": {"preferences": preferences.dict()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Preferences updated", "data": preferences}

@router.post("/profile", response_class=HTMLResponse)
async def save_preferences(
    request: Request,
    topics: Annotated[list[str] | None, Form()] = None,
    article_count: Annotated[int, Form(...)] = ...,
    user = Depends(get_current_user),
):
    """
    Save user topic preferences and article count from profile form.
    
    Args:
        request (Request): FastAPI request object for template rendering
        topics (list[str] | None): Selected topic interests from form
        article_count (int): Number of articles to display per page
        user (dict): Current authenticated user from dependency injection
        
    Returns:
        RedirectResponse: Redirects to loading page with preferences
        TemplateResponse: Profile form with error if validation fails
        
    Note:
        Language preference is hardcoded to English ('en')
    """
    print(f"[DEBUG] Received topics: {topics}")
    print(f"[DEBUG] Topics type: {type(topics)}")
    print(f"[DEBUG] Number of topics: {len(topics) if topics else 0}")
    
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
    
    print(f"[DEBUG] Final topics to save: {topics}")
    print(f"[DEBUG] Final topics count: {len(topics)}")

    # Handle test user scenario: log preferences without database modification
    if user["_id"] == "test_user_id":
        print(f"[TEST USER] Would save topics: {topics}")
        print(f"[TEST USER] Would save article_count: {article_count}")
        # Test user data cannot be persisted to database
    else:
        await db["users"].update_one(
            {"_id": ObjectId(user["_id"])},
            {"$set": {
                "preferences": {
                    "topics": topics,
                    "article_count": article_count,
                },
                "preferred_language": "en",
                "article_count": article_count,
            }},
        )

    # Construct loading page URL with user preference parameters
    topics_str = ",".join(topics) if topics else ""
    loading_url = f"/loading?article_count={article_count}&topics={topics_str}"
    return RedirectResponse(loading_url, status_code=302)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(get_current_user)):
    """
    Display personalized news dashboard with user's preferred articles.
    
    Args:
        request (Request): FastAPI request object for template rendering
        user (dict): Current authenticated user from dependency injection
        
    Returns:
        TemplateResponse: Rendered dashboard.html with personalized news articles
        RedirectResponse: Redirects to login/profile if user invalid or no preferences
        
    Raises:
        HTTPException: 500 for dashboard errors, 502 for external API failures
    """
    try:
        print("[DEBUG] Dashboard function started")
        print(f"[DEBUG] User object: {user}")

        # Validate user authentication and required fields
        if not user or "email" not in user:
            print("[ERROR] User object missing or no email")
            return RedirectResponse("/login")

        # Retrieve complete user document from database
        # Handle test user scenario: use cached user data for development/testing
        if user["_id"] == "test_user_id":
            user_doc = user  # Use the test user object directly
            print("[DEBUG] Using test user data directly")
        else:
            try:
                user_doc = await db["users"].find_one({"_id": ObjectId(user["_id"])})
            except:
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
            # Extract best available content from API response
            title = a.get("title", "")
            description = a.get("description", "")
            content = a.get("content", "")
            
            # Combine available text content, prioritizing description over full content
            full_text = ""
            if description and len(description) > 50:
                full_text = f"{title}. {description}"
            elif content and len(content) > 50:
                full_text = f"{title}. {content}"
            else:
                full_text = title
                
            # Generate AI summary from available content
            try:
                if len(full_text) > 30:  # Minimum content threshold for AI processing
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