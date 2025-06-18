# backend/db/mongo.py

import os
from motor.motor_asyncio import AsyncIOMotorClient
from backend.core.config import MONGODB_URI, DATABASE_NAME

# בדיקת תקינות משתנים
if not MONGODB_URI:
    raise RuntimeError("❌ MONGODB_URI not set in environment variables")

if not DATABASE_NAME:
    raise RuntimeError("❌ DATABASE_NAME not set in environment variables")

# התחברות למסד
try:
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    print(f"✅ Connected to MongoDB database: {DATABASE_NAME}")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    raise
