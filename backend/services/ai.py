# backend/services/ai.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.routers.auth import get_current_user
from openai import OpenAI
import os
import redis.asyncio as redis
from backend.core.config import REDIS_URL, OPENAI_API_KEY

router = APIRouter()
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


class AIRequest(BaseModel):
    question: str


class AIResponse(BaseModel):
    answer: str


redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.post("/ai/ask", response_model=AIResponse)
def ask_openai(
    payload: AIRequest,
    current_user: dict = Depends(get_current_user)
):
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI not configured")
        
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "אתה עוזר אינטיליגנטי בעברית."},
                {"role": "user", "content": payload.question},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return {"answer": response.choices[0].message.content.strip()}
    except Exception as e:
        print(f"❌ OpenAI Error in ai service: {e}")
        raise HTTPException(status_code=500, detail=f"OpenAI Error: {str(e)}")
