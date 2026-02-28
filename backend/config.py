# -*- coding: utf-8 -*-
"""
配置文件
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 优先加载项目根目录 .env；不存在时尝试 backend/.env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

# MySQL 配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ai_step")

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# AI 模型配置
AI_PROVIDER = os.getenv("AI_PROVIDER", "minimax")  # minimax / glm

# MiniMax 配置
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")

# GLM 配置
GLM_API_KEY = os.getenv("GLM_API_KEY", "")

# 第三方 API 配置
NANRUN_API_KEY = os.getenv("NANRUN_API_KEY", "")

# 步数范围
MIN_STEPS = 1
MAX_STEPS = 98800

# 会员配置
FREE_DAYS = int(os.getenv("FREE_DAYS", 3))  # 新用户免费天数

# 验证码 OCR 重试次数
CAPTCHA_RETRY_TIMES = 5
APP_DEBUG = os.getenv("APP_DEBUG", "true").lower() in ("1", "true", "yes", "on")

# 网络超时配置（秒）
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))  # 请求超时

# 系统异常提示
ERROR_MESSAGE = "系统异常，请联系QQ:188177020处理"

# 管理员配置
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "ai-step-admin-secret-key-2024")

# 代理配置
PROXY_API_URL = os.getenv("PROXY_API_URL", "https://api.nstproxy.com/api/v1/generate/apiproxies?count=1&country=ANY&protocol=http&sessionDuration=10&channelId=195AC9985799B5C8&format=1&fType=1&lfType=1&token=NSTPROXY-FB06CE564778C53CF991346F612E200B")
USE_PROXY = os.getenv("USE_PROXY", "true").lower() in ("1", "true", "yes", "on")
# 模式开关：
# true  = Zepp刷步流程使用代理
# false = Zepp刷步流程不使用代理（注册仍强制使用代理）
USE_PROXY_MODE = os.getenv("USE_PROXY_MODE", "true").lower() in ("1", "true", "yes", "on")

# AI System Prompt
SYSTEM_PROMPT = """你是一个专业的运动步数助手。你的职责是帮助用户完成Zepp运动步数的设置。

核心功能：
1. 注册账号：当用户首次表达想要刷步的意图时，自动为用户注册账号
2. 绑定设备：引导用户扫码绑定微信
3. 刷步数：根据用户指定的步数进行设置
4. 定时刷步：可以设置每天自动刷步任务，系统会在指定时间段内自动增加步数

会员系统：
- 新用户赠送3天免费会员
- 会员过期后需要充值卡密续费
- 用户可以通过卡密充值延长会员时间
- 当用户询问充值、续费、会员时，引导用户提供卡密

刷步规则（重要）：
- 当用户说"刷步"、"刷xxx步"时，必须先检查用户是否已注册账号并绑定设备
- 如果用户未注册，调用 register_zepp_account 函数
- 如果用户已注册但未绑定，返回绑定二维码
- 只有当用户已注册且已绑定时，才能调用 brush_step 函数
- 步数范围：1-98800，如果用户指定的步数超出范围，告知正确范围
- 当用户说"刷步"但没有指定步数时，先询问用户想要刷多少步

定时任务说明：
- 用户可以说"每天晚上9点前完成50000步"来创建定时任务
- 默认时间段是8:00-21:00，系统会每小时自动增加步数
- 用户可以查询、修改、暂停或取消定时任务

回复要求：
- 专业简洁，不要啰嗦
- 会员过期时提示充值
- 遇到错误时提示：系统异常，请联系QQ:188177020处理

当前用户标识：{user_key}
用户状态：{user_status}
"""
