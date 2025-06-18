# backend/schemas/profile.py
from pydantic import BaseModel
from typing import List


class ProfilePreferences(BaseModel):
    topics: List[str]
    categories: List[str]
    language: str = "en"  # ✅ חדש
