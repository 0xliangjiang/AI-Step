# -*- coding: utf-8 -*-
"""
FastAPI 主应用
"""
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from models import init_db, User, Card, SessionLocal, ChatSession, AdWatch, SystemConfig, VipPackage, PaymentOrder, StepRecord, get_db_session
from ai_client import ai_client
from admin import router as admin_router, init_admin
from config import FREE_DAYS, AD_REWARD_DAYS, AD_DAILY_LIMIT, WX_APPID, WX_MCH_ID, REVIEW_MODE
import time
from collections import defaultdict
import threading
from time_utils import get_china_now

app = FastAPI(title="AI智能刷步系统", version="1.0.0")


class BlockSensitiveFilesMiddleware(BaseHTTPMiddleware):
    """阻止对敏感文件的访问"""
    async def dispatch(self, request, call_next):
        path = request.url.path.lower()
        # 阻止敏感文件/目录访问
        blocked_patterns = ['.env', '.git', '.htaccess', '.htpasswd', 'credentials',
                           'config.json', 'secrets', '.pem', '.key', 'docker-compose']
        if any(pattern in path for pattern in blocked_patterns):
            return Response(content="Not Found", status_code=404)
        return await call_next(request)


app.add_middleware(BlockSensitiveFilesMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册后台管理路由
app.include_router(admin_router)

# 存储用户会话消息
user_sessions: Dict[str, List[Dict]] = {}

# 简单的内存限流器（生产环境建议用 Redis）
class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        with self.lock:
            now = time.time()
            # 清理过期记录
            self.requests[key] = [t for t in self.requests[key] if now - t < self.window_seconds]
            if len(self.requests[key]) >= self.max_requests:
                return False
            self.requests[key].append(now)
            return True

rate_limiter = RateLimiter(max_requests=30, window_seconds=60)  # 每分钟最多30次


# 聊天会话管理
def get_user_chat_history(user_key: str, limit: int = 20) -> List[Dict]:
    """从数据库获取用户聊天历史"""
    with get_db_session() as db:
        sessions = db.query(ChatSession).filter(
            ChatSession.user_key == user_key
        ).order_by(ChatSession.created_at.desc()).limit(limit).all()
        # 反转顺序，最早的在前
        sessions.reverse()
        return [{"role": s.role, "content": s.content} for s in sessions]


def save_chat_message(user_key: str, role: str, content: str):
    """保存聊天消息到数据库"""
    with get_db_session() as db:
        msg = ChatSession(user_key=user_key, role=role, content=content)
        db.add(msg)
        # commit 由上下文管理器处理


def cleanup_old_chat_sessions(days: int = 7):
    """清理指定天数前的聊天记录"""
    with get_db_session() as db:
        cutoff = get_china_now() - timedelta(days=days)
        db.query(ChatSession).filter(ChatSession.created_at < cutoff).delete()


class LoginRequest(BaseModel):
    user_key: str


class ChatRequest(BaseModel):
    user_key: str
    message: str


class ChatResponse(BaseModel):
    success: bool
    reply: str
    images: List[Dict] = []
    function_result: Optional[Dict] = None


class UserInfoResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    message: str = ""


class PublicConfigResponse(BaseModel):
    success: bool
    data: dict


class SyncStatusResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    message: str = ""


@app.on_event("startup")
async def startup():
    """启动时初始化数据库和管理员"""
    init_db()
    init_admin()

    # 启动定时任务调度器
    from scheduler import scheduler
    scheduler.start()
    print("[Main] 定时任务调度器已启动")

    # 清理旧的聊天记录
    try:
        cleanup_old_chat_sessions(days=7)
        print("[Main] 已清理7天前的聊天记录")
    except Exception as e:
        print(f"[Main] 清理聊天记录失败: {e}")


@app.post("/api/user/login")
async def user_login(request: LoginRequest):
    """用户登录/注册（卡密作为用户标识）"""
    user_key = request.user_key.strip()
    if not user_key:
        raise HTTPException(status_code=400, detail="卡密不能为空")

    with get_db_session() as db:
        # 访问控制：必须是已存在的卡密
        card = db.query(Card).filter(Card.card_key == user_key).first()
        if not card:
            raise HTTPException(status_code=403, detail="卡密无效，请输入正确卡密")

        user = db.query(User).filter(User.user_key == user_key).first()

        if not user:
            # 新用户注册
            # 计算会员时间：卡密天数 + 免费天数
            total_days = card.days + FREE_DAYS
            vip_expire_at = get_china_now() + timedelta(days=total_days)

            user = User(
                user_key=user_key,
                vip_expire_at=vip_expire_at
            )
            db.add(user)

            # 标记卡密为已使用
            card.status = 'used'
            card.used_by = user_key
            card.used_at = get_china_now()

            print(f"[Login] 新用户 {user_key} 注册，卡密充值 {card.days} 天 + 赠送 {FREE_DAYS} 天，共 {total_days} 天会员")
        else:
            # 更新用户信息（如果 user_key 之前为空）
            if user.user_key is None:
                user.user_key = user_key

    return {"success": True, "user_key": user_key}


@app.get("/api/public/config", response_model=PublicConfigResponse)
async def get_public_config():
    """获取小程序公共配置"""
    return PublicConfigResponse(
        success=True,
        data={
            "review_mode": REVIEW_MODE
        }
    )


class WxLoginRequest(BaseModel):
    code: str
    nickname: str = ""
    avatar_url: str = ""


class UpdateProfileRequest(BaseModel):
    user_key: str
    nickname: str = ""
    avatar_url: str = ""


@app.post("/api/user/wxlogin")
async def wx_login(request: WxLoginRequest):
    """微信小程序登录（使用openid作为用户标识）"""
    import requests

    code = request.code.strip()
    nickname = request.nickname.strip()
    avatar_url = request.avatar_url.strip()
    if not code:
        raise HTTPException(status_code=400, detail="code不能为空")

    # 微信小程序配置（需要替换为你的AppID和AppSecret）
    WX_APPID = os.getenv("WX_APPID", "")
    WX_SECRET = os.getenv("WX_SECRET", "")

    if not WX_APPID or not WX_SECRET:
        # 开发环境：使用code作为openid（方便测试）
        openid = f"dev_{code}"
    else:
        # 生产环境：调用微信API获取openid
        url = f"https://api.weixin.qq.com/sns/jscode2session?appid={WX_APPID}&secret={WX_SECRET}&js_code={code}&grant_type=authorization_code"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if "openid" not in data:
                return {"success": False, "message": f"微信登录失败: {data.get('errmsg', '未知错误')}"}
            openid = data["openid"]
        except Exception as e:
            return {"success": False, "message": f"微信API调用失败: {str(e)}"}

    with get_db_session() as db:
        user = db.query(User).filter(User.user_key == openid).first()

        if not user:
            # 新用户注册，赠送免费天数
            user = User(
                user_key=openid,
                nickname=nickname or None,
                avatar_url=avatar_url or None,
                vip_expire_at=get_china_now() + timedelta(days=FREE_DAYS)
            )
            db.add(user)
            print(f"[WxLogin] 新用户 {openid} 注册，赠送 {FREE_DAYS} 天会员")
        else:
            if nickname:
                user.nickname = nickname
            if avatar_url:
                user.avatar_url = avatar_url

    # 初始化用户会话
    if openid not in user_sessions:
        user_sessions[openid] = []

    return {
        "success": True,
        "openid": openid,
        "nickname": nickname,
        "avatar_url": avatar_url
    }


@app.post("/api/user/profile", response_model=UserInfoResponse)
async def update_user_profile(request: UpdateProfileRequest):
    """更新用户头像昵称"""
    user_key = request.user_key.strip()
    nickname = request.nickname.strip()
    avatar_url = request.avatar_url.strip()

    if not user_key:
        return UserInfoResponse(success=False, message="请先登录")

    with get_db_session() as db:
        user = db.query(User).filter(User.user_key == user_key).first()
        if not user:
            return UserInfoResponse(success=False, message="用户不存在")

        user.nickname = nickname or None
        user.avatar_url = avatar_url or None

        return UserInfoResponse(success=True, data=user.to_dict(), message="保存成功")


@app.get("/api/user/info", response_model=UserInfoResponse)
async def get_user_info(user_key: str = ""):
    """获取用户信息"""
    if not user_key:
        return UserInfoResponse(success=False, message="请先登录")

    with get_db_session() as db:
        user = db.query(User).filter(User.user_key == user_key).first()
        if not user:
            return UserInfoResponse(success=False, message="用户不存在")

        data = user.to_dict()
        # 计算剩余天数
        if user.vip_expire_at:
            remaining = (user.vip_expire_at - get_china_now()).days
            data["remaining_days"] = max(0, remaining)
        else:
            data["remaining_days"] = 0

        return UserInfoResponse(success=True, data=data)


def _parse_sync_log_message(raw_message: str) -> Dict[str, str]:
    def sanitize(text: str) -> str:
        if not text:
            return ""
        replacements = {
            "刷步": "状态更新",
            "刷到": "更新到",
            "用户未注册设备": "当前账号还没有完成设备准备",
            "用户未完成绑定": "当前账号还没有完成设备连接",
            "刷步失败": "状态更新未完成",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    if not raw_message:
        return {
            "status_text": "状态更新中",
            "mode_text": "按计划更新",
            "detail": "最近一次状态记录已生成"
        }

    if raw_message.startswith("scheduled_sync|"):
        parts = raw_message.split("|", 3)
        status = parts[1] if len(parts) > 1 else ""
        execution_mode = parts[2] if len(parts) > 2 else ""
        detail = parts[3] if len(parts) > 3 else ""
        return {
            "status_text": "已完成" if status == "success" else "稍后重试",
            "mode_text": "补充更新" if execution_mode == "补执行" else "按计划更新",
            "detail": sanitize(detail) or ("本次状态已完成更新" if status == "success" else "本次状态暂未完成更新")
        }

    return {
        "status_text": "状态更新中",
        "mode_text": "记录已生成",
        "detail": sanitize(raw_message)
    }


@app.get("/api/user/sync-status", response_model=SyncStatusResponse)
async def get_user_sync_status(user_key: str = ""):
    if not user_key:
        return SyncStatusResponse(success=False, message="请先登录")

    from scheduler import scheduler, get_beijing_time

    with get_db_session() as db:
        user = db.query(User).filter(User.user_key == user_key).first()
        if not user:
            return SyncStatusResponse(success=False, message="用户不存在")

        task = scheduler.get_task(user_key)
        log_rows = db.query(StepRecord).filter(
            StepRecord.user_key == user_key,
            StepRecord.message.like("scheduled_sync|%")
        ).order_by(StepRecord.created_at.desc()).limit(10).all()

        next_sync_at = scheduler._next_scan_time(get_beijing_time()).strftime("%Y-%m-%d %H:%M:%S")
        logs = []
        for row in log_rows:
            parsed = _parse_sync_log_message(row.message)
            logs.append({
                "status_text": parsed["status_text"],
                "mode_text": parsed["mode_text"],
                "detail": parsed["detail"],
                "steps": row.steps,
                "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else None
            })

        if task:
            last_result_text = "已完成"
            if task.get("last_error"):
                last_result_text = "稍后重试"
            elif task.get("last_success_at"):
                last_result_text = "已完成"
            status_text = {"active": "已开启", "paused": "已暂停"}.get(task.get("status"), "状态更新中")
            data = {
                "has_task": True,
                "status_text": status_text,
                "last_result_text": last_result_text,
                "target_steps": task.get("target_steps", 0),
                "time_range": f"{task.get('start_hour')}:00-{task.get('end_hour')}:00",
                "current_progress": f"{task.get('current_steps', 0)}/{task.get('target_steps', 0)}",
                "last_success_at": task.get("last_success_at"),
                "last_attempt_at": task.get("last_attempt_at"),
                "last_detail": _parse_sync_log_message(task.get("last_error") or "").get("detail") or "最近一次更新状态正常",
                "consecutive_failures": task.get("consecutive_failures", 0),
                "next_sync_at": next_sync_at,
                "logs": logs
            }
            return SyncStatusResponse(success=True, data=data)

        return SyncStatusResponse(success=True, data={
            "has_task": False,
            "status_text": "未开启",
            "last_result_text": "未设置",
            "target_steps": 0,
            "time_range": "--",
            "current_progress": "0/0",
            "last_success_at": None,
            "last_attempt_at": None,
            "last_detail": "当前还没有同步安排",
            "consecutive_failures": 0,
            "next_sync_at": next_sync_at,
            "logs": logs
        })


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    if REVIEW_MODE:
        return ChatResponse(success=False, reply="当前版本暂未开放此功能")

    user_key = request.user_key.strip()
    message = request.message.strip()

    if not user_key or not message:
        raise HTTPException(status_code=400, detail="参数不能为空")

    # 限流检查
    if not rate_limiter.is_allowed(user_key):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    # 从数据库获取用户历史消息
    messages = get_user_chat_history(user_key, limit=20)

    # 调用 AI
    result = ai_client.chat(user_key, messages, message)
    function_result = result.get("function_result") or {}
    if not result.get("success", False):
        print(
            f"[Chat] failed user_key={user_key} message={message} "
            f"reply={result.get('reply')} function_result={function_result}"
        )

    # 保存消息到数据库
    save_chat_message(user_key, "user", message)
    save_chat_message(user_key, "assistant", result.get("reply", ""))

    return ChatResponse(
        success=result.get("success", False),
        reply=result.get("reply", ""),
        images=result.get("images", []),
        function_result=result.get("function_result")
    )


# ==================== 广告相关接口 - 暂时隐藏 ====================
# class AdWatchResponse(BaseModel):
#     success: bool
#     message: str
#     reward_days: int = 0
#     daily_count: int = 0
#     daily_limit: int = 0
#     vip_expire_at: Optional[str] = None
#
#
# def get_ad_reward_config() -> tuple:
#     """获取广告奖励配置（优先从数据库读取，否则使用默认配置）"""
#     with get_db_session() as db:
#         reward_days_config = db.query(SystemConfig).filter(
#             SystemConfig.config_key == "ad_reward_days"
#         ).first()
#         daily_limit_config = db.query(SystemConfig).filter(
#             SystemConfig.config_key == "ad_daily_limit"
#         ).first()
#
#         reward_days = int(reward_days_config.config_value) if reward_days_config else AD_REWARD_DAYS
#         daily_limit = int(daily_limit_config.config_value) if daily_limit_config else AD_DAILY_LIMIT
#
#         return reward_days, daily_limit
#
#
# @app.get("/api/user/ad-config")
# async def get_ad_config():
#     """获取广告奖励配置"""
#     reward_days, daily_limit = get_ad_reward_config()
#     return {
#         "success": True,
#         "reward_days": reward_days,
#         "daily_limit": daily_limit
#     }
#
#
# @app.get("/api/user/ad-status", response_model=AdWatchResponse)
# async def get_ad_status(user_key: str = ""):
#     """获取用户今日观看广告状态"""
#     if not user_key:
#         return AdWatchResponse(success=False, message="请先登录")
#
#     today = datetime.now().strftime("%Y-%m-%d")
#     reward_days, daily_limit = get_ad_reward_config()
#
#     with get_db_session() as db:
#         # 查询今日观看次数
#         today_count = db.query(AdWatch).filter(
#             AdWatch.user_key == user_key,
#             AdWatch.watch_date == today
#         ).count()
#
#         # 查询用户信息
#         user = db.query(User).filter(User.user_key == user_key).first()
#
#         return AdWatchResponse(
#             success=True,
#             message="获取成功",
#             daily_count=today_count,
#             daily_limit=daily_limit,
#             reward_days=reward_days,
#             vip_expire_at=user.vip_expire_at.strftime("%Y-%m-%d %H:%M:%S") if user and user.vip_expire_at else None
#         )
#
#
# @app.post("/api/user/watch-ad", response_model=AdWatchResponse)
# async def watch_ad(user_key: str = ""):
#     """观看广告奖励会员天数"""
#     if not user_key:
#         return AdWatchResponse(success=False, message="请先登录")
#
#     today = datetime.now().strftime("%Y-%m-%d")
#     reward_days, daily_limit = get_ad_reward_config()
#
#     with get_db_session() as db:
#         # 查询今日观看次数
#         today_count = db.query(AdWatch).filter(
#             AdWatch.user_key == user_key,
#             AdWatch.watch_date == today
#         ).count()
#
#         # 检查是否超过每日限制
#         if today_count >= daily_limit:
#             return AdWatchResponse(
#                 success=False,
#                 message=f"今日观看次数已达上限（{daily_limit}次），请明天再来",
#                 daily_count=today_count,
#                 daily_limit=daily_limit
#             )
#
#         # 获取用户信息
#         user = db.query(User).filter(User.user_key == user_key).first()
#         if not user:
#             return AdWatchResponse(success=False, message="用户不存在")
#
#         # 计算新的会员过期时间
#         if user.vip_expire_at and user.vip_expire_at > datetime.now():
#             new_expire = user.vip_expire_at + timedelta(days=reward_days)
#         else:
#             new_expire = datetime.now() + timedelta(days=reward_days)
#
#         # 更新用户会员时间
#         user.vip_expire_at = new_expire
#
#         # 记录观看记录
#         ad_watch = AdWatch(
#             user_key=user_key,
#             watch_date=today,
#             reward_days=reward_days
#         )
#         db.add(ad_watch)
#
#         print(f"[AdWatch] 用户 {user_key} 观看广告，奖励 {reward_days} 天，新过期时间: {new_expire}")
#
#         return AdWatchResponse(
#             success=True,
#             message=f"观看成功，获得 {reward_days} 天会员",
#             reward_days=reward_days,
#             daily_count=today_count + 1,
#             daily_limit=daily_limit,
#             vip_expire_at=new_expire.strftime("%Y-%m-%d %H:%M:%S")
#         )
# ==================== 广告相关接口结束 ====================


# ==================== 支付相关 ====================

from payment import wechat_pay, generate_order_no


class PackageResponse(BaseModel):
    success: bool
    data: List[dict] = []
    message: str = ""


class CreateOrderRequest(BaseModel):
    user_key: str
    package_id: int


class OrderResponse(BaseModel):
    success: bool
    message: str = ""
    order_no: Optional[str] = None
    pay_params: Optional[dict] = None


async def _build_package_response():
    if REVIEW_MODE:
        return PackageResponse(
            success=False,
            message="当前版本暂未开放购买功能"
        )

    with get_db_session() as db:
        packages = db.query(VipPackage).filter(
            VipPackage.status == 1
        ).order_by(VipPackage.sort_order.asc()).all()

        return PackageResponse(
            success=True,
            data=[p.to_dict() for p in packages]
        )


@app.get("/api/packages", response_model=PackageResponse)
async def get_packages():
    """获取VIP套餐列表"""
    return await _build_package_response()


@app.get("/api/vip/packages", response_model=PackageResponse)
async def get_vip_packages():
    """获取VIP套餐列表（兼容备用路径）"""
    return await _build_package_response()


@app.get("/api/membership/options", response_model=PackageResponse)
async def get_membership_options():
    """获取会员套餐列表（避开线上被拦截的历史路径）"""
    return await _build_package_response()


@app.post("/api/pay/create", response_model=OrderResponse)
async def create_payment_order(request: CreateOrderRequest):
    """创建支付订单"""
    if REVIEW_MODE:
        return OrderResponse(success=False, message="当前版本暂未开放购买功能")

    if not request.user_key:
        return OrderResponse(success=False, message="请先登录")

    with get_db_session() as db:
        # 获取套餐信息
        package = db.query(VipPackage).filter(
            VipPackage.id == request.package_id,
            VipPackage.status == 1
        ).first()

        if not package:
            return OrderResponse(success=False, message="套餐不存在")

        # 生成订单号
        order_no = generate_order_no()

        # 创建订单
        order = PaymentOrder(
            order_no=order_no,
            user_key=request.user_key,
            package_id=package.id,
            package_name=package.name,
            days=package.days,
            amount=package.price,
            status="pending"
        )
        db.add(order)
        # 先 flush，使订单进入持久化状态，后续更新/删除都不会触发 session 状态异常
        db.flush()

        # 调用微信支付下单
        result = wechat_pay.create_jsapi_order(
            order_no=order_no,
            amount=package.price,
            description=f"智问AI-{package.name}",
            openid=request.user_key  # 小程序用户使用openid
        )

        if result.get("success"):
            # 更新prepay_id
            order.prepay_id = result.get("prepay_id")

            # 获取小程序支付参数
            pay_params = wechat_pay.get_jsapi_params(result.get("prepay_id"))

            print(f"[Payment] 创建订单成功: {order_no}, 用户: {request.user_key}, 套餐: {package.name}")

            return OrderResponse(
                success=True,
                message="下单成功",
                order_no=order_no,
                pay_params=pay_params
            )
        else:
            # 下单失败，删除订单
            db.delete(order)
            return OrderResponse(
                success=False,
                message=result.get("message", "下单失败")
            )


@app.get("/api/pay/query/{order_no}")
async def query_payment_order(order_no: str, user_key: str = ""):
    """查询订单状态，不做最终入账"""
    if REVIEW_MODE:
        return {"success": False, "message": "当前版本暂未开放购买功能"}

    if not user_key:
        return {"success": False, "message": "请先登录"}

    with get_db_session() as db:
        order = db.query(PaymentOrder).filter(
            PaymentOrder.order_no == order_no
        ).first()

        if not order:
            return {"success": False, "message": "订单不存在"}

        if order.user_key != user_key:
            return {"success": False, "message": "无权查看该订单"}

        remote_status = None
        remote_trade_state_desc = ""

        # 如果订单待支付，主动查询微信，但不在这里做最终入账
        if order.status == "pending":
            result = wechat_pay.query_order(order_no)
            if result.get("success"):
                remote_status = result.get("trade_state")
                remote_trade_state_desc = result.get("trade_state_desc") or ""

        return {
            "success": True,
            "status": order.status,
            "remote_status": remote_status,
            "remote_trade_state_desc": remote_trade_state_desc,
            "order": order.to_dict()
        }


@app.post("/api/pay/notify")
async def payment_notify(request: Request):
    """微信支付回调"""
    body = await request.body()
    xml_data = body.decode('utf-8')

    print(f"[Payment] 收到回调: {xml_data}")

    # 解析回调数据
    result = wechat_pay.parse_notify(xml_data)

    if not result.get("success"):
        print(f"[Payment] 回调验签失败: {result.get('message')}")
        return Response(content=wechat_pay.fail_response(result.get("message")), media_type="application/xml")

    data = result.get("data")

    # 验证支付结果
    if data.get("result_code") != "SUCCESS":
        return Response(content=wechat_pay.fail_response("支付失败"), media_type="application/xml")

    order_no = data.get("out_trade_no")
    transaction_id = data.get("transaction_id")
    callback_appid = data.get("appid")
    callback_mch_id = data.get("mch_id")
    callback_total_fee = data.get("total_fee")

    with get_db_session() as db:
        order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()

        if not order:
            print(f"[Payment] 订单不存在: {order_no}")
            return Response(content=wechat_pay.fail_response("订单不存在"), media_type="application/xml")

        # 已处理过的订单直接返回成功
        if order.status == "paid":
            return Response(content=wechat_pay.success_response(), media_type="application/xml")

        # 回调关键字段校验，避免错单或串单到账
        if callback_appid != WX_APPID:
            print(f"[Payment] 回调appid不匹配: {order_no}, callback={callback_appid}, local={WX_APPID}")
            return Response(content=wechat_pay.fail_response("appid不匹配"), media_type="application/xml")

        if callback_mch_id != WX_MCH_ID:
            print(f"[Payment] 回调mch_id不匹配: {order_no}, callback={callback_mch_id}, local={WX_MCH_ID}")
            return Response(content=wechat_pay.fail_response("mch_id不匹配"), media_type="application/xml")

        if str(order.amount) != str(callback_total_fee):
            print(
                f"[Payment] 回调金额不匹配: {order_no}, callback={callback_total_fee}, local={order.amount}"
            )
            return Response(content=wechat_pay.fail_response("金额不匹配"), media_type="application/xml")

        # 原子更新订单状态，确保并发场景下只有一个请求能完成最终入账
        paid_at = get_china_now()
        updated_rows = db.query(PaymentOrder).filter(
            PaymentOrder.id == order.id,
            PaymentOrder.status == "pending"
        ).update({
            PaymentOrder.status: "paid",
            PaymentOrder.transaction_id: transaction_id,
            PaymentOrder.paid_at: paid_at,
        }, synchronize_session=False)

        if updated_rows == 0:
            return Response(content=wechat_pay.success_response(), media_type="application/xml")

        order.status = "paid"
        order.transaction_id = transaction_id
        order.paid_at = paid_at

        # 增加用户会员时间
        user = db.query(User).filter(User.user_key == order.user_key).first()
        if user:
            if user.vip_expire_at and user.vip_expire_at > get_china_now():
                user.vip_expire_at = user.vip_expire_at + timedelta(days=order.days)
            else:
                user.vip_expire_at = get_china_now() + timedelta(days=order.days)

            print(f"[Payment] 支付成功(回调): {order_no}, 用户: {order.user_key}, 增加 {order.days} 天")

    return Response(content=wechat_pay.success_response(), media_type="application/xml")


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
