# -*- coding: utf-8 -*-
"""
刷步微服务 - 部署到国内服务器
提供 Zepp 刷步相关 HTTP 接口，供国外服务器调用
"""
import sys
import os

# 将父目录加入路径，以便复用根目录的 step_brush.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Optional

from step_brush import (
    ZeppAPI, bindband, check_bindstatus,
    generate_qrcode, QRCODE_AVAILABLE
)
from config import (
    STEP_SERVICE_KEY, APP_DEBUG, CAPTCHA_RETRY_TIMES
)

app = FastAPI(title="Step Service", description="刷步微服务，部署于国内服务器")

# ---------- 认证 ----------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def require_api_key(api_key: str = Security(_api_key_header)):
    if api_key != STEP_SERVICE_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


# ---------- 请求/响应模型 ----------

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    """一次性完成注册尝试（含内部 OCR 重试）"""
    email: str
    password: str
    register_name: str


class RegisterCompleteRequest(BaseModel):
    """用户手动输入验证码后完成注册"""
    email: str
    password: str
    register_name: str
    captcha_key: str
    captcha_code: str


class BindRequest(BaseModel):
    email: str
    password: str
    step: int = 1
    use_proxy: bool = False


class QRCodeRequest(BaseModel):
    userid: str


class BrushRequest(BaseModel):
    email: str
    password: str
    steps: int
    login_token: Optional[str] = None
    app_token: Optional[str] = None
    userid: Optional[str] = None


# ---------- 接口 ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
async def login(req: LoginRequest, _=Security(require_api_key)):
    """登录 Zepp，返回 login_token / app_token / userid"""
    api = ZeppAPI(req.email, req.password, verbose=APP_DEBUG, use_tls=False, use_proxy=True)
    result = api.login()
    if result.get("success"):
        return {
            "success": True,
            "userid": api.userid,
            "login_token": api.login_token,
            "app_token": api.app_token,
            "message": result.get("message", "ok"),
        }
    return {"success": False, "message": result.get("message", "登录失败")}


@app.post("/api/register")
async def register(req: RegisterRequest, _=Security(require_api_key)):
    """
    带 OCR 自动重试的注册接口。

    - 若 OCR 自动识别成功并注册：返回 success=true + 账号 token。
    - 若 OCR 全部失败：返回 need_captcha=true + 验证码图片，让上游请求用户手动输入。
    """
    api = ZeppAPI(verbose=APP_DEBUG, use_tls=False, use_proxy=True)
    last_error = ""

    for retry in range(CAPTCHA_RETRY_TIMES):
        cap_result = api.get_captcha("register", auto_ocr=True)
        if not cap_result.get("success"):
            last_error = cap_result.get("message", "获取验证码失败")
            continue

        captcha_key = cap_result["key"]
        captcha_code = cap_result.get("code", "")

        if captcha_code:
            reg_result = api.register_account(
                req.email, req.password, req.register_name,
                captcha_key, captcha_code,
            )
            if reg_result.get("success"):
                # 注册成功，立即登录获取 token
                return _login_after_register(req.email, req.password)
            last_error = reg_result.get("message", "注册失败")
        else:
            last_error = cap_result.get("ocr_error", "OCR 未识别出结果")

    # OCR 全部失败，返回验证码图片给上游展示给用户
    cap_result = api.get_captcha("register", auto_ocr=False)
    if cap_result.get("success"):
        return {
            "success": False,
            "need_captcha": True,
            "captcha_key": cap_result["key"],
            "captcha_image": cap_result.get("image_base64", ""),
            "message": f"验证码自动识别失败（{last_error}），请手动输入验证码",
        }

    return {
        "success": False,
        "need_captcha": False,
        "message": f"获取验证码失败：{cap_result.get('message', last_error)}",
    }


@app.post("/api/register/complete")
async def register_complete(req: RegisterCompleteRequest, _=Security(require_api_key)):
    """使用用户手动输入的验证码完成注册"""
    api = ZeppAPI(verbose=APP_DEBUG, use_tls=False, use_proxy=True)
    reg_result = api.register_account(
        req.email, req.password, req.register_name,
        req.captcha_key, req.captcha_code,
    )
    if not reg_result.get("success"):
        return {"success": False, "message": reg_result.get("message", "注册失败")}
    return _login_after_register(req.email, req.password)


@app.post("/api/bind")
async def bind(req: BindRequest, _=Security(require_api_key)):
    """通过第三方 nan.run API 绑定手环"""
    result = bindband(
        req.email, req.password,
        step=req.step,
        verbose=APP_DEBUG,
        use_proxy=req.use_proxy,
    )
    return result


@app.get("/api/bind/status")
async def bind_status(userid: str, use_proxy: bool = False, _=Security(require_api_key)):
    """检查微信绑定状态"""
    result = check_bindstatus(userid, verbose=APP_DEBUG, use_proxy=use_proxy)
    return result


@app.post("/api/bind/qrcode")
async def get_qrcode(req: QRCodeRequest, _=Security(require_api_key)):
    """获取微信绑定二维码"""
    api = ZeppAPI(verbose=APP_DEBUG, use_tls=False, use_proxy=False)
    api.userid = req.userid
    result = api.get_qrcode_ticket(req.userid)
    if result.get("success") and QRCODE_AVAILABLE:
        qrcode_b64 = generate_qrcode(result["ticket"])
        return {"success": True, "qrcode": qrcode_b64, "ticket": result["ticket"]}
    return result


@app.post("/api/brush")
async def brush(req: BrushRequest, _=Security(require_api_key)):
    """
    刷步数。
    传入缓存的 login_token / app_token 可跳过重新登录；
    若 token 已过期，内部会自动重新登录并在返回值中带出新 token。
    """
    api = ZeppAPI(req.email, req.password, verbose=APP_DEBUG, use_proxy=True)
    if req.userid:
        api.userid = req.userid
    if req.login_token:
        api.login_token = req.login_token
    if req.app_token:
        api.app_token = req.app_token

    result = api.update_step(req.steps)

    # 若 token 被更新（重新登录），一并返回给上游刷新缓存
    return {
        "success": result.get("success", False),
        "message": result.get("message", ""),
        "login_token": api.login_token,
        "app_token": api.app_token,
        "userid": api.userid,
    }


# ---------- 内部辅助 ----------

def _login_after_register(email: str, password: str) -> dict:
    """注册成功后立即登录，返回 token 信息"""
    login_api = ZeppAPI(email, password, verbose=APP_DEBUG, use_tls=False, use_proxy=True)
    login_result = login_api.login()
    if login_result.get("success"):
        return {
            "success": True,
            "userid": login_api.userid,
            "login_token": login_api.login_token,
            "app_token": login_api.app_token,
            "message": "注册成功",
        }
    # 注册成功但登录失败——仍视为成功，上游稍后再登录
    return {
        "success": True,
        "userid": None,
        "login_token": None,
        "app_token": None,
        "message": "注册成功（登录暂时失败，请稍后重试）",
    }


# ---------- 启动入口 ----------

if __name__ == "__main__":
    import uvicorn
    from config import SERVICE_PORT
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
