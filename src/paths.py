import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
CONV_DIR = DATA_DIR / "conversations"
CONV_INDEX = DATA_DIR / "conversations.index.json"

def ensure_all_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    if not CONV_INDEX.exists():
        CONV_INDEX.write_text('{"conversations": []}', encoding="utf-8")
