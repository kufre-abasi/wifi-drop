#!/usr/bin/env python3
"""Native desktop control panel for WiFi Drop."""

import json
import os
import platform
import secrets
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

from wifi_drop import Handler, UPLOADS, UPLOADS_LOCK, WiFiDropServer, local_ipv4_addresses


APP_NAME = "WiFi Drop"
DEFAULT_FOLDER = Path.home() / "Desktop" / APP_NAME
PAPER = "#f5f1e8"
CARD = "#fffdf8"
INK = "#17211b"
MUTED = "#647069"
GREEN = "#176b4a"
SOFT = "#dfeee5"
LINE = "#d9d5ca"


def settings_path():
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME / "settings.json"


def load_destination():
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        path = Path(data.get("destination", "")).expanduser()
        if str(path):
            return path
    except (OSError, ValueError, TypeError):
        pass
    return DEFAULT_FOLDER


def save_destination(path):
    target = settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"destination": str(path)}, indent=2), encoding="utf-8")


def reveal_path(path):
    path = str(path)
    if platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    elif platform.system() == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", path])


class WiFiDropApp:
    def __init__(self, root):
        self.root = root
        self.server = None
        self.server_thread = None
        self.destination = load_destination().resolve()
        self.url = ""
        self.qr_photo = None

        root.title(APP_NAME)
        root.geometry("670x710")
        root.minsize(610, 650)
        root.configure(bg=PAPER)
        root.protocol("WM_DELETE_WINDOW", self.close)
        if platform.system() == "Darwin":
            try:
                root.tk.call("::tk::unsupported::MacWindowStyle", "style", root._w, "document", "closeBox resizable")
            except tk.TclError:
                pass

        self.status_var = tk.StringVar(value="Starting…")
        self.link_var = tk.StringVar(value="Preparing your private link…")
        self.folder_var = tk.StringVar(value=str(self.destination))
        self.activity_var = tk.StringVar(value="No transfers yet")
        self.shared_var = tk.StringVar(value="No files shared from this laptop")

        self.build_ui()
        self.start_server()
        self.poll_activity()

    def label(self, parent, text="", **kwargs):
        options = {"bg": kwargs.pop("bg", parent.cget("bg")), "fg": INK, "font": ("Helvetica", 13)}
        options.update(kwargs)
        return tk.Label(parent, text=text, **options)

    def button(self, parent, text, command, primary=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=GREEN if primary else SOFT,
            fg="white" if primary else GREEN,
            activebackground="#0d5137" if primary else "#d3e8dc",
            activeforeground="white" if primary else GREEN,
            relief="flat",
            bd=0,
            padx=17,
            pady=9,
            cursor="hand2",
            font=("Helvetica", 12, "bold"),
            highlightthickness=0,
        )

    def card(self, parent):
        return tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1, padx=20, pady=17)

    def build_ui(self):
        outer = tk.Frame(self.root, bg=PAPER, padx=30, pady=25)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=PAPER)
        header.pack(fill="x")
        self.label(header, APP_NAME, font=("Helvetica", 20, "bold")).pack(side="left")
        status = self.label(header, textvariable=self.status_var, bg=SOFT, fg=GREEN, font=("Helvetica", 11, "bold"), padx=12, pady=6)
        status.pack(side="right")

        self.label(outer, "Share files across the room.", font=("Helvetica", 33, "bold"), anchor="w").pack(fill="x", pady=(24, 5))
        self.label(outer, "No cloud, no account, no phone app. Just the same Wi-Fi.", fg=MUTED, font=("Helvetica", 14), anchor="w").pack(fill="x", pady=(0, 20))

        link_card = self.card(outer)
        link_card.pack(fill="x", pady=(0, 14))
        left = tk.Frame(link_card, bg=CARD)
        left.pack(side="left", fill="both", expand=True)
        self.label(left, "PHONE LINK", bg=CARD, fg=MUTED, font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        link = tk.Entry(left, textvariable=self.link_var, state="readonly", readonlybackground=CARD, fg=INK, relief="flat", font=("Menlo", 12), width=42)
        link.pack(fill="x", pady=(8, 13))
        actions = tk.Frame(left, bg=CARD)
        actions.pack(fill="x")
        self.button(actions, "Copy link", self.copy_link, primary=True).pack(side="left", padx=(0, 9))
        self.button(actions, "Open preview", self.open_preview).pack(side="left")
        self.qr_label = tk.Label(link_card, bg=CARD, width=11, height=6)
        self.qr_label.pack(side="right", padx=(18, 0))

        folder_card = self.card(outer)
        folder_card.pack(fill="x", pady=(0, 14))
        self.label(folder_card, "SAVE RECEIVED FILES TO", bg=CARD, fg=MUTED, font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        self.label(folder_card, textvariable=self.folder_var, bg=CARD, font=("Helvetica", 13, "bold"), anchor="w").pack(fill="x", pady=(7, 12))
        folder_actions = tk.Frame(folder_card, bg=CARD)
        folder_actions.pack(fill="x")
        self.button(folder_actions, "Choose folder", self.choose_folder).pack(side="left", padx=(0, 9))
        self.button(folder_actions, "Open folder", self.open_folder).pack(side="left")

        share_card = self.card(outer)
        share_card.pack(fill="x", pady=(0, 14))
        share_top = tk.Frame(share_card, bg=CARD)
        share_top.pack(fill="x")
        share_copy = tk.Frame(share_top, bg=CARD)
        share_copy.pack(side="left", fill="x", expand=True)
        self.label(share_copy, "SEND FROM THIS LAPTOP", bg=CARD, fg=MUTED, font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        self.label(share_copy, textvariable=self.shared_var, bg=CARD, fg=INK, font=("Helvetica", 12), anchor="w").pack(fill="x", pady=(7, 0))
        self.button(share_top, "Choose files", self.share_files, primary=True).pack(side="right", padx=(14, 0))

        activity_card = self.card(outer)
        activity_card.pack(fill="both", expand=True)
        self.label(activity_card, "ACTIVITY", bg=CARD, fg=MUTED, font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        self.label(activity_card, textvariable=self.activity_var, bg=CARD, font=("Helvetica", 13, "bold"), anchor="w").pack(fill="x", pady=(8, 8))
        self.recent_list = tk.Listbox(activity_card, height=4, bd=0, highlightthickness=0, bg=CARD, fg=MUTED, font=("Helvetica", 12), activestyle="none", selectbackground=SOFT, selectforeground=INK)
        self.recent_list.pack(fill="both", expand=True)

        self.label(outer, "Keep this app open while transferring. Files stay on your local network.", fg=MUTED, font=("Helvetica", 11), anchor="center").pack(fill="x", pady=(15, 0))

    def new_server(self):
        server = None
        for port in range(8765, 8776):
            try:
                server = WiFiDropServer(("0.0.0.0", port), Handler)
                break
            except OSError:
                continue
        if server is None:
            raise OSError("No available local port between 8765 and 8775")
        server.pin = f"{secrets.randbelow(900000) + 100000}"
        server.output_dir = self.destination
        server.verbose = False
        server.received_files = []
        server.received_files_lock = threading.Lock()
        server.shared_files = {}
        server.shared_files_lock = threading.Lock()
        return server

    def start_server(self):
        try:
            self.destination.mkdir(parents=True, exist_ok=True)
            self.server = self.new_server()
            self.server_thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.25}, daemon=True)
            self.server_thread.start()
            addresses = local_ipv4_addresses()
            host = addresses[0] if addresses else "127.0.0.1"
            self.url = f"http://{host}:{self.server.server_port}/?pin={self.server.pin}"
            self.link_var.set(self.url)
            self.status_var.set("● Ready")
            self.render_qr()
        except OSError as error:
            self.status_var.set("Could not start")
            messagebox.showerror(APP_NAME, f"WiFi Drop could not start.\n\n{error}")

    def render_qr(self):
        try:
            import qrcode
            from PIL import ImageTk

            image = qrcode.make(self.url).resize((104, 104))
            self.qr_photo = ImageTk.PhotoImage(image)
            self.qr_label.configure(image=self.qr_photo, width=104, height=104)
        except (ImportError, tk.TclError):
            self.qr_label.configure(text="Same\nWi-Fi", fg=GREEN, font=("Helvetica", 11, "bold"), width=10, height=5)

    def copy_link(self):
        if not self.url:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.url)
        self.root.update()
        self.status_var.set("✓ Link copied")
        self.root.after(1800, lambda: self.status_var.set("● Ready"))

    def open_preview(self):
        if self.url:
            webbrowser.open(self.url)

    def choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=str(self.destination), title="Choose where received files are saved")
        if not chosen:
            return
        destination = Path(chosen).resolve()
        try:
            destination.mkdir(parents=True, exist_ok=True)
            save_destination(destination)
        except OSError as error:
            messagebox.showerror(APP_NAME, f"That folder cannot be used.\n\n{error}")
            return
        self.destination = destination
        self.folder_var.set(str(destination))
        if self.server:
            self.server.output_dir = destination

    def open_folder(self):
        self.destination.mkdir(parents=True, exist_ok=True)
        reveal_path(self.destination)

    def share_files(self):
        if not self.server:
            return
        selected = filedialog.askopenfilenames(title="Choose files to share with phones")
        if not selected:
            return
        with self.server.shared_files_lock:
            for value in selected:
                path = Path(value).resolve()
                if path.is_file() and path not in self.server.shared_files.values():
                    self.server.shared_files[secrets.token_urlsafe(10)] = path
            count = len(self.server.shared_files)
        self.shared_var.set(f"{count} file{'s' if count != 1 else ''} available on the phone")

    def poll_activity(self):
        if self.server:
            with UPLOADS_LOCK:
                active = len(UPLOADS)
            with self.server.received_files_lock:
                recent = list(self.server.received_files[:8])
            if active:
                self.activity_var.set(f"Receiving {active} file{'s' if active != 1 else ''}…")
                self.status_var.set("↓ Receiving")
            else:
                self.activity_var.set(f"{len(recent)} file{'s' if len(recent) != 1 else ''} received this session" if recent else "No transfers yet")
                if self.status_var.get() == "↓ Receiving":
                    self.status_var.set("● Ready")
            current_names = [path.name for path in recent if path.exists()]
            existing_names = list(self.recent_list.get(0, tk.END))
            if current_names != existing_names:
                self.recent_list.delete(0, tk.END)
                for name in current_names:
                    self.recent_list.insert(tk.END, f"✓  {name}")
        self.root.after(900, self.poll_activity)

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.root.destroy()


def main():
    if "--self-test" in sys.argv:
        destination = load_destination()
        print(json.dumps({"app": APP_NAME, "default_destination": str(DEFAULT_FOLDER), "destination": str(destination)}))
        return
    root = tk.Tk()
    WiFiDropApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
