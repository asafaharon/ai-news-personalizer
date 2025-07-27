"""
Security module handling authentication, password hashing, and JWT token management.

This module provides core security functions for user authentication including:
- Password hashing and verification using bcrypt
- JWT token creation and verification  
- User authentication middleware
- Session management via HTTP cookies
"""
from bson import ObjectId
from fastapi import Request, HTTPException, Depends
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from backend.db.mongo import db

SECRET_KEY = "AI_PERSONAL_NEWS_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """
    Verify a plain text password against its hashed version.
    
    Args:
        plain_password (str): The plain text password to verify
        hashed_password (str): The stored bcrypt hash to compare against
        
    Returns:
        bool: True if password matches hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """
    Generate a bcrypt hash from a plain text password.
    
    Args:
        password (str): Plain text password to hash
        
    Returns:
        str: Bcrypt hashed password suitable for database storage
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token with user data and expiration.
    
    Args:
        data (dict): User data to encode in token (typically contains user ID)
        expires_delta (Optional[timedelta]): Custom expiration time, defaults to ACCESS_TOKEN_EXPIRE_MINUTES
        
    Returns:
        str: Encoded JWT token string for authentication
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token (str): JWT token string to verify and decode
        
    Returns:
        Optional[dict]: Decoded token payload if valid, None if invalid or expired
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

async def get_current_user(request: Request):
    """
    Extract and validate current user from request authentication cookie.
    
    Args:
        request (Request): FastAPI request object containing authentication cookie
        
    Returns:
        dict: Complete user document from database or cached test user data
        
    Raises:
        HTTPException: 401 for missing/invalid tokens, 400 for invalid user ID format,
                      404 for user not found in database
        
    Note:
        Includes special handling for test user during development
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user ID")

    # Handle test user scenario: return cached user data for development/testing
    if user_id == "test_user_id":
        user = {
            "_id": "test_user_id",
            "name": "asaf",
            "email": "asafasaf16@gmail.com", 
            "password": "$2b$12$XYReGERF2WVbnu6U81Xopud4zxL9HkI57hi2S9AhAb/2..gD8/oG.",  # "password"
            "preferences": {
                "topics": ["Mobile", "Football", "Space", "Climate", "Chemistry", "Music", "Security", "Food"],
                "article_count": 13
            },
            "created_at": "2025-07-22T13:52:05.138000",
            "article_count": 13,
            "preferred_language": "en",
            "favorites": [
                {
                    "url": "https://slickdeals.net/f/18468184-redragon-mechanical-wireless-keyboard-k556-se-rgb-34-61-k673-pro-75-35-82-k686-pro-se-98-keys-53-26-free-shipping",
                    "title": "Redragon K556 SE RGB LED Backlit Wired Mechanical Keyboard (Red Switch, Blue) $34.60 & More + Free Shipping",
                    "source": "Slickdeals.net",
                    "published": "2025-07-21T14:45:56Z"
                }
            ]
        }
    else:
        try:
            user = await db["users"].find_one({"_id": ObjectId(user_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid user ID format")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
