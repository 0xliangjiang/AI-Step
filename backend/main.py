# -*- coding: utf-8 -*-
"""
FastAPI 主应用
"""
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from models import init_db, User, Card, SessionLocal, ChatSession, get_db_session
from ai_client import ai_client
from admin import router as admin_router, init_admin
from config import FREE_DAYS
import time
from collections import defaultdict
import threading

app = FastAPI(title="AI智能刷步系统", version="1.0.0")

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
        cutoff = datetime.now() - timedelta(days=days)
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


class UserInfoResponse(BaseModel):
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
            vip_expire_at = datetime.now() + timedelta(days=total_days)

            user = User(
                user_key=user_key,
                vip_expire_at=vip_expire_at
            )
            db.add(user)

            # 标记卡密为已使用
            card.status = 'used'
            card.used_by = user_key
            card.used_at = datetime.now()

            print(f"[Login] 新用户 {user_key} 注册，卡密充值 {card.days} 天 + 赠送 {FREE_DAYS} 天，共 {total_days} 天会员")
        else:
            # 更新用户信息（如果 user_key 之前为空）
            if user.user_key is None:
                user.user_key = user_key

    return {"success": True, "user_key": user_key}


@app.get("/api/user/info", response_model=UserInfoResponse)
async def get_user_info(user_key: str):
    """获取用户信息"""
    with get_db_session() as db:
        user = db.query(User).filter(User.user_key == user_key).first()
        if not user:
            return UserInfoResponse(success=False, message="用户不存在")

        data = user.to_dict()
        # 计算剩余天数
        if user.vip_expire_at:
            remaining = (user.vip_expire_at - datetime.now()).days
            data["remaining_days"] = max(0, remaining)
        else:
            data["remaining_days"] = 0

        return UserInfoResponse(success=True, data=data)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
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

    # 保存消息到数据库
    save_chat_message(user_key, "user", message)
    save_chat_message(user_key, "assistant", result.get("reply", ""))

    return ChatResponse(
        success=result.get("success", False),
        reply=result.get("reply", ""),
        images=result.get("images", [])
    )


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
