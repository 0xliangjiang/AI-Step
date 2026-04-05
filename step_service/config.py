# -*- coding: utf-8 -*-
"""
刷步微服务配置
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# 服务安全密钥（调用方必须携带此 key）
STEP_SERVICE_KEY = os.getenv("STEP_SERVICE_KEY", "change-me-please")

# 代理配置（用于 Zepp 登录/注册）
PROXY_API_URL = os.getenv("PROXY_API_URL", "")
USE_PROXY = os.getenv("USE_PROXY", "true").lower() in ("1", "true", "yes", "on")

# Zepp 加密密钥
ZEPP_AES_KEY = os.getenv("ZEPP_AES_KEY", "xeNtBVqzDc6tuNTh")
ZEPP_AES_IV = os.getenv("ZEPP_AES_IV", "MAAAYAAAAAAAAABg")

# 第三方 nan.run API 密钥
NANRUN_API_KEY = os.getenv("NANRUN_API_KEY", "")

# 调试模式
APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() in ("1", "true", "yes", "on")

# 验证码 OCR 重试次数
CAPTCHA_RETRY_TIMES = int(os.getenv("CAPTCHA_RETRY_TIMES", "5"))

# 服务监听端口
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8001"))
