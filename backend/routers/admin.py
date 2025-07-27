# backend/routers/admin.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from backend.db.mongo import db

router = APIRouter()

@router.delete("/admin/clear-users")
async def clear_all_users():
    """
    DANGER: This endpoint deletes ALL users from the database
    Only use for development/testing purposes
    """
    try:
        # Count users before deletion
        user_count = await db["users"].count_documents({})
        
        if user_count == 0:
            return JSONResponse(
                content={"message": "No users found to delete", "deleted_count": 0},
                status_code=200
            )
        
        # Delete all users
        result = await db["users"].delete_many({})
        
        return JSONResponse(
            content={
                "message": f"Successfully deleted all users",
                "deleted_count": result.deleted_count,
                "original_count": user_count
            },
            status_code=200
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting users: {str(e)}")

@router.get("/admin/user-count")
async def get_user_count():
    """Get the current number of users in the database"""
    try:
        count = await db["users"].count_documents({})
        return JSONResponse(
            content={"user_count": count},
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting users: {str(e)}")