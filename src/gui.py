# src/gui.py
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from .paths import ensure_all_dirs
from .conversations import list_conversations, create_conversation, load_conversation, append_message, save_conversation
from .api import chat_completions, DEFAULT_MODEL, DEFAULT_TEMP
from .logger import log_json
from .api import chat_completions

class ChatGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Thực Chiến AI – Chat GUI")
        self.geometry("1100x700")
        self.minsize(1000, 640)

        ensure_all_dirs()

        self.current_conv = None
        self.current_conv_id = None

        # ====== Layout: Left (conversations) / Right (chat) ======
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.left = ttk.Frame(self, padding=10)
        self.left.grid(row=0, column=0, sticky="ns")
        self.right = ttk.Frame(self, padding=10)
        self.right.grid(row=0, column=1, sticky="nsew")

        # ====== Left panel: Conversations ======
        ttk.Label(self.left, text="Conversations", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.conv_list = tk.Listbox(self.left, height=26, activestyle="dotbox")
        self.conv_list.grid(row=1, column=0, columnspan=2, sticky="nswe")
        self.left.grid_rowconfigure(1, weight=1)
        self.left.grid_columnconfigure(0, weight=1)

        btns = ttk.Frame(self.left)
        btns.grid(row=2, column=0, columnspan=2, sticky="we", pady=8)
        ttk.Button(btns, text="New", command=self.on_new_conv).pack(side="left")
        ttk.Button(btns, text="Refresh", command=self.refresh_convs).pack(side="left", padx=6)
        ttk.Button(btns, text="Open", command=self.on_open_conv).pack(side="left")

        # ====== Right panel: Controls ======
        topbar = ttk.Frame(self.right)
        topbar.grid(row=0, column=0, sticky="we")
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        ttk.Label(topbar, text="API:").pack(side="left")
        self.api_var = tk.StringVar(value="Chat Completions (/chat/completions)")
        self.api_combo = ttk.Combobox(topbar, textvariable=self.api_var, state="readonly",
                                      values=["Chat Completions (/chat/completions)"])
        self.api_combo.pack(side="left", padx=(6, 12))

        ttk.Label(topbar, text="Model:").pack(side="left")
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.model_entry = ttk.Entry(topbar, textvariable=self.model_var, width=24)
        self.model_entry.pack(side="left", padx=(6, 12))

        ttk.Label(topbar, text="Temp:").pack(side="left")
        self.temp_var = tk.DoubleVar(value=DEFAULT_TEMP)
        self.temp_spin = ttk.Spinbox(topbar, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var, width=5)
        self.temp_spin.pack(side="left", padx=(6, 12))

        # ====== Chat history ======
        self.history = ScrolledText(self.right, wrap="word", height=22, state="disabled")
        self.history.grid(row=1, column=0, sticky="nsew", pady=(8, 8))

        # ====== Input area ======
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

        # ====== Status bar ======
        self.status = tk.StringVar(value="Ready.")
        statusbar = ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken")
        statusbar.grid(row=1, column=0, columnspan=2, sticky="we")

        # Load initial list
        self.refresh_convs()

        # Auto-open latest if available
        if self.conv_list.size() > 0:
            self.conv_list.selection_set(0)
            self.on_open_conv()

    # ---------- Conversation management ----------
    def refresh_convs(self):
        self.conv_list.delete(0, tk.END)
        convs = list_conversations()
        for c in convs:
            ts = c.get("updatedAt", c.get("createdAt"))
            label = f"{c['name']} — {ts}"
            self.conv_list.insert(tk.END, label)
            self.conv_list.itemconfig(tk.END)
        self.status.set(f"Loaded {self.conv_list.size()} conversation(s).")

    def on_new_conv(self):
        conv = create_conversation()
        self.status.set(f"Created: {conv['name']}")
        self.refresh_convs()
        # Select newly created (list_conversations sorts by updated desc → it’s at top)
        if self.conv_list.size() > 0:
            self.conv_list.selection_clear(0, tk.END)
            self.conv_list.selection_set(0)
            self.on_open_conv()

    def on_open_conv(self):
        idx = self.conv_list.curselection()
        if not idx:
            self.status.set("Select a conversation first.")
            return
        # list_conversations() is sorted desc; map ui index to actual id
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
                if role == "user":
                    self.history.insert(tk.END, f"You:\n{content}\n\n")
                elif role == "assistant":
                    self.history.insert(tk.END, f"Assistant:\n{content}\n\n")
                else:
                    self.history.insert(tk.END, f"{role}:\n{content}\n\n")
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
        # clear input
        self.input_box.delete("1.0", tk.END)

        # Append user message + update history right away
        append_message(self.current_conv, "user", text)
        self.render_history()

        # Disable send while waiting
        self.send_btn.configure(state="disabled")
        self.status.set("Calling /chat/completions...")

        # Run API call in a background thread to keep UI responsive
        thread = threading.Thread(target=self._call_chat_api_threadsafe, daemon=True)
        thread.start()

    def _call_chat_api_threadsafe(self):
        start = time.time()
        try:
            messages = [{"role": m["role"], "content": m["content"]} for m in self.current_conv["messages"]]
            result = chat_completions(messages, model=self.model_var.get(), temperature=float(self.temp_var.get()))
            reply = result["content"] or "(empty response)"
            append_message(self.current_conv, "assistant", reply)

            log_path = log_json({
                "type": "chat.completions",
                "conversationId": self.current_conv["id"],
                "request": {"messages": messages},
                "response": result["raw"],
                "latency_ms": int((time.time() - start) * 1000),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })

            self._on_api_done(success=True, msg=f"Done. Log: {log_path}")
        except Exception as e:
            log_path = log_json({
                "type": "chat.completions.error",
                "conversationId": getattr(self.current_conv, "id", None),
                "error": {"message": str(e)},
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            self._on_api_done(success=False, msg=f"Error: {e}. Logged at: {log_path}")

    def _on_api_done(self, success: bool, msg: str):
        # Back to main thread to touch UI
        self.after(0, self._finalize_ui_update, success, msg)

    def _finalize_ui_update(self, success: bool, msg: str):
        # Reload the conversation from disk in case timestamps changed
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
