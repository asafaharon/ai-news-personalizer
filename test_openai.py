# test_openai.py

from openai import OpenAI
from backend.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def ask_openai(prompt: str) -> str:
    """שולח שאלה ל־OpenAI ומחזיר תשובה פשוטה"""
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-4o",  # או gpt-4
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"שגיאה: {str(e)}"

if __name__ == "__main__":
    question = input("מה ברצונך לשאול את OpenAI? ")
    answer = ask_openai(question)
    print("תשובה:\n", answer)
