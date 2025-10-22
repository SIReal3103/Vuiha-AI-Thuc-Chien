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
import base64
import io

from .paths import ensure_all_dirs
from .conversations import (
    list_conversations,
    create_conversation,
    load_conversation,
    append_message,
    append_image_message,
)
from .api import chat_completions, generate_image, save_image
from .logger import log_json

# ---- Model list / defaults ----
# Try to import from constants.py if you created it; otherwise fallback.
try:
    from .constants import AVAILABLE_MODELS, DEFAULT_MODEL
except Exception:
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
    # Text-only models for regular chat
    CHAT_MODELS = [
        {"name": "Gemini 2.5 Pro", "value": "gemini-2.5-pro"},
        {"name": "Gemini 2.5 Flash", "value": "gemini-2.5-flash"},
        {"name": "Veo 3", "value": "veo 3"},
        {"name": "Gemini 2.5 Flash Preview TTS", "value": "gemini-2.5-flash-preview-tts"},
        {"name": "Gemini 2.5 Pro Preview TTS", "value": "gemini-2.5-pro-preview-tts"},
    ]
    # Image generation models
    IMAGE_MODELS = [
        {"name": "Imagen 4 (Google Vertex AI)", "value": "imagen-4"},
        {"name": "Gemini 2.5 Flash Image Preview", "value": "gemini-2.5-flash-image-preview"},
    ]
    # Combined list for backwards compatibility
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
            values=["Chat Completions (/chat/completions)"],
            width=34,
        )
        self.api_combo.pack(side="left", padx=(6, 12))

        ttk.Label(topbar, text="Model:").pack(side="left")
        self.model_combo = ttk.Combobox(
            topbar, values=[m["value"] for m in CHAT_MODELS], width=30
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
        
        # Image buttons
        img_buttons = ttk.Frame(actions)
        img_buttons.grid(row=1, column=0, sticky="we", pady=(8, 0))
        ttk.Button(img_buttons, text="Upload Image", command=self.on_upload_image).pack(side="left", padx=(0, 4))
        ttk.Button(img_buttons, text="Generate Image", command=self.open_image_generator).pack(side="left")
        self.image_status = tk.StringVar(value="")
        ttk.Label(img_buttons, textvariable=self.image_status).pack(side="left", padx=(8, 0))
        
        # Store reference to image generator window
        self.image_generator_window = None

        # Status bar
        self.status = tk.StringVar(value="Ready.")
        statusbar = ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken")
        statusbar.grid(row=1, column=0, columnspan=2, sticky="we")

        # Load conversations
        self.refresh_convs()
        if self.conv_list.size() > 0:
            self.conv_list.selection_set(0)
            self.on_open_conv()

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
                message_type = m.get("type", "text")
                prefix = "You" if role == "user" else ("Assistant" if role == "assistant" else role)
                
                self.history.insert(tk.END, f"{prefix}:\n")
                
                if message_type == "image" and "image_path" in m:
                    # Display image directly in chat
                    self._display_image_in_chat(m["image_path"], content, m.get('filename', 'image.png'))
                else:
                    # Regular text message
                    self.history.insert(tk.END, f"{content}\n\n")
                    
        self.history.config(state="disabled")
        self.history.see(tk.END)
    
    def _display_image_in_chat(self, image_path, content, filename):
        """Display an image directly in the chat history."""
        try:
            # Insert the content text first
            self.history.insert(tk.END, f"{content}\n")
            
            # Load and display the image
            image = Image.open(image_path)
            
            # Resize image to fit in chat (max width 400, max height 300)
            max_width, max_height = 400, 300
            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(image)
            
            # Create a label for the image
            img_label = tk.Label(self.history, image=photo, bd=2, relief="solid")
            img_label.image = photo  # Keep a reference
            
            # Calculate position to insert the image
            line_start = self.history.index(tk.END)
            self.history.window_create(tk.END, window=img_label)
            self.history.insert(tk.END, f"\n[Image: {filename}]\n\n")
            
        except Exception as e:
            # Fallback to clickable link if image display fails
            self.history.insert(tk.END, f"{content}\n")
            
            def open_image():
                try:
                    # Open image with default viewer
                    if os.name == 'nt':  # Windows
                        os.startfile(image_path)
                    elif os.name == 'posix':  # macOS and Linux
                        os.system(f'open "{image_path}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{image_path}"')
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open image: {e}")
            
            # Create a clickable text link
            link_start = self.history.index(tk.END)
            self.history.insert(tk.END, f"[📷 {filename} - Could not display: {e}]")
            link_end = self.history.index(tk.END)
            
            # Add tag for clickable link
            self.history.tag_add("image_link", link_start, link_end)
            self.history.tag_config("image_link", foreground="blue", underline=True)
            self.history.tag_bind("image_link", "<Button-1>", lambda e: open_image())
            self.history.tag_bind("image_link", "<Enter>", lambda e: self.history.config(cursor="hand2"))
            self.history.tag_bind("image_link", "<Leave>", lambda e: self.history.config(cursor=""))
            
            self.history.insert(tk.END, "\n\n")

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

        # Handle uploaded image if present
        if self.uploaded_image_data:
            filename = os.path.basename(self.uploaded_image_path) if self.uploaded_image_path else "uploaded_image.png"
            append_image_message(self.current_conv, "user", text or "Uploaded image", self.uploaded_image_data, filename)
            self.uploaded_image_data = None
            self.uploaded_image_path = None
            self.image_status.set("")
        else:
            # append user message + update UI
            append_message(self.current_conv, "user", text)
        
        self.render_history()

        # lock UI while calling API
        self.send_btn.configure(state="disabled")
        self.status.set("Calling /chat/completions...")
        threading.Thread(target=self._call_chat_api_threadsafe, daemon=True).start()

    def _call_chat_api_threadsafe(self):
        start = time.time()
        try:
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
        except Exception as e:
            log_path = log_json({
                "type": "api.error",
                "api": "/chat/completions",
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

    # ---------- Image Functions ----------
    def on_upload_image(self):
        """Handle image upload from file system."""
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
            
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"),
                ("All files", "*.*")
            ]
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

    def open_image_generator(self):
        """Open the separate image generation window."""
        if self.image_generator_window is not None and tk.Toplevel.winfo_exists(self.image_generator_window):
            # If window already exists, bring it to front
            self.image_generator_window.lift()
            self.image_generator_window.focus()
        else:
            # Create new image generator window
            self.image_generator_window = ImageGeneratorWindow(self)
    
    def add_generated_image_to_conversation(self, image_data, filename, prompt, model):
        """Add a generated image to the current conversation."""
        if not self.current_conv:
            messagebox.showwarning("No Conversation", "Please create or open a conversation first.")
            return None
            
        # Add to conversation
        image_path = append_image_message(
            self.current_conv,
            "assistant",
            f"Generated image using {model} based on: '{prompt}'",
            image_data,
            filename
        )
        
        # Reload and render conversation
        self.current_conv = load_conversation(self.current_conv_id)
        self.render_history()
        
        return image_path


class ImageGeneratorWindow(tk.Toplevel):
    """Separate window for image generation that mirrors the main conversation window."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.title("Thực Chiến AI – Image Generator")
        self.geometry("1120x740")
        self.minsize(1000, 640)
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
        # Center the window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        # Use the same conversation as parent
        self.current_conv = parent.current_conv
        self.current_conv_id = parent.current_conv_id
        self.uploaded_image_path = None
        self.uploaded_image_data = None
        
        # ========== Layout split (same as main window) ==========
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
        
        # Topbar controls with image generation settings
        topbar = ttk.Frame(self.right)
        topbar.grid(row=0, column=0, sticky="we", pady=(0, 6))
        
        ttk.Label(topbar, text="API:").pack(side="left")
        self.api_var = tk.StringVar(value="Image Generation")
        self.api_combo = ttk.Combobox(
            topbar,
            textvariable=self.api_var,
            state="readonly",
            values=["Image Generation"],
            width=34,
        )
        self.api_combo.pack(side="left", padx=(6, 12))
        
        ttk.Label(topbar, text="Model:").pack(side="left")
        self.model_combo = ttk.Combobox(
            topbar, values=["imagen-4", "gemini-2.5-flash-image-preview"], width=30
        )
        self.model_combo.set("imagen-4")
        self.model_combo.pack(side="left", padx=(6, 12))
        
        ttk.Label(topbar, text="Aspect Ratio:").pack(side="left")
        self.ratio_var = tk.StringVar(value="1:1")
        self.ratio_combo = ttk.Combobox(topbar, textvariable=self.ratio_var, width=10)
        self.ratio_combo['values'] = ["1:1", "16:9", "9:16", "4:3", "3:4"]
        self.ratio_combo.pack(side="left", padx=(6, 12))
        
        # API base indicator (from env)
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
        
        # Image buttons
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
            # Find and select current conversation
            for i in range(self.conv_list.size()):
                if self.current_conv_id in self.conv_list.get(i):
                    self.conv_list.selection_set(i)
                    break
            self.render_history()
        
        # Store generated image data
        self.current_image_data = None
        self.current_image_filename = None
        
        # Bind events
        self.bind('<Escape>', lambda e: self.on_close())
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    # ---------- Conversations (same as main window) ----------
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
        
        # Also update parent's conversation
        self.parent.current_conv = self.current_conv
        self.parent.current_conv_id = self.current_conv_id
        self.parent.render_history()

    # ---------- Chat (modified for image generation) ----------
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
                    # Display image directly in chat
                    self._display_image_in_chat(m["image_path"], content, m.get('filename', 'image.png'))
                else:
                    # Regular text message
                    self.history.insert(tk.END, f"{content}\n\n")
                    
        self.history.config(state="disabled")
        self.history.see(tk.END)
    
    def _display_image_in_chat(self, image_path, content, filename):
        """Display an image directly in the chat history."""
        try:
            # Insert the content text first
            self.history.insert(tk.END, f"{content}\n")
            
            # Load and display the image
            image = Image.open(image_path)
            
            # Resize image to fit in chat (max width 400, max height 300)
            max_width, max_height = 400, 300
            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(image)
            
            # Create a label for the image
            img_label = tk.Label(self.history, image=photo, bd=2, relief="solid")
            img_label.image = photo  # Keep a reference
            
            # Calculate position to insert the image
            line_start = self.history.index(tk.END)
            self.history.window_create(tk.END, window=img_label)
            self.history.insert(tk.END, f"\n[Image: {filename}]\n\n")
            
        except Exception as e:
            # Fallback to clickable link if image display fails
            self.history.insert(tk.END, f"{content}\n")
            
            def open_image():
                try:
                    # Open image with default viewer
                    if os.name == 'nt':  # Windows
                        os.startfile(image_path)
                    elif os.name == 'posix':  # macOS and Linux
                        os.system(f'open "{image_path}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{image_path}"')
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open image: {e}")
            
            # Create a clickable text link
            link_start = self.history.index(tk.END)
            self.history.insert(tk.END, f"[📷 {filename} - Could not display: {e}]")
            link_end = self.history.index(tk.END)
            
            # Add tag for clickable link
            self.history.tag_add("image_link", link_start, link_end)
            self.history.tag_config("image_link", foreground="blue", underline=True)
            self.history.tag_bind("image_link", "<Button-1>", lambda e: open_image())
            self.history.tag_bind("image_link", "<Enter>", lambda e: self.history.config(cursor="hand2"))
            self.history.tag_bind("image_link", "<Leave>", lambda e: self.history.config(cursor=""))
            
            self.history.insert(tk.END, "\n\n")

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

        # Handle uploaded image if present
        if self.uploaded_image_data:
            filename = os.path.basename(self.uploaded_image_path) if self.uploaded_image_path else "uploaded_image.png"
            append_image_message(self.current_conv, "user", text or "Uploaded image", self.uploaded_image_data, filename)
            self.uploaded_image_data = None
            self.uploaded_image_path = None
            self.image_status.set("")
        else:
            # append user message + update UI
            append_message(self.current_conv, "user", text)
        
        self.render_history()

        # Generate image
        self.send_btn.configure(state="disabled")
        self.status.set("Generating image...")
        threading.Thread(target=self._generate_image_threadsafe, daemon=True).start()

    def _generate_image_threadsafe(self):
        """Generate image in a separate thread."""
        start = time.time()
        try:
            # Get the last user message as prompt
            prompt = ""
            image_context = []
            
            # Collect uploaded image from current session
            if self.uploaded_image_data:
                image_context.append(self.uploaded_image_data)
            
            # Also collect images from conversation history
            for m in reversed(self.current_conv["messages"]):
                if m.get("type") == "image" and "image_path" in m:
                    try:
                        with open(m["image_path"], "rb") as img_file:
                            img_data = img_file.read()
                            image_context.append(img_data)
                    except Exception:
                        pass  # Skip if image can't be loaded
                elif m["role"] == "user" and not prompt:
                    # Get the text from the last user message
                    prompt = m["content"]
            
            # If no user message found, use empty string
            if not prompt:
                prompt = "Generate an image based on the uploaded context"
            
            result = generate_image(
                prompt=prompt,
                model=self.model_combo.get(),
                aspect_ratio=self.ratio_var.get(),
                image_context=image_context if image_context else None
            )
            
            if result["success"]:
                # Save the image
                timestamp = int(time.time())
                filename = f"generated_{timestamp}.png"
                saved_path = save_image(result["image_data"], filename)
                
                # Add to conversation
                image_path = append_image_message(
                    self.current_conv,
                    "assistant",
                    f"Generated image using {self.model_combo.get()} based on: '{prompt}'",
                    result["image_data"],
                    filename
                )
                
                self._on_image_done(True, f"Image generated and saved: {filename}", image_path)
                
                # Update parent window
                self.parent.current_conv = load_conversation(self.current_conv_id)
                self.parent.render_history()
                
                # Log the generation
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
        """Handle image generation completion."""
        self.after(0, self._finalize_ui_update, success, msg, image_path)

    def _finalize_ui_update(self, _success: bool, msg: str, image_path: str = None):
        """Finalize UI update after image generation."""
        # Reload conversation to get updated messages
        if self.current_conv_id:
            try:
                self.current_conv = load_conversation(self.current_conv_id)
            except Exception:
                pass
        
        self.render_history()
        self.send_btn.configure(state="normal")
        self.status.set(msg)

    # ---------- Image Functions ----------
    def on_upload_image(self):
        """Handle image upload from file system."""
        if not self.current_conv:
            self.status.set("Create or open a conversation first.")
            return
            
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"),
                ("All files", "*.*")
            ]
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
        """Close the image generator window."""
        # Release grab and destroy window
        self.grab_release()
        self.parent.image_generator_window = None
        self.destroy()


def launch():
    app = ChatGUI()
    app.mainloop()
