# src/logger.py
import json
import base64
from datetime import datetime, date
from pathlib import Path
from typing import Any

from .paths import LOGS_DIR

# ---- Helpers to make any Python object JSON-serializable ----

def _is_primitive(x: Any) -> bool:
    return isinstance(x, (str, int, float, bool)) or x is None

def _safe_default(obj: Any):
    """
    Fallback for json.dumps(..., default=_safe_default).
    Converts unknown objects to a JSON-safe representation.
    """
    # Pydantic v2 (ModelResponse / BaseModel)
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()
        except Exception:
            pass

    # Pydantic v1 .dict()
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return obj.dict()
        except Exception:
            pass

    # Datetime / Date
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # bytes -> base64 (string)
    if isinstance(obj, (bytes, bytearray)):
        return base64.b64encode(obj).decode("ascii")

    # Exception -> tên + message
    if isinstance(obj, BaseException):
        return {
            "error_type": obj.__class__.__name__,
            "message": str(obj),
        }

    # Generic: try __dict__
    if hasattr(obj, "__dict__"):
        try:
            return {k: v for k, v in vars(obj).items()}
        except Exception:
            pass

    # Last resort: string
    return str(obj)


def _to_jsonable(obj: Any):
    """
    Recursively convert common containers to JSON-safe values.
    Uses _safe_default for unknown leaf objects.
    """
    if _is_primitive(obj):
        return obj

    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]

    # Let json.dumps with default handle the rest
    return obj


def log_json(event: dict) -> str:
    """
    Write an event dict to logs/<UTC-timestamp>.json in UTF-8.
    Automatically converts non-serializable objects (e.g., LiteLLM ModelResponse)
    into JSON-safe forms.
    Returns the file path (string).
    """
    # Ensure folder exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Timestamp filename (UTC)
    stamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    fp = LOGS_DIR / f"{stamp}.json"

    # Normalize event recursively first
    normalized = _to_jsonable(event)

    try:
        # json.dumps with default handler for any leftover complex objects
        fp.write_text(
            json.dumps(normalized, indent=2, ensure_ascii=False, default=_safe_default),
            encoding="utf-8",
        )
    except Exception as e:
        # If even fallback fails, write a minimal error log
        fallback = {
            "type": "logger.write_error",
            "at": datetime.utcnow().isoformat() + "Z",
            "error": {
                "type": e.__class__.__name__,
                "message": str(e),
            },
            "raw_event_str": str(event)[:5000],  # prevent huge dumps
        }
        fp.write_text(json.dumps(fallback, indent=2, ensure_ascii=False), encoding="utf-8")

    return str(fp)
