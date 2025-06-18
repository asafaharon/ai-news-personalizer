# backend/models/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from bson import ObjectId


class UserInDB(BaseModel):
    id: Optional[str] = Field(alias="_id")
    email: EmailStr
    hashed_password: str
    preferences: Optional[dict] = {
        "topics": [],
        "categories": []
    }


def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "preferences": user.get("preferences", {"topics": [], "categories": []})
    }
