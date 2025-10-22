# Thực Chiến AI – Python CLI

Python CLI to manage conversations and call docs.thucchien.ai APIs.  
Currently supports **/chat/completions**, structured to add the other 8 APIs.

## Setup
```bash
git clone <repo> thucchien-ai-cli-py
cd thucchien-ai-cli-py
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # fill THUCCHIEN_API_KEY (and optional overrides)
python -m src.app
```

## Features

- `.env` secrets with `python-dotenv`
- `logs/` auto-written JSON logs per request
- `data/conversations/` one JSON per conversation
- Arrow-key CLI (`InquirerPy`): pick conversation, pick API, type message
- Simple to extend: add more endpoints in `src/api.py` and another branch in the menu


---

## How to extend to all 9 APIs
- Create a function per endpoint in `src/api.py` (e.g., `embeddings()`, `images_generate()`, etc.) following the `chat_completions()` pattern.
- In `src/app.py`, add them to `pick_api()` and build a tiny loop to gather parameters, then call and log.

If you want, I can drop in stub functions for the other 8 endpoints so you only fill
