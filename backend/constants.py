# -*- coding: utf-8 -*-
"""
常量定义 - API URL、请求头等
"""

# Zepp API URLs
ZEPP_API_BASE = "https://api-user.zepp.com"
ZEPP_ACCOUNT_BASE = "https://account.huami.com"
ZEPP_ACCOUNT_CN = "https://account-cn.huami.com"
ZEPP_MIFIT_API = "https://api-mifit-cn.huami.com"
ZEPP_WEIXIN_API = "https://weixin.amazfit.com"
HUAMI_API_BASE = "https://api-user.huami.com"

# 登录相关URL
URL_REGISTRATIONS_TOKENS = f"{ZEPP_API_BASE}/v2/registrations/tokens"
URL_CLIENT_LOGIN = f"{ZEPP_ACCOUNT_BASE}/v2/client/login"
URL_APP_TOKENS = f"{ZEPP_ACCOUNT_CN}/v1/client/app_tokens"

# 注册相关URL
URL_REGISTRATIONS = f"{HUAMI_API_BASE}/registrations"
URL_CLIENT_REGISTER = f"{ZEPP_ACCOUNT_BASE}/v1/client/register"

# 验证码URL
URL_CAPTCHA = f"{HUAMI_API_BASE}/captcha"

# 二维码绑定URL
URL_BIND_QRCODE = f"{ZEPP_WEIXIN_API}/v1/bind/qrcode.json"
URL_BIND_INFO = f"{ZEPP_WEIXIN_API}/v1/info/users.json"

# 刷步URL
URL_BAND_DATA = f"{ZEPP_MIFIT_API}/v1/data/band_data.json"

# 第三方API
URL_THIRD_PARTY_API = "https://api.nan.run/api/xiaomisport"

# 通用请求头
HEADERS_COMMON = {
    "user-agent": "MiFit6.14.0 (M2007J1SC; Android 12; Density/2.75)",
    "app_name": "com.xiaomi.hm.health",
    "appname": "com.xiaomi.hm.health",
    "appplatform": "android_phone",
}

HEADERS_LOGIN = {
    **HEADERS_COMMON,
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-hm-ekv": "1",
    "hm-privacy-ceip": "false"
}

HEADERS_REGISTER = {
    "app_name": "com.huami.webapp",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
}

HEADERS_APP_TOKEN = {
    "User-Agent": "MiFit/5.3.0 (iPhone; iOS 14.7.1; Scale/3.00)"
}

# 重定向URL
REDIRECT_URI = "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html"

# 响应消息
MSG_SUCCESS = "成功"
MSG_LOGIN_FAILED = "登录失败"
MSG_REGISTER_FAILED = "注册失败"
MSG_CAPTCHA_FAILED = "获取验证码失败"
MSG_BIND_FAILED = "绑定失败"
MSG_BRUSH_FAILED = "刷步失败"
