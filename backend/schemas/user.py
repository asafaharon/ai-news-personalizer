# schemas/user.py

from pydantic import BaseModel, EmailStr
from typing import List, Optional

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class UserPreferences(BaseModel):
    topics: List[str]
    categories: List[str]
    num_articles: int = 10



class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr]
    topics: Optional[List[str]] = []
    categories: Optional[List[str]] = []

class UserCreate(BaseModel):
    """ מבנה נתונים להרשמה של משתמש חדש """
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """ מבנה נתונים להתחברות של משתמש """
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """ המידע שנשלח ללקוח אודות המשתמש """
    id: str
    email: EmailStr
    interests: List[str] = []


class Token(BaseModel):
    """ טוקן גישה שנשלח לאחר התחברות מוצלחת """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """ נתונים שמוצאים מתוך הטוקן """
    id: Optional[str] = None
