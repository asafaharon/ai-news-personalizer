# backend/db/mongo.py

import os
from motor.motor_asyncio import AsyncIOMotorClient
from backend.core.config import MONGODB_URI, DATABASE_NAME

# Check environment variables
if not MONGODB_URI:
    raise RuntimeError("[ERROR] MONGODB_URI not set in environment variables")

if not DATABASE_NAME:
    raise RuntimeError("[ERROR] DATABASE_NAME not set in environment variables")
# Database connection
try:
    # Improved connection settings for MongoDB Atlas
    client = AsyncIOMotorClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=10000,  # Reduced timeout
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        retryWrites=True,
        w='majority'
    )
    db = client[DATABASE_NAME]
    print(f"[OK] Connected to MongoDB database: {DATABASE_NAME}")
    
    # Test the connection immediately
    async def test_connection():
        try:
            await client.admin.command('ping')
            print("[OK] MongoDB connection test successful")
        except Exception as e:
            print(f"[ERROR] MongoDB connection test failed: {e}")
    
    # Note: Connection test will happen when first database operation occurs
    
except Exception as e:
    print("[ERROR] MongoDB Atlas connection failed:", e)
    print("[INFO] Using fallback configuration...")
    
    # Create a simpler connection without some Atlas-specific options
    try:
        # Simplified connection for troubleshooting
        simple_uri = MONGODB_URI.replace('&ssl_cert_reqs=CERT_NONE&tlsInsecure=true', '')
        client = AsyncIOMotorClient(simple_uri, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]
        print(f"[OK] Connected to MongoDB with simplified configuration: {DATABASE_NAME}")
    except Exception as e2:
        print(f"[ERROR] Simplified connection also failed: {e2}")
        raise RuntimeError("Cannot connect to MongoDB. Please check your connection string and network.")
