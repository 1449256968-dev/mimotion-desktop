import json
import threading
import unittest
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

import requests

from desktop_core import Cancelled, MotionClient, MotionError, validate_inputs


class Resp:
    def __init__(self, value, status_code=200): self.value, self.status_code = value, status_code
    def json(self): return self.value


class FakeSession:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs)); item = self.responses.pop(0)
        if isinstance(item, BaseException): raise item
        return item if isinstance(item, Resp) else Resp(item)
    def close(self): pass


def login_ok(): return [{"access": "CODE"}, {"token_info": {"user_id": "42", "app_token": "APP"}}]


class CoreTests(unittest.TestCase):
    def test_validation_and_protocols(self):
        self.assertEqual(validate_inputs(" 13800138000 ", "pw", "100", "200"), ("+8613800138000", "pw", 100, 200))
        self.assertEqual(validate_inputs("a.user@example.com", "pw", 1, 1)[0], "a.user@example.com")
        session = FakeSession(login_ok()); MotionClient(session=session).verify_login("a.user@example.com", "pw")
        self.assertEqual(session.calls[1][1]["data"]["app_version"], "6.5.5")
        self.assertEqual(session.calls[1][1]["data"]["device_model"], "phone")
        self.assertEqual(session.calls[1][1]["headers"]["User-Agent"], "MiFit/6.12.0 (MCE16; Android 16; Density/1.5)")

    def test_invalid_before_request(self):
        for args in [("bad", "pw", 1, 2), ("13800138000", "", 1, 2), ("13800138000", "pw", 0, 2), ("13800138000", "pw", 3, 2), ("13800138000", "pw", 1, 100001)]:
            session = FakeSession([])
            with self.assertRaises(ValueError): MotionClient(session=session).submit(*args)
            self.assertFalse(session.calls)

    def test_payload_date_ttl_encoding_and_secret_safe(self):
        session = FakeSession(login_ok() + [{"message": "success"}]); logs = []
        result = MotionClient(log=logs.append, session=session).submit("13800138000", "SECRET", 12345, 12345)
        self.assertEqual(result.steps, 12345); self.assertEqual(result.user, "+8***00")
        body = session.calls[-1][1]["data"]; encoded = body.split("data_json=", 1)[1]
        self.assertNotIn("%2522", encoded); payload = json.loads(unquote(encoded))
        self.assertEqual(payload[0]["date"], datetime.now(timezone(timedelta(hours=8))).date().isoformat())
        self.assertEqual(json.loads(payload[0]["summary"])["stp"]["ttl"], 12345)
        self.assertNotIn("SECRET", " ".join(logs))

    def test_bad_status_login_never_submits(self):
        for response in [Resp({"access": "CODE"}, 302), Resp({"access": "CODE"}, 500), Resp({"token_info": {"user_id": "", "app_token": "APP"}})]:
            session = FakeSession([response])
            with self.assertRaises(MotionError): MotionClient(session=session).submit("13800138000", "SECRET", 1, 2)
            self.assertLessEqual(len(session.calls), 2)

    def test_cancellation_checkpoints(self):
        event = threading.Event(); event.set(); session = FakeSession([])
        with self.assertRaises(Cancelled): MotionClient(cancel=event, session=session).submit("13800138000", "pw", 1, 2)
        self.assertFalse(session.calls)
        event.clear()
        class Cancelling(FakeSession):
            def post(self, url, **kwargs): out = super().post(url, **kwargs); event.set(); return out
        with self.assertRaises(Cancelled): MotionClient(cancel=event, session=Cancelling(login_ok())).submit("13800138000", "pw", 1, 2)

    def test_cancel_after_success_preserves_success(self):
        event = threading.Event()
        class After(FakeSession):
            def post(self, url, **kwargs):
                out = super().post(url, **kwargs)
                if url.endswith("band_data.json"): event.set()
                return out
        result = MotionClient(cancel=event, session=After(login_ok() + [{"message": "success"}])).submit("13800138000", "pw", 4, 4)
        self.assertEqual(result.message, "提交成功")

    def test_timeout_connection_and_server_errors_safe(self):
        for exc in [requests.Timeout("SECRET"), requests.ConnectionError("SECRET")]:
            session = FakeSession(login_ok() + [exc])
            with self.assertRaises(MotionError) as ctx: MotionClient(session=session).submit("13800138000", "SECRET", 1, 2)
            self.assertNotIn("SECRET", str(ctx.exception)); self.assertIn("提交阶段", str(ctx.exception))
        session = FakeSession(login_ok() + [Resp({"message": "accepted"}, 500)])
        with self.assertRaises(MotionError) as ctx: MotionClient(session=session).submit("13800138000", "pw", 1, 2)
        self.assertIn("第三方步数", str(ctx.exception))

    def test_invalid_token_fields_do_not_verify_or_submit(self):
        for uid, token in [("", "APP"), (0, "APP"), (True, "APP"), ("42", ""), ("42", None)]:
            with self.subTest(uid=uid, token=token):
                session = FakeSession([{"access": "CODE"}, {"token_info": {"user_id": uid, "app_token": token}}])
                with self.assertRaises(MotionError):
                    MotionClient(session=session).verify_login("13800138000", "SECRET")
                self.assertEqual(len(session.calls), 2)

    def test_cancellation_during_second_login_request_is_cancellation(self):
        event = threading.Event()
        class DuringSecond(FakeSession):
            def post(self, url, **kwargs):
                result = super().post(url, **kwargs)
                if len(self.calls) == 2:
                    event.set()
                return result
        session = DuringSecond(login_ok())
        with self.assertRaises(Cancelled):
            MotionClient(cancel=event, session=session).verify_login("13800138000", "pw")
        self.assertEqual(len(session.calls), 2)

    def test_submit_failure_never_returns_success(self):
        for response in [{"message": "failed SECRET"}, ["invalid"], Resp({"message": "success"}, 503)]:
            with self.subTest(response=response):
                session = FakeSession(login_ok() + [response])
                with self.assertRaises(MotionError) as error:
                    MotionClient(session=session).submit("13800138000", "SECRET", 20, 20)
                self.assertNotIn("SECRET", str(error.exception))
                self.assertEqual(len(session.calls), 3)


if __name__ == "__main__": unittest.main()
