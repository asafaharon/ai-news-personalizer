import openai
from backend.core.config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY


# backend/utils/openai_client.py
def get_openai_summary(text: str) -> str:
    """
    Summarize a news article in clear, engaging English.
    Always returns English (portfolio version).
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You summarize news articles in concise, engaging English."},
                {"role": "user",
                 "content": f"Summarize this article:\n\n{text}"},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "AI summary error"
