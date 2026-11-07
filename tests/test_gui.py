"""Offline GUI tests for the Tk wrapper.

These tests only exercise the UI state machine.  Fake clients never make network
requests, so the suite is safe to run on a developer machine.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

try:
    import tkinter as tk
    from tkinter import messagebox
    from desktop_app import DesktopApp
    from desktop_core import Cancelled, MotionError, RunResult
except Exception:  # pragma: no cover - gives a useful skip on minimal Python installs
    tk = None


class FakeClient:
    mode = "success"
    calls = []
    gate = None

    def __init__(self, log=None, cancel=None):
        self.log = log or (lambda _line: None)
        self.cancel = cancel

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def verify_login(self, user, password):
        type(self).calls.append(("verify", user, password))
        self.log("测试客户端已完成验证")
        if self.mode == "error":
            raise MotionError("登录失败（测试）")
        if self.mode == "cancel":
            raise Cancelled("操作已取消")
        return RunResult("+86***1234", None, "登录成功（测试）")

    def submit(self, user, password, low, high):
        type(self).calls.append(("submit", user, password, low, high))
        if self.mode == "wait":
            # Let the test request cancellation while the background worker is alive.
            while not self.cancel.is_set():
                time.sleep(0.005)
            raise Cancelled("操作已取消")
        if self.mode == "error":
            raise MotionError("提交失败（测试）")
        if self.mode == "cancel":
            raise Cancelled("操作已取消")
        return RunResult("+86***1234", low, "提交成功（测试）")


@unittest.skipIf(tk is None, "Tkinter is not available")
class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:  # headless CI is a legitimate environment
            raise unittest.SkipTest(f"Tk display unavailable: {exc}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        if cls.root.winfo_exists():
            cls.root.destroy()

    def setUp(self):
        FakeClient.mode = "success"
        FakeClient.calls = []
        FakeClient.gate = None
        self.temp = tempfile.TemporaryDirectory()
        self.config = Path(self.temp.name) / "settings.json"
        self.app = DesktopApp(self.root, client_factory=FakeClient, config_path=self.config)
        self.app.user.set("13800138000")
        self.app.password.set("secret-value")

    def tearDown(self):
        self.app.closed = True
        if self.app.poll_id:
            try:
                self.root.after_cancel(self.app.poll_id)
            except tk.TclError:
                pass
        for child in list(self.root.winfo_children()):
            child.destroy()
        self.temp.cleanup()

    def pump(self, seconds=1.0):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.root.update()
            if not self.app.busy and not self.app.events.qsize():
                return
            time.sleep(0.01)
        self.root.update()

    def test_default_is_not_remembered_and_password_is_not_saved(self):
        self.assertFalse(self.app.remember.get())
        self.app._save()
        self.assertFalse(self.config.exists())
        self.app.remember.set(True)
        self.app._save()
        saved = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(saved["user"], "13800138000")
        self.assertNotIn("password", saved)
        self.assertNotIn("secret-value", self.config.read_text(encoding="utf-8"))

    def test_uncheck_remember_deletes_saved_file(self):
        self.app.remember.set(True)
        self.app._save()
        self.assertTrue(self.config.exists())
        self.app.remember.set(False)
        self.app._remember_changed()
        self.assertFalse(self.config.exists())

    def test_show_password_switches_entry_mask(self):
        self.assertEqual(self.app.password_entry.cget("show"), "●")
        self.app.show_password.set(True)
        self.app._toggle_password()
        self.assertEqual(self.app.password_entry.cget("show"), "")
        self.app.show_password.set(False)
        self.app._toggle_password()
        self.assertEqual(self.app.password_entry.cget("show"), "●")

    def test_verify_does_not_require_valid_step_range(self):
        self.app.minimum.set("not a number")
        self.app.maximum.set("also invalid")
        self.app._start("verify")
        self.pump()
        self.assertEqual(FakeClient.calls[0][0], "verify")
        self.assertEqual(self.app.status.get(), "登录验证成功")

    def test_success_runs_in_background_and_updates_status(self):
        self.app.minimum.set("12345")
        self.app.maximum.set("12345")
        self.app._start("submit")
        self.assertTrue(self.app.busy)
        self.pump()
        self.assertFalse(self.app.busy)
        self.assertIn("提交成功", self.app.status.get())
        self.assertEqual(FakeClient.calls[0][3:], (12345, 12345))

    def test_error_is_displayed_without_freezing(self):
        FakeClient.mode = "error"
        self.app._start("submit")
        self.pump()
        self.assertFalse(self.app.busy)
        self.assertEqual(self.app.status.get(), "操作未完成 · 请查看日志")
        self.assertIn("提交失败（测试）", self.app.log_text.get("1.0", "end"))
        self.assertNotIn("secret-value", self.app.log_text.get("1.0", "end"))

    def test_invalid_input_does_not_start_client(self):
        self.app.user.set("not-an-account")
        shown = []
        original = messagebox.showerror
        messagebox.showerror = lambda *args, **kwargs: shown.append(args[1])
        try:
            self.app._start("submit")
        finally:
            messagebox.showerror = original
        self.assertFalse(self.app.busy)
        self.assertEqual(FakeClient.calls, [])
        self.assertTrue(shown)

    def test_cancel_waiting_operation_reaches_idle_state(self):
        FakeClient.mode = "wait"
        self.app._start("submit")
        deadline = time.monotonic() + 1
        while not self.app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.app._cancel()
        self.pump()
        self.assertFalse(self.app.busy)
        self.assertEqual(self.app.status.get(), "已取消")


if __name__ == "__main__":
    unittest.main()
