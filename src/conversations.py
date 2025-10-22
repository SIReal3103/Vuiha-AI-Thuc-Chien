import json
import time
import uuid
from pathlib import Path
from .paths import CONV_DIR, CONV_INDEX, ensure_all_dirs

ensure_all_dirs()

def _read_index():
    try:
        return json.loads(Path(CONV_INDEX).read_text(encoding="utf-8"))
    except Exception:
        return {"conversations": []}

def _write_index(idx):
    Path(CONV_INDEX).write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")

def list_conversations():
    idx = _read_index()
    idx["conversations"].sort(key=lambda c: c.get("updatedAt", 0), reverse=True)
    return idx["conversations"]

def create_conversation(name: str | None = None):
    ts = int(time.time() * 1000)
    conv_id = str(uuid.uuid4())
    conv = {
        "id": conv_id,
        "name": name or f"Conversation {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "createdAt": ts,
        "updatedAt": ts,
        "messages": []  # { role: "user"|"assistant"|"system", content: str, at: ms }
    }
    (CONV_DIR / f"{conv_id}.json").write_text(json.dumps(conv, indent=2, ensure_ascii=False), encoding="utf-8")

    idx = _read_index()
    idx["conversations"].append({"id": conv_id, "name": conv["name"], "createdAt": ts, "updatedAt": ts})
    _write_index(idx)
    return conv

def load_conversation(conv_id: str):
    p = CONV_DIR / f"{conv_id}.json"
    return json.loads(p.read_text(encoding="utf-8"))

def save_conversation(conv: dict):
    conv["updatedAt"] = int(time.time() * 1000)
    (CONV_DIR / f"{conv['id']}.json").write_text(json.dumps(conv, indent=2, ensure_ascii=False), encoding="utf-8")
    idx = _read_index()
    for it in idx["conversations"]:
        if it["id"] == conv["id"]:
            it["name"] = conv["name"]
            it["updatedAt"] = conv["updatedAt"]
            break
    _write_index(idx)

def append_message(conv: dict, role: str, content: str, message_type: str = "text"):
    """
    Append a message to the conversation.
    
    Args:
        conv (dict): The conversation object
        role (str): The role of the message sender (user, assistant, system)
        content (str): The content of the message
        message_type (str): The type of message (text, image)
    """
    message = {
        "role": role,
        "content": content,
        "at": int(time.time() * 1000),
        "type": message_type
    }
    conv["messages"].append(message)
    save_conversation(conv)


def append_image_message(conv: dict, role: str, content: str, image_data: bytes, filename: str = None):
    """
    Append an image message to the conversation.
    
    Args:
        conv (dict): The conversation object
        role (str): The role of the message sender (user, assistant)
        content (str): The text content associated with the image
        image_data (bytes): The image data in bytes
        filename (str): Optional filename for the image
    """
    import os
    import base64
    
    # Create images directory for this conversation if it doesn't exist
    conv_images_dir = Path(CONV_DIR) / conv["id"] / "images"
    conv_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate a filename if not provided
    if not filename:
        timestamp = int(time.time())
        filename = f"image_{timestamp}.png"
    
    # Save the image file
    image_path = conv_images_dir / filename
    with open(image_path, "wb") as f:
        f.write(image_data)
    
    # Create message with image reference
    message = {
        "role": role,
        "content": content,
        "at": int(time.time() * 1000),
        "type": "image",
        "image_path": str(image_path.relative_to(CONV_DIR.parent.parent)),  # Store relative path
        "filename": filename
    }
    
    conv["messages"].append(message)
    save_conversation(conv)
    
    return str(image_path)
