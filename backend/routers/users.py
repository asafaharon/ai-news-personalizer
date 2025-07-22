# backend/routers/users.py

from fastapi import APIRouter, Depends
from backend.routers.auth import get_current_user
from backend.schemas.user import UserOut

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/test")
async def test_users():
    return {"message": "Users endpoint working"}


@router.get("/me", response_model=UserOut)
async def get_me(user=Depends(get_current_user)):
    return user
