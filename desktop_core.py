"""Desktop adaptation of xunichanghuan/mimotion-run (Apache-2.0).

Modified: validation, range selection, local time, errors and cancellation.
See NOTICE.txt for the upstream revision. Credentials stay in memory only.
"""
from __future__ import annotations
import json, random, re, sys, threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote
import requests

PHONE = re.compile(r"^1\d{10}$")
PHONE86 = re.compile(r"^\+861\d{10}$")
EMAIL = re.compile(r"^[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+$")

class MotionError(Exception): pass
class Cancelled(MotionError): pass

@dataclass(frozen=True)
class RunResult:
    user: str
    steps: Optional[int]
    message: str

def mask_user(user: str) -> str:
    if len(user) <= 4: return "***"
    return user[:2] + "***" + user[-2:]

def validate_inputs(user, password, min_step, max_step):
    user = str(user or "").strip(); password = str(password or "")
    if not user or not password: raise ValueError("账号和密码不能为空")
    if not (EMAIL.fullmatch(user) or PHONE.fullmatch(user) or PHONE86.fullmatch(user)):
        raise ValueError("账号请输入邮箱或中国大陆手机号")
    if PHONE.fullmatch(user): user = "+86" + user
    try: lo, hi = int(str(min_step).strip()), int(str(max_step).strip())
    except Exception as e: raise ValueError("步数范围必须是整数") from e
    if lo < 1 or hi < 1 or lo > hi or hi > 100000: raise ValueError("步数范围应为 1 到 100000，且最小值不大于最大值")
    return user, password, lo, hi

def _asset_path():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / "assets" / "band_template.json"

class MotionClient:
    def __init__(self, log: Callable[[str], None] = print, cancel: Optional[threading.Event] = None, session=None):
        self.log = log; self.cancel = cancel or threading.Event(); self.session = session or requests.Session()
        self.headers = {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8", "User-Agent":"MiFit/6.12.0 (MCE16; Android 16; Density/1.5)", "app_name":"com.xiaomi.hm.health"}
    def __enter__(self): return self
    def __exit__(self, *exc):
        close = getattr(self.session, "close", None)
        if close: close()
    def _check(self):
        if self.cancel.is_set(): raise Cancelled("操作已取消")
    def _post(self, url, **kw):
        self._check()
        try: return self.session.post(url, timeout=15, verify=True, allow_redirects=False, **kw)
        except requests.Timeout as e: raise MotionError("请求超时；如果发生在提交阶段，请先确认第三方步数再重试") from e
        except requests.ConnectionError as e: raise MotionError("网络连接失败；如果发生在提交阶段，请先确认第三方步数再重试") from e
        except requests.RequestException as e: raise MotionError("网络请求失败") from e
    def _login_tokens(self, user, password):
        third = "email" if EMAIL.fullmatch(user) else "huami_phone"
        r1 = self._post(f"https://api-user.zepp.com/registrations/{user}/tokens", data={"client_id":"HuaMi","country_code":"CN","json_response":"true","name":user,"password":password,"redirect_uri":"https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html","state":"REDIRECTION","token":"access"}, headers=self.headers)
        if r1.status_code != 200:
            raise MotionError(f"登录第 1 步失败（HTTP {r1.status_code}），请检查账号或稍后再试")
        try:
            code = r1.json()["access"]
            if not isinstance(code, str) or not code: raise ValueError
        except Exception as e: raise MotionError("登录失败：账号或密码不正确") from e
        if EMAIL.fullmatch(user):
            data = {"app_name":"com.xiaomi.hm.health","country_code":"CN","code":code,"device_id":"2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1","device_model":"phone","app_version":"6.5.5","grant_type":"access_token","allow_registration":"false","dn":"api-user.huami.com,api-mifit.huami.com,app-analytics.huami.com","source":"com.xiaomi.hm.health","third_name":third,"os_version":"1.5.0","lang":"zh_CN"}
        else:
            data = {"app_name":"com.xiaomi.hm.health","country_code":"CN","code":code,"device_id":"2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1","device_model":"android_phone","app_version":"6.12.0","grant_type":"access_token","allow_registration":"false","dn":"account.zepp.com,api-user.zepp.com,api-mifit.zepp.com,api-watch.zepp.com,app-analytics.zepp.com,api-analytics.huami.com,auth.zepp.com","source":"com.xiaomi.hm.health","third_name":third}
        r2 = self._post("https://account.zepp.com/v2/client/login", data=data, headers=self.headers)
        if r2.status_code != 200:
            raise MotionError(f"登录第 2 步失败（HTTP {r2.status_code}），服务器未接受登录")
        try:
            info = r2.json()["token_info"]; uid, token = info["user_id"], info["app_token"]
            if (isinstance(uid, bool) or not isinstance(uid, (str, int))
                    or not str(uid).strip() or str(uid).strip() == "0"
                    or not isinstance(token, str) or not token.strip()):
                raise ValueError
        except Exception as e: raise MotionError("登录失败：服务器返回异常") from e
        self._check()
        return uid, token
    def verify_login(self, user, password):
        user, password, _, _ = validate_inputs(user, password, 1, 1)
        self._login_tokens(user, password)
        return RunResult(mask_user(user), None, "登录成功")
    def submit(self, user, password, min_step, max_step):
        user, password, lo, hi = validate_inputs(user, password, min_step, max_step)
        shown = mask_user(user); self.log(f"正在登录 {shown}…")
        uid, token = self._login_tokens(user, password)
        self._check(); steps = random.randint(lo, hi)
        try: template = json.loads(_asset_path().read_text(encoding="utf-8"))
        except Exception as e: raise MotionError("程序资源损坏：找不到步数模板") from e
        today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
        payload = json.loads(json.dumps(template)); payload[0]["date"] = today
        try:
            summary = json.loads(payload[0]["summary"])
            summary["stp"]["ttl"] = steps
            payload[0]["summary"] = json.dumps(summary, separators=(",", ":"))
        except Exception as e: raise MotionError("程序资源损坏：步数模板无效") from e
        body = "userid=" + quote(str(uid)) + "&last_sync_data_time=1628256960&device_type=0&last_deviceid=C4BDB6FFFE2BCA4C&data_json=" + quote(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        self.log(f"正在提交 {steps} 步…")
        r = self._post("https://api-mifit-cn.huami.com/v1/data/band_data.json", params={"t": int(datetime.now().timestamp()*1000)}, data=body, headers={"apptoken":token,"Content-Type":"application/x-www-form-urlencoded"})
        if r.status_code != 200:
            raise MotionError(f"提交未确认（HTTP {r.status_code}），请先查看第三方步数再决定是否重试")
        try: ok = r.json().get("message") == "success"
        except Exception as e: raise MotionError("提交结果无法解析，请先查看第三方步数再决定是否重试") from e
        if not ok: raise MotionError("提交失败，请稍后检查第三方步数")
        return RunResult(shown, steps, "提交成功")
