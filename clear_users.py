#!/usr/bin/env python3
"""
Script to clear all users from the AI News Personalizer database
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clear_all_users():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["ai_news_db"]

    try:
        # Count existing users
        user_count = await db["users"].count_documents({})
        print(f"Found {user_count} users in database")

        if user_count == 0:
            print("No users to delete")
            return

        # Ask for confirmation
        confirm = input(f"Are you sure you want to delete all {user_count} users? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled")
            return

        # Delete all users
        result = await db["users"].delete_many({})
        print(f"Successfully deleted {result.deleted_count} users")

        # Verify deletion
        remaining = await db["users"].count_documents({})
        print(f"Remaining users: {remaining}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(clear_all_users())