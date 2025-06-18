# backend/routers/auth.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from backend.auth.security import get_current_user

from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from datetime import timedelta
from bson import ObjectId
from backend.db.mongo import db
from backend.models.user import user_helper
from backend.auth.security import create_access_token, verify_token

from pathlib import Path
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()
    user_record = await db["users"].find_one({"email": email})

    if not user_record:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "אימייל לא נמצא במערכת"
        })

    if not pwd_context.verify(password, user_record["password"]):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "סיסמה שגויה"
        })

    token = create_access_token(data={"sub": str(user_record["_id"])}, expires_delta=timedelta(hours=1))
    response = RedirectResponse(url="/loading", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False
    )
    return response




@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()
    user_exists = await db["users"].find_one({"email": email})
    if user_exists:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "אימייל זה כבר רשום"
        })

    hashed_password = pwd_context.hash(password)
    new_user = {
        "full_name": full_name,
        "email": email,
        "password": hashed_password,
        "preferences": {"categories": [], "topics": [], "num_articles": 10}
    }
    result = await db["users"].insert_one(new_user)

    token = create_access_token(data={"sub": str(result.inserted_id)}, expires_delta=timedelta(hours=1))
    response = RedirectResponse(url="/loading", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user=Depends(get_current_user)):
    """
    מציג את טופס העריכה של תחומי העניין כאשר התחומים הקיימים של המשתמש כבר מסומנים,
    וכן את השפה וכמות הכתבות שנשמרו בפעם הקודמת.
    """
    # ❶ שליפת המסמך המלא של המשתמש (צריך את ההעדפות)
    user_doc = await db["users"].find_one({"_id": ObjectId(user["_id"])})

    # אם מדובר במשתמש חדש לגמרי – ניצור מבנה ריק כדי שה-template לא יקרוס
    prefs = user_doc.get("preferences", {"topics": [], "categories": []})
    preferred_language = user_doc.get("language", user_doc.get("preferred_language", "en"))
    article_count = int(user_doc.get("article_count", 10))

    context = {
        "request": request,
        "user":    user_doc,
        "preferences": prefs,
        "preferred_language": preferred_language,
        "article_count": article_count,
    }
    return templates.TemplateResponse("profile.html", context)


