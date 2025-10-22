# src/api.py
import os
from dotenv import load_dotenv
import litellm

load_dotenv()

API_BASE = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
API_KEY = os.getenv("THUCCHIEN_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
DEFAULT_TEMP = float(os.getenv("TEMPERATURE", "1.0"))

# set the API base ON the client
litellm.api_base = API_BASE


def chat_completions(messages, model=None, temperature=None, use_web_search=False):
    """
    Call /chat/completions with optional web_search_options.
    If use_web_search=True, adds {"search_context_size": "medium"}.
    Otherwise, no web_search_options are sent.
    """
    kwargs = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": DEFAULT_TEMP if temperature is None else temperature,
        "api_key": API_KEY,
        "api_base": API_BASE,  # explicit
        "custom_llm_provider": "openai",  # force OpenAI-compatible route
    }

    # ✅ only include this if user toggled web search
    if use_web_search:
        kwargs["web_search_options"] = {"search_context_size": "medium"}

    resp = litellm.completion(**kwargs)
    content = getattr(resp.choices[0].message, "content", str(resp))

    return {"raw": resp, "content": content}
