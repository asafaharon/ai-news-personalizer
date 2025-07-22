from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
import os

from backend.routers import auth, users, profile, preferences, news , favorites

app = FastAPI()

# ✅ mount static only if directory exists
static_dir = "static"
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"⚠️ תיקיית סטטיק לא קיימת: {static_dir} — דילוג על טעינה")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profile.router)
app.include_router(preferences.router)
app.include_router(news.router)
app.include_router(favorites.router)

@app.get("/loading", response_class=HTMLResponse)
async def loading(request: Request):
    return templates.TemplateResponse("loading.html", {"request": request})


# ✅ נתיב הבית הראשי
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    print("🏠 נטען דף הבית מתוך main.py")
    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": {"full_name": "משתמש הדגמה"}
    })

@app.exception_handler(StarletteHTTPException)
async def redirect_unauthorized(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        return RedirectResponse("/login")
    return HTMLResponse(f"שגיאה {exc.status_code}", status_code=exc.status_code)

# ✅ אפשרות להריץ ישירות main.py
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8081))
    print(f"🚀 מריץ ישירות main.py על פורט {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
