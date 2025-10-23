from InquirerPy import inquirer
from InquirerPy.separator import Separator
from src.paths import ensure_all_dirs
from src.conversations import list_conversations, create_conversation, load_conversation, append_message
from src.api import chat_completions
from src.logger import log_json
import os
from dotenv import load_dotenv
from src.gui import launch

load_dotenv()

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

AVAILABLE_MODELS = [
    {"name": "Gemini 2.5 Pro", "value": "gemini-2.5-pro"},
    {"name": "Gemini 2.5 Flash", "value": "gemini-2.5-flash"},
    {"name": "Veo 3", "value": "veo 3"},
    {"name": "Imagen 4 (Google Vertex AI)", "value": "imagen-4"},
    {"name": "Gemini 2.5 Flash Image Preview", "value": "gemini-2.5-flash-image-preview"},
    {"name": "Gemini 2.5 Flash Preview TTS", "value": "gemini-2.5-flash-preview-tts"},
    {"name": "Gemini 2.5 Pro Preview TTS", "value": "gemini-2.5-pro-preview-tts"},
]

def pick_conversation():
    convs = list_conversations()
    choices = [("➕ Create new conversation", "__new__")]
    for c in convs:
        label = f"🗂  {c['name']} — {c.get('updatedAt', c['createdAt'])}"
        choices.append((label, c["id"]))
    choices.extend([Separator(), ("🚪 Exit", "__exit__")])

    sel = inquirer.select(message="Choose conversation:", choices=choices, default=choices[0][1]).execute()
    if sel == "__exit__":
        return None
    if sel == "__new__":
        return create_conversation()
    return load_conversation(sel)

def pick_api():
    apis = [("Chat Completions (/chat/completions)", "chat")]
    return inquirer.select(message="Choose API:", choices=apis).execute()

def pick_model():
    return inquirer.select(message="Choose AI model:", choices=[(m["name"], m["value"]) for m in AVAILABLE_MODELS], default=DEFAULT_MODEL).execute()

def chat_loop(conv: dict, selected_model: str):
    print(f"\n💬 Using: {conv['name']} (id: {conv['id']}) with model: {selected_model}")
    print("Type /exit to return to menu.\n")
    while True:
        prompt = inquirer.text(message="You:").execute()
        if not prompt or prompt.strip() == "/exit":
            break

        append_message(conv, "user", prompt)
        try:
            start = __import__("time").time()
            result = chat_completions([{"role": m["role"], "content": m["content"]} for m in conv["messages"]], model=selected_model)
            content = result["content"]
            append_message(conv, "assistant", content)

            log_path = log_json({
                "type": "chat.completions",
                "conversationId": conv["id"],
                "request": {"messages": [{"role": m["role"], "content": m["content"]} for m in conv["messages"][:-1]]},
                "response": result["raw"],
                "latency_ms": int((__import__("time").time() - start) * 1000),
            })

            print(f"\n🤖 Assistant:\n{content}\n")
            print(f"🗒  Log: {log_path}\n")
        except Exception as e:
            log_path = log_json({
                "type": "chat.completions.error",
                "conversationId": conv["id"],
                "error": {"message": str(e)},
            })
            print(f"❌ Error calling API. Details logged at: {log_path}\n")


def main():
    launch()

if __name__ == "__main__":
    main()
