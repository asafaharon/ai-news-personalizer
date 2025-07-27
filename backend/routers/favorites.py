from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from backend.db.mongo import db
from backend.routers.auth import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/favorites", tags=["Favorites"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

@router.post("/remove")
async def remove_favorite(
    url: str = Form(...),
    user=Depends(get_current_user),
):
    """
    Remove a single article from user's favorites by URL.
    
    Args:
        url (str): The URL of the article to remove
        user (dict): Current authenticated user from dependency injection
        
    Returns:
        RedirectResponse: Redirects to favorites page after removal
        
    Raises:
        HTTPException: 404 if user not found in database
    """
    # Handle test user scenario: log action without database modification
    if user["_id"] == "test_user_id":
        print(f"[TEST USER] Would remove favorite with URL: {url}")
        return RedirectResponse("/favorites", status_code=302)
    
    try:
        user_id = ObjectId(user["_id"])
    except:
        user_id = user["_id"]
        
    res = await db["users"].update_one(
        {"_id": user_id},
        {"$pull": {"favorites": {"url": url}}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "User not found")

    # Redirect back to favorites list
    return RedirectResponse("/favorites", status_code=302)

@router.post("/add")
async def add_favorite(
    url: str = Form(...),
    title: str = Form(...),
    source: str = Form(...),
    published: str = Form(...),
    user=Depends(get_current_user),
):
    """
    Add an article to user's favorites collection.
    
    Args:
        url (str): Article URL
        title (str): Article title
        source (str): Article source/publisher
        published (str): Publication date
        user (dict): Current authenticated user from dependency injection
        
    Returns:
        RedirectResponse: Redirects to dashboard after adding favorite
        
    Raises:
        HTTPException: 404 if user not found in database
    """
    fav = {"url": url, "title": title, "source": source, "published": published}

    # Handle test user scenario: log action without database modification
    if user["_id"] == "test_user_id":
        print(f"[TEST USER] Would add favorite: {fav}")
        return RedirectResponse("/dashboard", status_code=302)
    
    try:
        user_id = ObjectId(user["_id"])
    except:
        user_id = user["_id"]

    res = await db["users"].update_one(
        {"_id": user_id},
        {"$addToSet": {"favorites": fav}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "User not found")

    return RedirectResponse("/dashboard", status_code=302)

@router.get("/", response_class=HTMLResponse)
async def view_favorites(request: Request, user=Depends(get_current_user)):
    """
    Display user's saved favorite articles.
    
    Args:
        request (Request): FastAPI request object for template rendering
        user (dict): Current authenticated user from dependency injection
        
    Returns:
        TemplateResponse: Rendered favorites.html template with user favorites
        RedirectResponse: Redirects to login if user not found
    """
    # Handle test user scenario: use cached user data for development/testing
    if user["_id"] == "test_user_id":
        user_doc = user  # Use the test user object directly
    else:
        try:
            user_doc = await db["users"].find_one({"_id": ObjectId(user["_id"])})
        except:
            user_doc = await db["users"].find_one({"_id": user["_id"]})
    
    if not user_doc:
        return RedirectResponse("/login")
        
    favorites = user_doc.get("favorites", [])
    return templates.TemplateResponse("favorites.html", {
        "request": request,
        "user": user_doc,
        "favorites": favorites
    })
