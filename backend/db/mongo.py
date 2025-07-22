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
    client = AsyncIOMotorClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    db = client[DATABASE_NAME]
    print(f"✅ Connected to MongoDB database: {DATABASE_NAME}")
except Exception as e:
    print("❌ MongoDB Atlas connection failed:", e)
    print("🔄 Attempting local MongoDB connection...")
    try:
        # Fallback to local MongoDB
        local_uri = "mongodb://localhost:27017"
        client = AsyncIOMotorClient(local_uri)
        db = client[DATABASE_NAME]
        print(f"✅ Connected to local MongoDB database: {DATABASE_NAME}")
    except Exception as local_e:
        print("❌ Local MongoDB connection also failed:", local_e)
        print("⚠️  Using mock database for development...")
        # Create a simple in-memory mock for development
        class MockDB:
            def __init__(self):
                self.collections = {}
            
            def __getitem__(self, name):
                if name not in self.collections:
                    self.collections[name] = MockCollection()
                return self.collections[name]
        
        class MockCollection:
            def __init__(self):
                self.data = []
            
            async def find_one(self, query):
                return None  # No users in mock DB
            
            async def insert_one(self, doc):
                self.data.append(doc)
                return type('InsertResult', (), {'inserted_id': 'mock_id'})()
                
            async def find(self, query=None):
                return self.data
        
        db = MockDB()
        print("📝 Using mock database - login will not work, but app will start")
