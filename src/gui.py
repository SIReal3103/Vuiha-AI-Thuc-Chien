# src/gui.py
import os
import json
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

from .paths import ensure_all_dirs
from .conversations import (
    list_conversations,
    create_conversation,
    load_conversation,
    append_message,
    append_image_message,
)
from .api import chat_completions, generate_image, save_image, generate_video
from .logger import log_json

# ---- Model list / defaults ----
try:
    from .constants import AVAILABLE_MODELS, DEFAULT_MODEL
except Exception:
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
    CHAT_MODELS = [
        {"name": "Gemini 2.5 Pro", "value": "gemini-2.5-pro"},
        {"name": "Gemini 2.5 Flash", "value": "gemini-2.5-flash"},
        {"name": "Veo 3.1 (preview)", "value": "veo-3.1-generate-preview"},
        {"name": "Gemini 2.5 Flash Preview TTS", "value": "gemini-2.5-flash-preview-tts"},
        {"name": "Gemini 2.5 Pro Preview TTS", "value": "gemini-2.5-pro-preview-tts"},
    ]
    IMAGE_MODELS = [
        {"name": "Imagen 4 (Google Vertex AI)", "value": "imagen-4"},
        {"name": "Gemini 2.5 Flash Image Preview", "value": "gemini-2.5-flash-image-preview"},
    ]
    AVAILABLE_MODELS = CHAT_MODELS + IMAGE_MODELS
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
        self.uploaded_image_path = None
        self.uploaded_image_data = None

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
        self.model_combo = ttk.Combobox(topbar, values=[m["value"] for m in AVAILABLE_MODELS], width=30)
        self.model_combo.set(DEFAULT_MODEL)
        self.model_combo.pack(side="left", padx=(6, 12))

        ttk.Label(topbar, text="Temp:").pack(side="left")
        self.temp_var = tk.DoubleVar(value=float(os.getenv("TEMPERATURE", "1.0")))
        self.temp_spin = ttk.Spinbox(
            topbar, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var, width=5
        )
        self.temp_spin.pack(side="left", padx=(6, 12))

        # Web Search toggle
        self.ws_enabled = tk.BooleanVar(value=False)
        self.ws_check = ttk.Checkbutton(topbar, text="Use Web Search (context: medium)", variable=self.ws_enabled)
        self.ws_check.pack(side="left", padx=(12, 6))

        # API base indicator
        api_base = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
        ttk.Label(topbar, text=f"@ {api_base}", foreground="#666").pack(side="right")

        # Video generation parameters frame (hidden by default)
        self.video_params_frame = ttk.Frame(self.right, padding=10)
        self.video_params_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(self.video_params_frame, text="Video Prompt:").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.video_prompt_input = ScrolledText(self.video_params_frame, wrap="word", height=3)
        self.video_prompt_input.grid(row=0, column=1, sticky="we", padx=(6, 0), pady=(0, 6))

        ttk.Label(self.video_params_frame, text="Video Model:").grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.video_model_combo = ttk.Combobox(
            self.video_params_frame, values=["veo-3.1-generate-preview"], width=30, state="readonly"
        )
        self.video_model_combo.set("veo-3.1-generate-preview")
        self.video_model_combo.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(0, 6))

        ttk.Label(self.video_params_frame, text="Aspect Ratio:").grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.video_ratio_var = tk.StringVar(value="16:9")
        self.video_ratio_combo = ttk.Combobox(
            self.video_params_frame, textvariable=self.video_ratio_var, values=["16:9", "1:1", "9:16"], width=10, state="readonly"
        )
        self.video_ratio_combo.grid(row=2, column=1, sticky="w", padx=(6, 0), pady=(0, 6))

        ttk.Label(self.video_params_frame, text="Duration (s):").grid(row=3, column=0, sticky="w", pady=(0, 6))
        self.video_duration_var = tk.IntVar(value=8)
        self.video_duration_spin = ttk.Spinbox(
            self.video_params_frame, from_=2, to=10, increment=1, textvariable=self.video_duration_var, width=5
        )
        self.video_duration_spin.grid(row=3, column=1, sticky="w", padx=(6, 0), pady=(0, 6))

        ttk.Label(self.video_params_frame, text="Negative Prompt:").grid(row=4, column=0, sticky="w", pady=(0, 6))
        self.video_negative_prompt_input = ScrolledText(self.video_params_frame, wrap="word", height=2)
        self.video_negative_prompt_input.grid(row=4, column=1, sticky="we", padx=(6, 0), pady=(0, 6))

        # First frame
        first_frame_img_frame = ttk.Frame(self.video_params_frame)
        first_frame_img_frame.grid(row=5, column=0, columnspan=2, sticky="we", pady=(6, 0))
        ttk.Button(first_frame_img_frame, text="Upload First Frame Image", command=self.on_upload_first_frame_image).pack(side="left")
        self.first_frame_image_status = tk.StringVar(value="")
        ttk.Label(first_frame_img_frame, textvariable=self.first_frame_image_status).pack(side="left", padx=(8, 0))
        self.first_frame_image_data = None
        self.first_frame_image_path = None

        # Last frame
        last_frame_img_frame = ttk.Frame(self.video_params_frame)
        last_frame_img_frame.grid(row=6, column=0, columnspan=2, sticky="we", pady=(6, 0))
        ttk.Button(last_frame_img_frame, text="Upload Last Frame Image", command=self.on_upload_last_frame_image).pack(side="left")
        self.last_frame_image_status = tk.StringVar(value="")
        ttk.Label(last_frame_img_frame, textvariable=self.last_frame_image_status).pack(side="left", padx=(8, 0))
        self.last_frame_image_data = None
        self.last_frame_image_path = None

        # Reference images (up to 3)
        ref_img_frame = ttk.Frame(self.video_params_frame)
        ref_img_frame.grid(row=7, column=0, columnspan=2, sticky="we", pady=(6, 0))
        ttk.Button(ref_img_frame, text="Upload Reference Images (max 3)", command=self.on_upload_reference_images).pack(side="left")
        self.reference_images_status = tk.StringVar(value="")
        ttk.Label(ref_img_frame, textvariable=self.reference_images_status).pack(side="left", padx=(8, 0))
        self.reference_images_data = []

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

        # Image buttons (for chat/image gen)
        img_buttons = ttk.Frame(actions)
        img_buttons.grid(row=1, column=0, sticky="we", pady=(8, 0))
        ttk.Button(img_buttons, text="Upload Image", command=self.on_upload_image).pack(side="left", padx=(0, 4))
        ttk.Button(img_buttons, text="Generate Image", command=self.open_image_generator).pack(side="left")
        self.image_status = tk.StringVar(value="")
        ttk.Label(img_buttons, textvariable=self.image_status).pack(side="left", padx=(8, 0))

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
            self.ws_check.pack_forget()
            self.temp_spin.pack_forget()
            self.video_params_frame.grid(row=0, column=0, sticky="we", pady=(0, 6))
            self.model_combo.config(values=["veo-3.1-generate-preview"])
            self.model_combo.set("veo-3.1-generate-preview")
        else:
            self.video_params_frame.grid_forget()
            self.ws_check.pack(side="left", padx=(12, 6))
            self.temp_spin.pack(side="left", padx=(6, 12))
            self.model_combo.config(values=[m["value"] for m in AVAILABLE_MODELS])
            self.model_combo.set(DEFAULT_MODEL)

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
        convs = list_conversations()
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
                message_type = m.get("type", "text")
                prefix = "You" if role == "user" else ("Assistant" if role == "assistant" else role)
                self.history.insert(tk.END, f"{prefix}:\n")
                if message_type == "image" and "image_path" in m:
                    self._display_image_in_chat(m["image_path"], content, m.get('filename', 'image.png'))
                else:
                    self.history.insert(tk.END, f"{content}\n\n")
        self.history.config(state="disabled")
        self.history.see(tk.END)

    def _display_image_in_chat(self, image_path, content, filename):
        try:
            self.history.insert(tk.END, f"{content}\n")
            image = Image.open(image_path)
            max_width, max_height = 400, 300
            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            img_label = tk.Label(self.history, image=photo, bd=2, relief="solid")
            img_label.image = photo
            self.history.window_create(tk.END, window=img_label)
            self.history.insert(tk.END, f"\n[Image: {filename}]\n\n")
        except Exception as e:
            self.history.insert(tk.END, f"{content}\n[📷 {filename} - Could not display: {e}]\n\n")

    def on_send_event(self, _evt):
        self.on_send()
        return "break"

    def on_send(self):
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
        text = self.input_box.get("1.0", tk.END).strip()
        if not text and not self.uploaded_image_data:
            return

        # clear input early
        self.input_box.delete("1.0", tk.END)

        if self.uploaded_image_data:
            filename = os.path.basename(self.uploaded_image_path) if self.uploaded_image_path else "uploaded_image.png"
            append_image_message(self.current_conv, "user", text or "Uploaded image", self.uploaded_image_data, filename)
            self.uploaded_image_data = None
            self.uploaded_image_path = None
            self.image_status.set("")
        else:
            append_message(self.current_conv, "user", text)

        self.render_history()
        self.send_btn.configure(state="disabled")

        selected_api = self.api_var.get()
        if selected_api == "Video Generation":
            self.status.set("Generating video...")
            threading.Thread(target=self._call_video_api_threadsafe, daemon=True).start()
        else:
            self.status.set("Calling /chat/completions...")
            threading.Thread(target=self._call_chat_api_threadsafe, daemon=True).start()

    def _serialize_litellm(self, raw):
        # Fix: ModelResponse is not JSON serializable
        try:
            if hasattr(raw, "model_dump"):
                return raw.model_dump()
            if hasattr(raw, "dict"):
                return raw.dict()
            if hasattr(raw, "json"):
                return json.loads(raw.json())
            return json.loads(str(raw))
        except Exception:
            return str(raw)

    def _call_chat_api_threadsafe(self):
        start = time.time()
        try:
            messages = [{"role": m["role"], "content": m["content"]} for m in self.current_conv["messages"]]
            selected_model = self.model_combo.get() or DEFAULT_MODEL
            temperature = float(self.temp_var.get())
            use_web_search = bool(self.ws_enabled.get())

            result = chat_completions(
                messages=messages,
                model=selected_model,
                temperature=temperature,
                use_web_search=use_web_search,
            )

            reply = result["content"] or "(empty response)"
            append_message(self.current_conv, "assistant", reply)

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
                "response": self._serialize_litellm(result["raw"]),
                "latency_ms": int((time.time() - start) * 1000),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            log_path = log_json(log_payload)
            self._on_api_done(True, f"Done. Log: {log_path}")
        except Exception as e:
            log_path = log_json({
                "type": "api.error",
                "api": "/chat/completions",
                "conversationId": getattr(self.current_conv, "id", None),
                "error": {"message": str(e)},
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            self._on_api_done(False, f"Error: {e}. Logged at: {log_path}")

    def _call_video_api_threadsafe(self):
        start = time.time()
        try:
            prompt = self.video_prompt_input.get("1.0", tk.END).strip()
            model = self.video_model_combo.get()
            aspect_ratio = self.video_ratio_var.get()
            duration = int(self.video_duration_var.get())
            negative_prompt = self.video_negative_prompt_input.get("1.0", tk.END).strip()

            first_frame_image_data = self.first_frame_image_data
            last_frame_image_data = self.last_frame_image_data
            reference_images = self.reference_images_data

            if not prompt and not first_frame_image_data and not last_frame_image_data and not reference_images:
                self._on_api_done(False, "Error: Provide a prompt or at least one image (first/last/reference).")
                return

            # ---- Enforce Veo 3.1 constraints ----
            # Reference images require 8s and 16:9
            if reference_images:
                if duration != 8:
                    duration = 8
                if aspect_ratio != "16:9":
                    aspect_ratio = "16:9"

            # Interpolation (first/last) works best at 8s
            if first_frame_image_data or last_frame_image_data:
                if duration != 8:
                    duration = 8

            # Person generation:
            # - text-to-video only: allow_all
            # - image-to-video / interpolation / referenceImages: allow_adult
            is_image_mode = bool(first_frame_image_data or last_frame_image_data or reference_images)
            person_generation = 'allow_adult' if is_image_mode else 'allow_all'

            result = generate_video(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                duration=duration,
                negative_prompt=negative_prompt,
                person_generation=person_generation,
                reference_images=reference_images if reference_images else None,
                first_frame_image_data=first_frame_image_data,
                last_frame_image_data=last_frame_image_data
            )

            # Clear images after call
            self.first_frame_image_data = None
            self.first_frame_image_path = None
            self.first_frame_image_status.set("")
            self.last_frame_image_data = None
            self.last_frame_image_path = None
            self.last_frame_image_status.set("")
            self.reference_images_data = []
            self.reference_images_status.set("")
            self.video_negative_prompt_input.delete("1.0", tk.END)

            if result["success"]:
                timestamp = int(time.time())
                filename = f"generated_video_{timestamp}.mp4"
                video_path = self._save_video(result["video_data"], filename)

                append_message(
                    self.current_conv,
                    "assistant",
                    f"Generated video using {model}\n"
                    f"- Prompt: {prompt[:180]}{'...' if len(prompt)>180 else ''}\n"
                    f"- Duration: {duration}s | Aspect Ratio: {aspect_ratio}\n"
                    f"- First frame: {result.get('first_frame_present')} | Last frame: {result.get('last_frame_present')} | Ref imgs: {result.get('reference_images')}\n"
                    f"- Saved to: {video_path}"
                )

                log_payload = {
                    "type": "api.call",
                    "api": "/video/generation",
                    "conversationId": self.current_conv["id"],
                    "request": {
                        "prompt": prompt,
                        "model": model,
                        "aspect_ratio": aspect_ratio,
                        "duration": duration,
                        "negative_prompt": negative_prompt,
                        "first_frame_image_present": bool(first_frame_image_data),
                        "last_frame_image_present": bool(last_frame_image_data),
                        "reference_images_count": len(reference_images) if reference_images else 0,
                        "person_generation": person_generation,
                    },
                    "response": {
                        "video_id": result.get("video_id"),
                        "path": video_path
                    },
                    "latency_ms": int((time.time() - start) * 1000),
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                log_json(log_payload)

                self._on_api_done(True, f"Video generated and saved: {filename}")
            else:
                self._on_api_done(False, f"Video generation failed: {result['error']}")

        except Exception as e:
            log_path = log_json({
                "type": "api.error",
                "api": "/video/generation",
                "conversationId": getattr(self.current_conv, "id", None),
                "error": {"message": str(e)},
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            self._on_api_done(False, f"Error: {e}. Logged at: {log_path}")

    def _save_video(self, video_data, filename):
        os.makedirs("generated_videos", exist_ok=True)
        filepath = os.path.join("generated_videos", filename)
        with open(filepath, "wb") as f:
            f.write(video_data)
        return filepath

    def _on_api_done(self, success: bool, msg: str):
        self.after(0, self._finalize_ui_update, success, msg)

    def _finalize_ui_update(self, _success: bool, msg: str):
        if self.current_conv_id:
            try:
                self.current_conv = load_conversation(self.current_conv_id)
            except Exception:
                pass
        self.render_history()
        self.send_btn.configure(state="normal")
        self.status.set(msg)

    # ---------- Image Functions (chat/image-gen) ----------
    def on_upload_image(self):
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    self.uploaded_image_data = f.read()
                self.uploaded_image_path = file_path
                filename = os.path.basename(file_path)
                self.image_status.set(f"Loaded: {filename}")
                self.status.set(f"Image uploaded: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
                self.status.set("Failed to load image")

    # ---------- Video image pickers ----------
    def on_upload_first_frame_image(self):
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
        file_path = filedialog.askopenfilename(
            title="Select a first frame image for video generation",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    self.first_frame_image_data = f.read()
                self.first_frame_image_path = file_path
                filename = os.path.basename(file_path)
                self.first_frame_image_status.set(f"Loaded: {filename}")
                self.status.set(f"First frame image uploaded: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load first frame image: {e}")
                self.status.set("Failed to load first frame image")

    def on_upload_last_frame_image(self):
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
        file_path = filedialog.askopenfilename(
            title="Select a last frame image for video generation",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    self.last_frame_image_data = f.read()
                self.last_frame_image_path = file_path
                filename = os.path.basename(file_path)
                self.last_frame_image_status.set(f"Loaded: {filename}")
                self.status.set(f"Last frame image uploaded: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load last frame image: {e}")
                self.status.set("Failed to load last frame image")

    def on_upload_reference_images(self):
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
        file_paths = filedialog.askopenfilenames(
            title="Select up to 3 reference images",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"), ("All files", "*.*")]
        )
        if file_paths:
            try:
                self.reference_images_data.clear()
                for p in list(file_paths)[:3]:
                    with open(p, "rb") as f:
                        self.reference_images_data.append(f.read())
                self.reference_images_status.set(f"{len(self.reference_images_data)} image(s) loaded")
                self.status.set("Reference images loaded.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load reference images: {e}")
                self.status.set("Failed to load reference images")

    # ---------- Image Generator window ----------
    def open_image_generator(self):
        if hasattr(self, "image_generator_window") and self.image_generator_window is not None and tk.Toplevel.winfo_exists(self.image_generator_window):
            self.image_generator_window.lift()
            self.image_generator_window.focus()
        else:
            self.image_generator_window = ImageGeneratorWindow(self)


class ImageGeneratorWindow(tk.Toplevel):
    """Separate window for image generation that mirrors the main conversation window."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("Thực Chiến AI – Image Generator")
        self.geometry("1120x740")
        self.minsize(1000, 640)

        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        self.current_conv = parent.current_conv
        self.current_conv_id = parent.current_conv_id
        self.uploaded_image_path = None
        self.uploaded_image_data = None

        # Layout
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

        # Right column
        self.right = ttk.Frame(self, padding=10)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        # Topbar
        topbar = ttk.Frame(self.right)
        topbar.grid(row=0, column=0, sticky="we", pady=(0, 6))
        ttk.Label(topbar, text="API:").pack(side="left")
        self.api_var = tk.StringVar(value="Image Generation")
        self.api_combo = ttk.Combobox(topbar, textvariable=self.api_var, state="readonly", values=["Image Generation"], width=34)
        self.api_combo.pack(side="left", padx=(6, 12))

        ttk.Label(topbar, text="Model:").pack(side="left")
        self.model_combo = ttk.Combobox(topbar, values=["imagen-4", "gemini-2.5-flash-image-preview"], width=30)
        self.model_combo.set("imagen-4")
        self.model_combo.pack(side="left", padx=(6, 12))

        ttk.Label(topbar, text="Aspect Ratio:").pack(side="left")
        self.ratio_var = tk.StringVar(value="1:1")
        self.ratio_combo = ttk.Combobox(topbar, textvariable=self.ratio_var, width=10)
        self.ratio_combo['values'] = ["1:1", "16:9", "9:16", "4:3", "3:4"]
        self.ratio_combo.pack(side="left", padx=(6, 12))

        api_base = os.getenv("THUCCHIEN_API_BASE", "https://api.thucchien.ai")
        ttk.Label(topbar, text=f"@ {api_base}", foreground="#666").pack(side="right")

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
        self.send_btn = ttk.Button(actions, text="Generate  (Ctrl+Enter)", command=self.on_send)
        self.send_btn.grid(row=0, column=0, sticky="we")
        img_buttons = ttk.Frame(actions)
        img_buttons.grid(row=1, column=0, sticky="we", pady=(8, 0))
        ttk.Button(img_buttons, text="Upload Image", command=self.on_upload_image).pack(side="left", padx=(0, 4))
        self.image_status = tk.StringVar(value="")
        ttk.Label(img_buttons, textvariable=self.image_status).pack(side="left", padx=(8, 0))

        # Status bar
        self.status = tk.StringVar(value="Ready to generate images.")
        statusbar = ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken")
        statusbar.grid(row=1, column=0, columnspan=2, sticky="we")

        # Load conversations
        self.refresh_convs()
        if self.conv_list.size() > 0 and self.current_conv_id:
            for i in range(self.conv_list.size()):
                if self.current_conv_id in self.conv_list.get(i):
                    self.conv_list.selection_set(i)
                    break
            self.render_history()

        self.current_image_data = None
        self.current_image_filename = None

        self.bind('<Escape>', lambda e: self.on_close())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # Conversations
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
        convs = list_conversations()
        item = convs[idx[0]]
        self.current_conv = load_conversation(item["id"])
        self.current_conv_id = item["id"]
        self.render_history()
        self.status.set(f"Opened: {self.current_conv['name']}")
        self.parent.current_conv = self.current_conv
        self.parent.current_conv_id = self.current_conv_id
        self.parent.render_history()

    # Chat UI
    def render_history(self):
        self.history.config(state="normal")
        self.history.delete("1.0", tk.END)
        if not self.current_conv:
            self.history.insert(tk.END, "No conversation selected.\n")
        else:
            for m in self.current_conv.get("messages", []):
                role = m["role"]
                content = m["content"]
                message_type = m.get("type", "text")
                prefix = "You" if role == "user" else ("Assistant" if role == "assistant" else role)
                self.history.insert(tk.END, f"{prefix}:\n")
                if message_type == "image" and "image_path" in m:
                    self._display_image_in_chat(m["image_path"], content, m.get('filename', 'image.png'))
                else:
                    self.history.insert(tk.END, f"{content}\n\n")
        self.history.config(state="disabled")
        self.history.see(tk.END)

    def _display_image_in_chat(self, image_path, content, filename):
        try:
            self.history.insert(tk.END, f"{content}\n")
            image = Image.open(image_path)
            max_width, max_height = 400, 300
            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            img_label = tk.Label(self.history, image=photo, bd=2, relief="solid")
            img_label.image = photo
            self.history.window_create(tk.END, window=img_label)
            self.history.insert(tk.END, f"\n[Image: {filename}]\n\n")
        except Exception as e:
            self.history.insert(tk.END, f"{content}\n[📷 {filename} - Could not display: {e}]\n\n")

    def on_send_event(self, _evt):
        self.on_send()
        return "break"

    def on_send(self):
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
        text = self.input_box.get("1.0", tk.END).strip()
        if not text and not self.uploaded_image_data:
            return
        self.input_box.delete("1.0", tk.END)
        if self.uploaded_image_data:
            filename = os.path.basename(self.uploaded_image_path) if self.uploaded_image_path else "uploaded_image.png"
            append_image_message(self.current_conv, "user", text or "Uploaded image", self.uploaded_image_data, filename)
            self.uploaded_image_data = None
            self.uploaded_image_path = None
            self.image_status.set("")
        else:
            append_message(self.current_conv, "user", text)
        self.render_history()
        self.send_btn.configure(state="disabled")
        self.status.set("Generating image...")
        threading.Thread(target=self._generate_image_threadsafe, daemon=True).start()

    def _generate_image_threadsafe(self):
        start = time.time()
        try:
            prompt = ""
            image_context = []
            if self.uploaded_image_data:
                image_context.append(self.uploaded_image_data)
            for m in reversed(self.current_conv["messages"]):
                if m.get("type") == "image" and "image_path" in m:
                    try:
                        with open(m["image_path"], "rb") as img_file:
                            img_data = img_file.read()
                            image_context.append(img_data)
                    except Exception:
                        pass
                elif m["role"] == "user" and not prompt:
                    prompt = m["content"]
            if not prompt:
                prompt = "Generate an image based on the uploaded context"

            result = generate_image(
                prompt=prompt,
                model=self.model_combo.get(),
                aspect_ratio=self.ratio_var.get(),
                image_context=image_context if image_context else None
            )

            if result["success"]:
                timestamp = int(time.time())
                filename = f"generated_{timestamp}.png"
                saved_path = save_image(result["image_data"], filename)
                image_path = append_image_message(
                    self.current_conv,
                    "assistant",
                    f"Generated image using {self.model_combo.get()} based on: '{prompt}'",
                    result["image_data"],
                    filename
                )
                self._on_image_done(True, f"Image generated and saved: {filename}", image_path)
                self.parent.current_conv = load_conversation(self.current_conv_id)
                self.parent.render_history()
                log_payload = {
                    "type": "image.generation",
                    "api": "/image/generation",
                    "conversationId": self.current_conv["id"],
                    "request": {
                        "prompt": prompt,
                        "model": self.model_combo.get(),
                        "aspect_ratio": self.ratio_var.get()
                    },
                    "response": {
                        "filename": filename,
                        "path": saved_path
                    },
                    "latency_ms": int((time.time() - start) * 1000),
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                log_json(log_payload)
            else:
                self._on_image_done(False, f"Image generation failed: {result['error']}", None)
        except Exception as e:
            self._on_image_done(False, f"Error generating image: {e}", None)

    def _on_image_done(self, success: bool, msg: str, image_path: str = None):
        self.after(0, self._finalize_ui_update, success, msg, image_path)

    def _finalize_ui_update(self, _success: bool, msg: str, image_path: str = None):
        if self.current_conv_id:
            try:
                self.current_conv = load_conversation(self.current_conv_id)
            except Exception:
                pass
        self.render_history()
        self.send_btn.configure(state="normal")
        self.status.set(msg)

    def on_upload_image(self):
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    self.uploaded_image_data = f.read()
                self.uploaded_image_path = file_path
                filename = os.path.basename(file_path)
                self.image_status.set(f"Loaded: {filename}")
                self.status.set(f"Image uploaded: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
                self.status.set("Failed to load image")

    def on_close(self):
        self.grab_release()
        self.parent.image_generator_window = None
        self.destroy()


def launch():
    app = ChatGUI()
    app.mainloop()
