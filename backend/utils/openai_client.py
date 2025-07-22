from openai import OpenAI
from backend.core.config import OPENAI_API_KEY

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def get_openai_summary(text: str) -> str:
    """
    Summarize a news article in clear, engaging English.
    Always returns English (portfolio version).
    """
    if not openai_client:
        return "OpenAI not configured"
        
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You summarize news articles in concise, engaging English."},
                {"role": "user",
                 "content": f"Summarize this article in 2-3 sentences:\n\n{text[:1500]}"},
            ],
            temperature=0.7,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ OpenAI Error in utils: {e}")
        return f"AI summary error: {str(e)[:50]}..."
