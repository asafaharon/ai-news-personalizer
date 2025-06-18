from motor.motor_asyncio import AsyncIOMotorClient
from backend.core.config import MONGODB_URI, DATABASE_NAME

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DATABASE_NAME]