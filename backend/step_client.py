# -*- coding: utf-8 -*-
"""
刷步微服务 HTTP 客户端
国外服务器通过此客户端调用部署在国内的 step_service
"""
import requests
from typing import Optional

from config import STEP_SERVICE_URL, STEP_SERVICE_KEY, APP_DEBUG, REQUEST_TIMEOUT


class StepClient:
    """刷步微服务客户端"""

    def __init__(self):
        self.base_url = STEP_SERVICE_URL.rstrip("/")
        self.headers = {"X-API-Key": STEP_SERVICE_KEY}
        self.timeout = REQUEST_TIMEOUT

    def _post(self, path: str, data: dict) -> dict:
        try:
            resp = requests.post(
                f"{self.base_url}{path}",
                json=data,
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "刷步服务请求超时，请稍后重试"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "无法连接到刷步服务，请检查网络配置"}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "message": f"刷步服务请求失败: {e}"}
        except Exception as e:
            return {"success": False, "message": f"刷步服务异常: {e}"}

    def _get(self, path: str, params: dict = None) -> dict:
        try:
            resp = requests.get(
                f"{self.base_url}{path}",
                params=params,
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "刷步服务请求超时，请稍后重试"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "无法连接到刷步服务，请检查网络配置"}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "message": f"刷步服务请求失败: {e}"}
        except Exception as e:
            return {"success": False, "message": f"刷步服务异常: {e}"}

    def health(self) -> bool:
        """检查刷步服务是否可用"""
        try:
            resp = requests.get(
                f"{self.base_url}/health",
                headers=self.headers,
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def login(self, email: str, password: str) -> dict:
        """
        登录 Zepp 账号。

        Returns:
            {"success": bool, "userid": str, "login_token": str, "app_token": str, "message": str}
        """
        return self._post("/api/login", {"email": email, "password": password})

    def register(self, email: str, password: str, register_name: str) -> dict:
        """
        注册 Zepp 账号（带 OCR 自动重试）。

        Returns:
            成功: {"success": True, "userid": str, "login_token": str, "app_token": str}
            需人工验证码: {"success": False, "need_captcha": True, "captcha_key": str, "captcha_image": str}
            错误: {"success": False, "need_captcha": False, "message": str}
        """
        return self._post("/api/register", {
            "email": email,
            "password": password,
            "register_name": register_name,
        })

    def register_complete(
        self,
        email: str,
        password: str,
        register_name: str,
        captcha_key: str,
        captcha_code: str,
    ) -> dict:
        """
        使用用户手动输入的验证码完成注册。

        Returns:
            {"success": bool, "userid": str, "login_token": str, "app_token": str}
        """
        return self._post("/api/register/complete", {
            "email": email,
            "password": password,
            "register_name": register_name,
            "captcha_key": captcha_key,
            "captcha_code": captcha_code,
        })

    def bind(self, email: str, password: str, step: int = 1, use_proxy: bool = False) -> dict:
        """
        通过 nan.run 绑定手环。

        Returns:
            {"success": bool, "userid": str, "message": str}
        """
        return self._post("/api/bind", {
            "email": email,
            "password": password,
            "step": step,
            "use_proxy": use_proxy,
        })

    def bind_status(self, userid: str, use_proxy: bool = False) -> dict:
        """
        检查微信绑定状态。

        Returns:
            {"success": bool, "is_bound": bool, "message": str}
        """
        return self._get("/api/bind/status", {"userid": userid, "use_proxy": use_proxy})

    def get_qrcode(self, userid: str) -> dict:
        """
        获取微信绑定二维码。

        Returns:
            {"success": bool, "qrcode": str (base64), "ticket": str}
        """
        return self._post("/api/bind/qrcode", {"userid": userid})

    def brush(
        self,
        email: str,
        password: str,
        steps: int,
        login_token: Optional[str] = None,
        app_token: Optional[str] = None,
        userid: Optional[str] = None,
    ) -> dict:
        """
        刷步数。传入缓存 token 可跳过重新登录；token 过期时自动重登录。

        Returns:
            {"success": bool, "message": str, "login_token": str, "app_token": str, "userid": str}
        """
        return self._post("/api/brush", {
            "email": email,
            "password": password,
            "steps": steps,
            "login_token": login_token,
            "app_token": app_token,
            "userid": userid,
        })


# 全局单例
step_client = StepClient()
