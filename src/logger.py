import json
from datetime import datetime
from .paths import LOGS_DIR

def log_json(event: dict) -> str:
    stamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
    fp = LOGS_DIR / f"{stamp}.json"
    fp.write_text(json.dumps(event, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(fp)
