# -*- coding: utf-8 -*-
"""
FastAPI 主应用
"""
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from models import init_db, User, SessionLocal
from ai_client import ai_client
from admin import router as admin_router, init_admin
from config import FREE_DAYS

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

# 存储用户会话消息
user_sessions: Dict[str, List[Dict]] = {}


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


@app.post("/api/user/login")
async def user_login(request: LoginRequest):
    """用户登录/注册"""
    user_key = request.user_key.strip()
    if not user_key:
        raise HTTPException(status_code=400, detail="用户标识不能为空")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_key == user_key).first()

        if not user:
            # 新用户，创建并赠送免费天数
            user = User(
                user_key=user_key,
                vip_expire_at=datetime.now() + timedelta(days=FREE_DAYS)
            )
            db.add(user)
            db.commit()
            print(f"[Login] 新用户 {user_key} 注册，赠送 {FREE_DAYS} 天会员")
        else:
            # 更新用户信息（如果 user_key 之前为空）
            if user.user_key is None:
                user.user_key = user_key
                db.commit()
    finally:
        db.close()

    # 初始化用户会话
    if user_key not in user_sessions:
        user_sessions[user_key] = []

    return {"success": True, "user_key": user_key}


@app.get("/api/user/info", response_model=UserInfoResponse)
async def get_user_info(user_key: str):
    """获取用户信息"""
    db = SessionLocal()
    try:
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
    finally:
        db.close()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    user_key = request.user_key.strip()
    message = request.message.strip()

    if not user_key or not message:
        raise HTTPException(status_code=400, detail="参数不能为空")

    # 获取用户历史消息
    if user_key not in user_sessions:
        user_sessions[user_key] = []

    messages = user_sessions[user_key]

    # 调用 AI
    result = ai_client.chat(user_key, messages, message)

    # 保存消息历史
    user_sessions[user_key].append({"role": "user", "content": message})
    user_sessions[user_key].append({"role": "assistant", "content": result.get("reply", "")})

    # 限制历史消息数量
    if len(user_sessions[user_key]) > 20:
        user_sessions[user_key] = user_sessions[user_key][-20:]

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
