# src/api.py
import os
from dotenv import load_dotenv
import litellm

load_dotenv()

API_BASE = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
API_KEY  = os.getenv("THUCCHIEN_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
DEFAULT_TEMP  = float(os.getenv("TEMPERATURE", "1.0"))

# set the API base ON the client
litellm.api_base = API_BASE

def chat_completions(messages, model=None, temperature=None):
    resp = litellm.completion(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=DEFAULT_TEMP if temperature is None else temperature,
        api_key=API_KEY,
        api_base=API_BASE,                     # per-call too (explicit)
        custom_llm_provider="openai",          # 👈 force OpenAI-compatible route
    )
    content = getattr(resp.choices[0].message, "content", str(resp))
    return {"raw": resp, "content": content}
