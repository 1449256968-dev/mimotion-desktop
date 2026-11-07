"""Simple Windows desktop UI for mimotion-run. See NOTICE.txt for attribution."""
from __future__ import annotations

import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from desktop_core import Cancelled, MotionClient, MotionError, validate_inputs

VERSION = "1.0.0"
BG = "#F3F6F8"
INK = "#172C35"
MUTED = "#657780"
ACCENT = "#087F78"


def resource_path(name: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / name


def settings_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MiMotionDesktop" / "settings.json"


class DesktopApp:
    def __init__(self, root: tk.Tk, client_factory=MotionClient, config_path: Path | None = None):
        self.root = root
        self.client_factory = client_factory
        self.config_path = config_path or settings_path()
        self.events: queue.Queue = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.closed = False
        self.poll_id = None
        self.user = tk.StringVar()
        self.password = tk.StringVar()
        self.minimum = tk.StringVar(value="10000")
        self.maximum = tk.StringVar(value="20000")
        self.remember = tk.BooleanVar(value=False)
        self.show_password = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="准备就绪")
        self._configure()
        self._build()
        self._restore()
        self._log("填写运动账号与步数，验证登录后即可提交。")
        self.poll_id = self.root.after(80, self._poll)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _configure(self):
        self.root.title("小米运动 · 桌面助手")
        # Tk fonts follow Windows DPI; window geometry uses physical pixels.
        # Scale both together so display scaling does not squeeze out the log.
        scale = max(1.0, self.root.winfo_fpixels("1i") / 96)
        width = min(round(680 * scale), self.root.winfo_screenwidth() - 40)
        height = min(round(810 * scale), self.root.winfo_screenheight() - round(110 * scale))
        self.root.geometry(f"{width}x{height}+{round(60 * scale)}+{round(20 * scale)}")
        self.root.minsize(min(round(620 * scale), width), min(round(750 * scale), height))
        self.root.configure(bg=BG)
        icon = resource_path("assets/app.ico")
        if icon.exists():
            self.root.iconbitmap(str(icon))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        self.root.tk.call("font", "configure", "TkDefaultFont", "-family", "Microsoft YaHei UI", "-size", 10)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background="white")
        style.configure("TLabel", background=BG, foreground=INK, font=("Microsoft YaHei UI", 10))
        style.configure("Card.TLabel", background="white")
        style.configure("Hint.TLabel", background="white", foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 24, "bold"))
        style.configure("Section.TLabel", background="white", font=("Microsoft YaHei UI", 12, "bold"))
        style.configure("TEntry", padding=(10, 5), fieldbackground="#FAFCFD", foreground=INK, font=("Microsoft YaHei UI", 10))
        style.configure("TCheckbutton", background="white", foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.map("TCheckbutton", background=[("active", "white"), ("disabled", "white")])
        style.configure("TButton", padding=(16, 8), font=("Microsoft YaHei UI", 10))
        style.configure("Accent.TButton", background=ACCENT, foreground="white", borderwidth=0)
        style.map("Accent.TButton", background=[("disabled", "#B0C9C7"), ("active", "#066B65")], foreground=[("disabled", "white")])
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor="#E7EEEE", borderwidth=0)

    def _build(self):
        body = ttk.Frame(self.root, padding=(28, 18, 28, 14))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="MiMotion / 桌面版", foreground=ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(body, text="小米运动助手", style="Title.TLabel").pack(anchor="w", pady=(5, 3))
        ttk.Label(body, text="输入账号，设定步数，一键提交。", foreground=MUTED).pack(anchor="w", pady=(0, 12))

        card = ttk.Frame(body, style="Card.TFrame", padding=16)
        card.pack(fill="x")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text="01  运动账号", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(card, text="手机号 / 邮箱", style="Card.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 3))
        self.user_entry = ttk.Entry(card, textvariable=self.user)
        self.user_entry.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(card, text="密码", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 3))
        self.show_check = ttk.Checkbutton(card, text="显示密码", variable=self.show_password, command=self._toggle_password)
        self.show_check.grid(row=3, column=1, sticky="e", pady=(8, 3))
        self.password_entry = ttk.Entry(card, textvariable=self.password, show="●")
        self.password_entry.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Label(card, text="使用小米运动账号密码（不是小米账号）。", style="Hint.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.remember_check = ttk.Checkbutton(card, text="记住账号与步数设置（不保存密码）", variable=self.remember, command=self._remember_changed)
        self.remember_check.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 10))
        ttk.Separator(card).grid(row=7, column=0, columnspan=2, sticky="ew")
        ttk.Label(card, text="02  目标步数", style="Section.TLabel").grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 8))
        ttk.Label(card, text="最小步数", style="Card.TLabel").grid(row=9, column=0, sticky="w", pady=(0, 3))
        ttk.Label(card, text="最大步数", style="Card.TLabel").grid(row=9, column=1, sticky="w", padx=(10, 0), pady=(0, 3))
        self.min_entry = ttk.Entry(card, textvariable=self.minimum, width=16)
        self.min_entry.grid(row=10, column=0, sticky="ew", padx=(0, 10))
        self.max_entry = ttk.Entry(card, textvariable=self.maximum, width=16)
        self.max_entry.grid(row=10, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(card, text="范围内随机取值；两项填相同数值，可提交固定步数。", style="Hint.TLabel").grid(row=11, column=0, columnspan=2, sticky="w", pady=(6, 0))

        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=(12, 8))
        self.verify_button = ttk.Button(actions, text="验证登录", command=lambda: self._start("verify"))
        self.verify_button.pack(side="left")
        self.submit_button = ttk.Button(actions, text="提交步数", style="Accent.TButton", command=lambda: self._start("submit"))
        self.submit_button.pack(side="left", padx=10)
        self.cancel_button = ttk.Button(actions, text="取消", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="right")
        self.progress = ttk.Progressbar(body, mode="indeterminate", length=100, value=0)
        self.progress.configure(style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 8))
        ttk.Label(body, textvariable=self.status, foreground=ACCENT).pack(anchor="w", pady=(0, 8))

        footer = ttk.Frame(body)
        footer.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Label(footer, text=f"v{VERSION}  ·  需要联网", foreground=MUTED, font=("Microsoft YaHei UI", 9)).pack(side="left")
        ttk.Button(footer, text="使用说明 / 关于", command=self._help, padding=(6, 2)).pack(side="right")
        log_card = ttk.Frame(body, style="Card.TFrame", padding=(12, 9))
        log_card.pack(fill="both", expand=True)
        log_title = ttk.Frame(log_card, style="Card.TFrame")
        log_title.pack(fill="x", pady=(0, 6))
        ttk.Label(log_title, text="运行日志", style="Card.TLabel").pack(side="left")
        self.clear_button = ttk.Button(log_title, text="清空", command=self._clear_log, padding=(6, 2))
        self.clear_button.pack(side="right")
        text_area = ttk.Frame(log_card, style="Card.TFrame")
        text_area.pack(fill="both", expand=True)
        self.log_text = tk.Text(text_area, height=3, wrap="word", font=("Microsoft YaHei UI", 9), bg="white", fg=INK, relief="flat", state="disabled", cursor="arrow", padx=2)
        scroll = ttk.Scrollbar(text_area, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)
        self.inputs = (self.user_entry, self.password_entry, self.min_entry, self.max_entry, self.remember_check)
        self.user_entry.focus_set()

    def _toggle_password(self):
        self.password_entry.configure(show="" if self.show_password.get() else "●")

    def _log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{datetime.now():%H:%M:%S}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _restore(self):
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("remember") is True:
                self.remember.set(True)
                for key, variable in (("user", self.user), ("min_step", self.minimum), ("max_step", self.maximum)):
                    if isinstance(data.get(key), (str, int)):
                        variable.set(str(data[key]))
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            self._log("无法读取上次设置，已使用默认值。")

    def _save(self):
        try:
            if not self.remember.get():
                self.config_path.unlink(missing_ok=True)
                return
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"remember": True, "user": self.user.get().strip(), "min_step": self.minimum.get().strip(), "max_step": self.maximum.get().strip()}
            temporary = self.config_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.config_path)
        except OSError:
            self._log("设置未能保存，仍可继续运行。")

    def _remember_changed(self):
        self._save()

    def _set_busy(self, busy: bool):
        self.busy = busy
        for widget in (*self.inputs, self.verify_button, self.submit_button):
            widget.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _start(self, operation: str):
        if self.busy:
            return
        try:
            # Login verification does not depend on the step fields.
            minimum = self.minimum.get() if operation == "submit" else "1"
            maximum = self.maximum.get() if operation == "submit" else "1"
            args = validate_inputs(self.user.get(), self.password.get(), minimum, maximum)
        except (MotionError, ValueError) as exc:
            messagebox.showerror("请检查输入", str(exc), parent=self.root)
            return
        self._save()
        self.cancel.clear()
        self._set_busy(True)
        self.status.set("正在验证登录…" if operation == "verify" else "正在登录并提交…")
        self._log("开始验证登录。" if operation == "verify" else "开始提交步数。")
        threading.Thread(target=self._worker, args=(operation, args), daemon=True).start()

    def _worker(self, operation, args):
        try:
            with self.client_factory(log=lambda line: self.events.put(("log", line)), cancel=self.cancel) as client:
                result = client.verify_login(*args[:2]) if operation == "verify" else client.submit(*args)
            self.events.put(("success", (operation, result)))
        except Cancelled:
            self.events.put(("cancelled", "操作已取消。"))
        except MotionError as exc:
            self.events.put(("error", str(exc)))
        except Exception:
            # Never dump credential-bearing exception/request objects into UI logs.
            self.events.put(("error", "程序遇到异常，请重启后再试；若已开始提交，请先检查第三方步数。"))

    def _poll(self):
        if self.closed:
            return
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._log(value)
                continue
            self._set_busy(False)
            if kind == "success":
                operation, result = value
                if operation == "verify":
                    self.status.set("登录验证成功")
                else:
                    self.status.set(f"提交成功 · {result.steps:,} 步")
                self._log(result.message)
                if operation == "submit":
                    self._log("请到已绑定的微信 / 支付宝查看同步结果。")
            elif kind == "cancelled":
                self.status.set("已取消")
                self._log(value)
            else:
                self.status.set("操作未完成 · 请查看日志")
                self._log(value)
        self.poll_id = self.root.after(80, self._poll)

    def _cancel(self):
        if not self.busy:
            return
        self.cancel.set()
        self.cancel_button.configure(state="disabled")
        self.status.set("正在取消，等待当前请求结束…")
        self._log("已请求取消；已经发出的提交无法撤回，请以接口结果为准。")

    def _help(self):
        window = tk.Toplevel(self.root)
        window.title("使用说明 / 关于")
        window.geometry("620x540")
        window.transient(self.root)
        text = tk.Text(window, wrap="word", padx=20, pady=16, font=("Microsoft YaHei UI", 10), relief="flat")
        scroll = ttk.Scrollbar(window, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.insert("end", "小米运动桌面助手 v" + VERSION + "\n\n"
                    "1. 输入能以密码登录的小米运动账号（手机号或邮箱）。\n"
                    "2. 点击“验证登录”，这一步不会修改步数。\n"
                    "3. 填写最小 / 最大步数后点击“提交步数”。两项相同即为固定步数。\n"
                    "4. 查看运行日志，再到已绑定的微信或支付宝确认同步。\n\n"
                    "本版为手动单账号工具，需要联网，不依赖 Python 或 GitHub。\n"
                    "密码仅用于本次登录，不写入配置或日志。选中“记住”只保存账号和步数；取消选中会删除保存的设置。\n"
                    "配置位置：" + str(self.config_path) + "\n\n"
                    "取消会在请求间生效，已经发出的提交不能撤回。提交超时或连接中断时，服务端可能已收到，请先查看第三方步数再决定是否重试。\n"
                    "服务端接受提交不代表微信 / 支付宝已完成同步。是否可用取决于上游接口和账号绑定。\n\n")
        for name in ("NOTICE.txt", "LICENSE", "THIRD_PARTY_NOTICES.txt"):
            path = resource_path(name)
            if path.exists():
                text.insert("end", path.read_text(encoding="utf-8") + "\n\n")
        text.configure(state="disabled")

    def _close(self):
        if self.busy:
            messagebox.showinfo("操作进行中", "请等待操作结束，或先点击“取消”。当前请求结束后即可关闭。", parent=self.root)
            return
        self._save()
        self.password.set("")
        self.closed = True
        if self.poll_id:
            self.root.after_cancel(self.poll_id)
        self.root.destroy()


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MiMotion.Desktop.1")
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    DesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
