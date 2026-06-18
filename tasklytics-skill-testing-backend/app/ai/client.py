import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TOGETHER_API_KEY")

URL = "https://api.together.xyz/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def call_llm(prompt: str, temperature: float = 0.3, max_tokens: int = 400):
    """
    Modern Together ChatAPI call
    """

    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "You are a helpful productivity assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    response = requests.post(URL, headers=HEADERS, json=payload)

    if response.status_code != 200:
        return f"Error: {response.text}"

    data = response.json()

    return data["choices"][0]["message"]["content"]