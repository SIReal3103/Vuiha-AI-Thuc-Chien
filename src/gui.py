# src/gui.py
import os
import json
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from .paths import ensure_all_dirs
from .conversations import (
    list_conversations,
    create_conversation,
    load_conversation,
    append_message,
)
from .api import chat_completions, generate_video_api_call, download_video_api_call
from .logger import log_json
import tempfile # For handling temporary video files
import webbrowser # For opening downloaded video

# ---- Model list / defaults ----
# Try to import from constants.py if you created it; otherwise fallback.
try:
    from .constants import AVAILABLE_MODELS, DEFAULT_MODEL
except Exception:
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
    AVAILABLE_MODELS = [
        {"name": "Gemini 2.5 Pro", "value": "gemini-2.5-pro"},
        {"name": "Gemini 2.5 Flash", "value": "gemini-2.5-flash"},
        {"name": "Veo 3", "value": "veo-3.0-generate-001"}, # Updated model name for video
        {"name": "Imagen 4 (Google Vertex AI)", "value": "imagen-4"},
        {"name": "Gemini 2.5 Flash Image Preview", "value": "gemini-2.5-flash-image-preview"},
        {"name": "Gemini 2.5 Flash Preview TTS", "value": "gemini-2.5-flash-preview-tts"},
        {"name": "Gemini 2.5 Pro Preview TTS", "value": "gemini-2.5-pro-preview-tts"},
    ]
    if DEFAULT_MODEL not in [m["value"] for m in AVAILABLE_MODELS]:
        AVAILABLE_MODELS.insert(0, {"name": f"Custom default ({DEFAULT_MODEL})", "value": DEFAULT_MODEL})


class ChatGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Thực Chiến AI – Chat GUI")
        self.geometry("1120x740")
        self.minsize(1000, 640)

        ensure_all_dirs()

        self.current_conv = None
        self.current_conv_id = None

        # ========== Layout split ==========
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left column (conversations)
        self.left = ttk.Frame(self, padding=10)
        self.left.grid(row=0, column=0, sticky="ns")
        ttk.Label(self.left, text="Conversations", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )

        self.conv_list = tk.Listbox(self.left, height=28, activestyle="dotbox")
        self.conv_list.grid(row=1, column=0, columnspan=2, sticky="nswe")
        self.left.grid_rowconfigure(1, weight=1)
        self.left.grid_columnconfigure(0, weight=1)

        btns = ttk.Frame(self.left)
        btns.grid(row=2, column=0, columnspan=2, sticky="we", pady=8)
        ttk.Button(btns, text="New", command=self.on_new_conv).pack(side="left")
        ttk.Button(btns, text="Refresh", command=self.refresh_convs).pack(side="left", padx=6)
        ttk.Button(btns, text="Open", command=self.on_open_conv).pack(side="left")

        # Right column (controls + chat)
        self.right = ttk.Frame(self, padding=10)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        # Topbar controls
        topbar = ttk.Frame(self.right)
        topbar.grid(row=0, column=0, sticky="we", pady=(0, 6))

        ttk.Label(topbar, text="API:").pack(side="left")
        self.api_var = tk.StringVar(value="Chat Completions (/chat/completions)")
        self.api_combo = ttk.Combobox(
            topbar,
            textvariable=self.api_var,
            state="readonly",
            values=["Chat Completions (/chat/completions)", "Video Generation"],
            width=34,
        )
        self.api_combo.pack(side="left", padx=(6, 12))
        self.api_combo.bind("<<ComboboxSelected>>", self.on_api_select)


        ttk.Label(topbar, text="Model:").pack(side="left")
        self.model_combo = ttk.Combobox(
            topbar, values=[m["value"] for m in AVAILABLE_MODELS], width=30
        )
        self.model_combo.set(DEFAULT_MODEL)
        self.model_combo.pack(side="left", padx=(6, 12))

        ttk.Label(topbar, text="Temp:").pack(side="left")
        self.temp_var = tk.DoubleVar(value=float(os.getenv("TEMPERATURE", "1.0")))
        self.temp_spin = ttk.Spinbox(
            topbar, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var, width=5
        )
        self.temp_spin.pack(side="left", padx=(6, 12))

        # Simple Web Search toggle (fixed "medium" context when on)
        self.ws_enabled = tk.BooleanVar(value=False)
        self.ws_check = ttk.Checkbutton(
            topbar, text="Use Web Search (context: medium)", variable=self.ws_enabled
        )
        self.ws_check.pack(side="left", padx=(12, 6))

        # API base indicator (from env)
        api_base = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
        ttk.Label(topbar, text=f"@ {api_base}", foreground="#666").pack(side="right")

        # Video generation parameters frame
        self.video_params_frame = ttk.Frame(self.right, padding=5)
        # self.video_params_frame.grid(row=0, column=0, sticky="we", pady=(0, 6)) # This will be managed by on_api_select

        ttk.Label(self.video_params_frame, text="Negative Prompt:").grid(row=0, column=0, sticky="w")
        self.negative_prompt_var = tk.StringVar(value="blurry, low quality")
        self.negative_prompt_entry = ttk.Entry(self.video_params_frame, textvariable=self.negative_prompt_var, width=40)
        self.negative_prompt_entry.grid(row=0, column=1, sticky="we", padx=(6, 12))

        ttk.Label(self.video_params_frame, text="Aspect Ratio:").grid(row=1, column=0, sticky="w")
        self.aspect_ratio_var = tk.StringVar(value="16:9")
        self.aspect_ratio_combo = ttk.Combobox(
            self.video_params_frame,
            textvariable=self.aspect_ratio_var,
            state="readonly",
            values=["16:9", "9:16", "1:1"],
            width=10,
        )
        self.aspect_ratio_combo.grid(row=1, column=1, sticky="we", padx=(6, 12))

        ttk.Label(self.video_params_frame, text="Resolution:").grid(row=2, column=0, sticky="w")
        self.resolution_var = tk.StringVar(value="720p")
        self.resolution_combo = ttk.Combobox(
            self.video_params_frame,
            textvariable=self.resolution_var,
            state="readonly",
            values=["720p", "1080p"],
            width=10,
        )
        self.resolution_combo.grid(row=2, column=1, sticky="we", padx=(6, 12))

        ttk.Label(self.video_params_frame, text="Person Generation:").grid(row=3, column=0, sticky="w")
        self.person_generation_var = tk.StringVar(value="allow_all")
        self.person_generation_combo = ttk.Combobox(
            self.video_params_frame,
            textvariable=self.person_generation_var,
            state="readonly",
            values=["allow_all", "deny_all"],
            width=15,
        )
        self.person_generation_combo.grid(row=3, column=1, sticky="we", padx=(6, 12))


        # Chat history
        self.history = ScrolledText(self.right, wrap="word", height=22, state="disabled")
        self.history.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        # Input area
        bottom = ttk.Frame(self.right)
        bottom.grid(row=2, column=0, sticky="we")
        bottom.grid_columnconfigure(0, weight=1)

        self.input_box = ScrolledText(bottom, wrap="word", height=5)
        self.input_box.grid(row=0, column=0, sticky="we")
        self.input_box.bind("<Control-Return>", self.on_send_event)

        actions = ttk.Frame(bottom)
        actions.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.send_btn = ttk.Button(actions, text="Send  (Ctrl+Enter)", command=self.on_send)
        self.send_btn.grid(row=0, column=0, sticky="we")

        # Status bar
        self.status = tk.StringVar(value="Ready.")
        statusbar = ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken")
        statusbar.grid(row=1, column=0, columnspan=2, sticky="we")

        # Load conversations
        self.refresh_convs()
        if self.conv_list.size() > 0:
            self.conv_list.selection_set(0)
            self.on_open_conv()

        # Initial API selection state
        self.on_api_select()

    def on_api_select(self, _event=None):
        selected_api = self.api_var.get()
        if selected_api == "Video Generation":
            self.ws_check.pack_forget() # Hide web search for video generation
            self.temp_spin.pack_forget() # Hide temperature for video generation
            self.video_params_frame.grid(row=0, column=0, sticky="we", pady=(0, 6))
            # Adjust model options for video generation
            self.model_combo.config(values=["veo-3.0-generate-001"])
            self.model_combo.set("veo-3.0-generate-001")
        else:
            self.video_params_frame.grid_forget()
            self.ws_check.pack(side="left", padx=(12, 6)) # Show web search
            self.temp_spin.pack(side="left", padx=(6, 12)) # Show temperature
            # Restore all models for chat completions
            self.model_combo.config(values=[m["value"] for m in AVAILABLE_MODELS])
            self.model_combo.set(DEFAULT_MODEL) # Reset to default chat model

    # ---------- Conversations ----------
    def refresh_convs(self):
        self.conv_list.delete(0, tk.END)
        convs = list_conversations()
        for c in convs:
            ts = c.get("updatedAt", c.get("createdAt"))
            label = f"{c['name']} — {ts}"
            self.conv_list.insert(tk.END, label)
        self.status.set(f"Loaded {self.conv_list.size()} conversation(s).")

    def on_new_conv(self):
        conv = create_conversation()
        self.status.set(f"Created: {conv['name']}")
        self.refresh_convs()
        if self.conv_list.size() > 0:
            self.conv_list.selection_clear(0, tk.END)
            self.conv_list.selection_set(0)
            self.on_open_conv()

    def on_open_conv(self):
        idx = self.conv_list.curselection()
        if not idx:
            self.status.set("Select a conversation first.")
            return
        convs = list_conversations()  # sorted desc
        item = convs[idx[0]]
        self.current_conv = load_conversation(item["id"])
        self.current_conv_id = item["id"]
        self.render_history()
        self.status.set(f"Opened: {self.current_conv['name']}")

    # ---------- Chat ----------
    def render_history(self):
        self.history.config(state="normal")
        self.history.delete("1.0", tk.END)
        if not self.current_conv:
            self.history.insert(tk.END, "No conversation selected.\n")
        else:
            for m in self.current_conv.get("messages", []):
                role = m["role"]
                content = m["content"]
                prefix = "You" if role == "user" else ("Assistant" if role == "assistant" else role)
                self.history.insert(tk.END, f"{prefix}:\n{content}\n\n")
        self.history.config(state="disabled")
        self.history.see(tk.END)

    def on_send_event(self, _evt):
        self.on_send()
        return "break"

    def on_send(self):
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
        text = self.input_box.get("1.0", tk.END).strip()
        if not text:
            return

        # clear input early
        self.input_box.delete("1.0", tk.END)

        # append user message + update UI
        append_message(self.current_conv, "user", text)
        self.render_history()

        # lock UI while calling API
        self.send_btn.configure(state="disabled")
        self.status.set("Calling API...")

        threading.Thread(target=self._call_api_threadsafe, daemon=True).start()

    def _call_api_threadsafe(self):
        start = time.time()
        selected_api = self.api_var.get()
        try:
            if selected_api == "Chat Completions (/chat/completions)":
                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in self.current_conv["messages"]
                ]
                selected_model = self.model_combo.get() or DEFAULT_MODEL
                temperature = float(self.temp_var.get())
                use_web_search = bool(self.ws_enabled.get())

                result = chat_completions(
                    messages=messages,
                    model=selected_model,
                    temperature=temperature,
                    use_web_search=use_web_search,  # <- only adds web_search_options when True
                )

                reply = result["content"] or "(empty response)"
                append_message(self.current_conv, "assistant", reply)

                # Comprehensive log (api + variables + response). No secrets included.
                api_base = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
                log_payload = {
                    "type": "api.call",
                    "api": "/chat/completions",
                    "conversationId": self.current_conv["id"],
                    "request": {
                        "api_base": api_base,
                        "model": selected_model,
                        "temperature": temperature,
                        "use_web_search": use_web_search,
                        "web_search_options": {"search_context_size": "medium"} if use_web_search else None,
                        "messages": messages,
                    },
                    "response": result["raw"],  # LiteLLM response (JSON-serializable)
                    "latency_ms": int((time.time() - start) * 1000),
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                log_path = log_json(log_payload)

                self._on_api_done(True, f"Done. Log: {log_path}")
            elif selected_api == "Video Generation":
                raw_input_text = self.input_box.get("1.0", tk.END).strip()
                
                # Default values from GUI controls
                prompt_str = raw_input_text
                selected_model = self.model_combo.get() or 'veo-3.0-generate-001'
                negative_prompt_val = self.negative_prompt_var.get()
                aspect_ratio_val = self.aspect_ratio_var.get()
                resolution_val = self.resolution_var.get()
                person_generation_val = self.person_generation_var.get()

                # Attempt to parse input as JSON
                try:
                    json_input = json.loads(raw_input_text)
                    if "prompt" in json_input:
                        prompt_str = json_input["prompt"]
                    if "negative_prompt" in json_input:
                        negative_prompt_val = json_input["negative_prompt"]
                    if "aspectRatio" in json_input:
                        aspect_ratio_val = json_input["aspectRatio"]
                    if "resolution" in json_input:
                        resolution_val = json_input["resolution"]
                    if "personGeneration" in json_input:
                        person_generation_val = json_input["personGeneration"]
                    # Other fields like style, duration, etc., are not directly supported by the API call
                    # and will be ignored for now.
                except json.JSONDecodeError:
                    # Not a JSON input, treat raw_input_text as the prompt string
                    pass

                if not prompt_str:
                    raise ValueError("Prompt is required for video generation.")

                self.status.set("Starting video generation...")
                video_result = generate_video_api_call(
                    prompt=prompt_str,
                    model=selected_model,
                    negative_prompt=negative_prompt_val,
                    aspect_ratio=aspect_ratio_val,
                    resolution=resolution_val,
                    person_generation=person_generation_val
                )
                video_id = video_result["video_id"]
                video_uri = video_result["video_uri"]

                # Download the video
                self.status.set(f"Video generated. Downloading video {video_id}...")
                video_content = download_video_api_call(video_id)

                # Save to a temporary file and provide a link
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4", mode="wb") as temp_video_file:
                    temp_video_file.write(video_content)
                    temp_video_path = temp_video_file.name

                reply = f"Video generated successfully! [Download Video]({temp_video_path}) [Open in Browser]({video_uri})"
                append_message(self.current_conv, "assistant", reply)

                log_payload = {
                    "type": "api.call",
                    "api": "Video Generation",
                    "conversationId": self.current_conv["id"],
                    "request": {
                        "prompt": prompt_str,
                        "model": selected_model,
                        "negativePrompt": negative_prompt_val,
                        "aspectRatio": aspect_ratio_val,
                        "resolution": resolution_val,
                        "personGeneration": person_generation_val,
                    },
                    "response": {"video_id": video_id, "video_uri": video_uri},
                    "latency_ms": int((time.time() - start) * 1000),
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                log_path = log_json(log_payload)

                self._on_api_done(True, f"Video generation complete. Log: {log_path}")
            else:
                self._on_api_done(False, "Unknown API selected.")

        except Exception as e:
            log_path = log_json({
                "type": "api.error",
                "api": selected_api,
                "conversationId": getattr(self.current_conv, "id", None),
                "error": {"message": str(e)},
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            self._on_api_done(False, f"Error: {e}. Logged at: {log_path}")

    def _on_api_done(self, success: bool, msg: str):
        self.after(0, self._finalize_ui_update, success, msg)

    def _finalize_ui_update(self, _success: bool, msg: str):
        # Re-load current conversation from disk (timestamps updated)
        if self.current_conv_id:
            try:
                self.current_conv = load_conversation(self.current_conv_id)
            except Exception:
                pass
        self.render_history()
        self.send_btn.configure(state="normal")
        self.status.set(msg)


def launch():
    app = ChatGUI()
    app.mainloop()
