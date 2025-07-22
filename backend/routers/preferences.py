from fastapi import APIRouter, Depends, HTTPException, status
from backend.schemas.user import UserPreferences
from backend.db.mongo import db
from backend.routers.auth import get_current_user
from pymongo.collection import ReturnDocument

router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"]
)

@router.get("/", response_model=UserPreferences)
def get_preferences(current_user: dict = Depends(get_current_user)):
    user = db.users.find_one({"_id": current_user["_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"preferences": user.get("preferences", [])}


@router.put("/", response_model=UserPreferences)
def update_preferences(preferences: UserPreferences, current_user: dict = Depends(get_current_user)):
    updated_user = db.users.find_one_and_update(
        {"_id": current_user["_id"]},
        {"$set": {"preferences": preferences.preferences}},
        return_document=ReturnDocument.AFTER
    )
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"preferences": updated_user.get("preferences", [])}