from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from backend.db.mongo import db
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/favorites", tags=["Favorites"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

@router.post("/remove")
async def remove_favorite(
    url: str = Form(...),
    user=Depends(get_current_user),
):
    """
    מסיר כתבה אחת (לפי ה-URL שלה) משדה favorites של המשתמש
    """
    res = await db["users"].update_one(
        {"_id": user["_id"]},
        {"$pull": {"favorites": {"url": url}}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "User not found")

    # חזרה לרשימת המועדפים
    return RedirectResponse("/favorites", status_code=302)

@router.post("/add")
async def add_favorite(
    url: str = Form(...),
    title: str = Form(...),
    source: str = Form(...),
    published: str = Form(...),
    user=Depends(get_current_user),
):
    fav = {"url": url, "title": title, "source": source, "published": published}

    res = await db["users"].update_one(
        {"_id": user["_id"]},
        {"$addToSet": {"favorites": fav}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "User not found")

    return RedirectResponse("/dashboard", status_code=302)

@router.get("/", response_class=HTMLResponse)
async def view_favorites(request: Request, user=Depends(get_current_user)):
    user_doc = await db["users"].find_one({"_id": user["_id"]})
    favorites = user_doc.get("favorites", [])
    return templates.TemplateResponse("favorites.html", {
        "request": request,
        "user": user_doc,
        "favorites": favorites
    })
