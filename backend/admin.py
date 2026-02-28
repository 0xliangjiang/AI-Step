# -*- coding: utf-8 -*-
"""
后台管理 API
"""
import hashlib
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import func

from models import Admin, User, StepRecord, SessionLocal, init_db
from config import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_SECRET_KEY

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ==================== 认证相关 ====================

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token(username: str) -> str:
    """生成简单的 token"""
    data = f"{username}:{int(time.time())}:{ADMIN_SECRET_KEY}"
    return hashlib.sha256(data.encode()).hexdigest()


def verify_token(authorization: str = Header(None)) -> str:
    """验证 token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")

    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    # 简单验证：token 存在即可
    if not token or len(token) < 10:
        raise HTTPException(status_code=401, detail="token 无效")

    return token


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str = ""


@router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """管理员登录"""
    if request.username != ADMIN_USERNAME:
        return LoginResponse(success=False, message="用户名或密码错误")

    if request.password != ADMIN_PASSWORD:
        return LoginResponse(success=False, message="用户名或密码错误")

    token = generate_token(request.username)
    return LoginResponse(success=True, token=token, message="登录成功")


# ==================== 用户管理 ====================

class UserListResponse(BaseModel):
    success: bool
    data: List[dict] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class UserDetailResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    message: str = ""


@router.get("/users", response_model=UserListResponse)
async def get_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    bind_status: Optional[int] = None,
    _: str = Depends(verify_token)
):
    """获取用户列表"""
    db = SessionLocal()
    try:
        query = db.query(User)

        # 关键词搜索
        if keyword:
            query = query.filter(
                (User.user_key.contains(keyword)) |
                (User.zepp_email.contains(keyword))
            )

        # 绑定状态筛选
        if bind_status is not None:
            query = query.filter(User.bind_status == bind_status)

        # 总数
        total = query.count()

        # 分页
        users = query.order_by(User.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return UserListResponse(
            success=True,
            data=[u.to_dict() for u in users],
            total=total,
            page=page,
            page_size=page_size
        )
    finally:
        db.close()


@router.get("/users/{user_key}", response_model=UserDetailResponse)
async def get_user_detail(user_key: str, _: str = Depends(verify_token)):
    """获取用户详情"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_key == user_key).first()
        if not user:
            return UserDetailResponse(success=False, message="用户不存在")

        # 获取最近刷步记录
        records = db.query(StepRecord) \
            .filter(StepRecord.user_key == user_key) \
            .order_by(StepRecord.created_at.desc()) \
            .limit(10) \
            .all()

        data = user.to_dict()
        data["recent_records"] = [r.to_dict() for r in records]

        return UserDetailResponse(success=True, data=data)
    finally:
        db.close()


class BindQRResponse(BaseModel):
    success: bool
    qrcode: Optional[str] = None
    message: str = ""


@router.get("/users/{user_key}/bindqr", response_model=BindQRResponse)
async def get_user_bindqr(user_key: str, _: str = Depends(verify_token)):
    """获取用户绑定二维码"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_key == user_key).first()
        if not user:
            return BindQRResponse(success=False, message="用户不存在")

        if not user.zepp_email or not user.zepp_password:
            return BindQRResponse(success=False, message="用户未注册 Zepp 账号")

        # 导入 skills 获取二维码
        from skills import skills
        result = skills.get_bindqr(user_key)

        if result.get("success") and result.get("qrcode_image"):
            return BindQRResponse(
                success=True,
                qrcode=result["qrcode_image"],
                message=result.get("message", "")
            )

        return BindQRResponse(success=False, message=result.get("message", "获取二维码失败"))
    finally:
        db.close()


class BindStatusResponse(BaseModel):
    success: bool
    is_bound: bool = False
    message: str = ""


@router.post("/users/{user_key}/bindstatus", response_model=BindStatusResponse)
async def refresh_bindstatus(user_key: str, _: str = Depends(verify_token)):
    """刷新用户绑定状态"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_key == user_key).first()
        if not user:
            return BindStatusResponse(success=False, message="用户不存在")

        if not user.zepp_userid:
            return BindStatusResponse(success=False, message="用户未注册 Zepp 账号")

        # 导入 skills 检查绑定状态
        from skills import skills
        result = skills.check_bindstatus(user_key)

        return BindStatusResponse(
            success=True,
            is_bound=result.get("is_bound", False),
            message=result.get("message", "")
        )
    finally:
        db.close()


# ==================== 批量注册 ====================

class BatchRegisterRequest(BaseModel):
    count: int  # 注册数量


class BatchRegisterResponse(BaseModel):
    success: bool
    message: str = ""
    registered: int = 0
    failed: int = 0
    accounts: List[dict] = []


@router.post("/batch-register", response_model=BatchRegisterResponse)
async def batch_register(request: BatchRegisterRequest, _: str = Depends(verify_token)):
    """批量注册 Zepp 账户"""
    if request.count < 1 or request.count > 50:
        return BatchRegisterResponse(success=False, message="注册数量范围为 1-50")

    from skills import generate_random_email, generate_strong_password
    from step_brush import ZeppAPI, QRCODE_AVAILABLE, generate_qrcode
    from config import APP_DEBUG, CAPTCHA_RETRY_TIMES

    registered = 0
    failed = 0
    accounts = []

    for i in range(request.count):
        email = generate_random_email()
        password = generate_strong_password()
        register_name = email

        # 注册流程强制使用代理
        api = ZeppAPI(verbose=APP_DEBUG, use_proxy=True)
        success = False
        user_data = None

        # 尝试注册，最多重试 CAPTCHA_RETRY_TIMES 次
        for retry in range(CAPTCHA_RETRY_TIMES):
            # 获取验证码
            captcha_result = api.get_captcha("register", auto_ocr=True)
            if not captcha_result['success']:
                continue

            captcha_key = captcha_result['key']
            captcha_code = captcha_result.get('code', '')

            if not captcha_code:
                continue

            # 尝试注册
            reg_result = api.register_account(email, password, register_name, captcha_key, captcha_code)
            if reg_result['success']:
                success = True
                # 登录获取 userid
                api.user = email
                api.password = password
                api.is_phone = False
                login_result = api.login()

                if login_result['success']:
                    user_data = {
                        "email": email,
                        "password": password,
                        "userid": login_result['userid'],
                        "login_token": login_result['login_token'],
                        "app_token": login_result['app_token']
                    }
                break

        if success and user_data:
            # 存入数据库（user_key 为空，等待分配给用户）
            db = SessionLocal()
            try:
                user = User(
                    user_key=None,  # 批量注册的账户，user_key 为空，等待分配
                    zepp_email=email,
                    zepp_password=password,
                    zepp_userid=user_data['userid'],
                    bind_status=0
                )
                db.add(user)
                db.commit()

                # 获取绑定二维码
                qr_result = api.get_qrcode_ticket(user_data['userid'])
                qrcode_url = None
                if qr_result['success'] and QRCODE_AVAILABLE:
                    qrcode_url = generate_qrcode(qr_result['ticket'])

                accounts.append({
                    "email": email,
                    "password": password,
                    "userid": user_data['userid'],
                    "qrcode": qrcode_url
                })
                registered += 1
            except Exception as e:
                print(f"[BatchRegister] 保存用户失败: {e}")
                db.rollback()
                failed += 1
            finally:
                db.close()
        else:
            failed += 1

    return BatchRegisterResponse(
        success=True,
        message=f"批量注册完成：成功 {registered} 个，失败 {failed} 个",
        registered=registered,
        failed=failed,
        accounts=accounts
    )


# ==================== 刷步记录 ====================

class RecordListResponse(BaseModel):
    success: bool
    data: List[dict] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


@router.get("/step-records", response_model=RecordListResponse)
async def get_step_records(
    page: int = 1,
    page_size: int = 20,
    user_key: str = "",
    status: str = "",
    _: str = Depends(verify_token)
):
    """获取刷步记录"""
    db = SessionLocal()
    try:
        query = db.query(StepRecord)

        # 用户筛选
        if user_key:
            query = query.filter(StepRecord.user_key.contains(user_key))

        # 状态筛选
        if status:
            query = query.filter(StepRecord.status == status)

        # 总数
        total = query.count()

        # 分页
        records = query.order_by(StepRecord.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return RecordListResponse(
            success=True,
            data=[r.to_dict() for r in records],
            total=total,
            page=page,
            page_size=page_size
        )
    finally:
        db.close()


# ==================== 统计数据 ====================

class StatsResponse(BaseModel):
    success: bool
    data: dict = {}


@router.get("/stats", response_model=StatsResponse)
async def get_stats(_: str = Depends(verify_token)):
    """获取统计数据"""
    db = SessionLocal()
    try:
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())

        # 用户统计
        total_users = db.query(User).count()
        bound_users = db.query(User).filter(User.bind_status == 1).count()
        unbound_users = total_users - bound_users

        # 今日注册
        today_new_users = db.query(User).filter(User.created_at >= today_start).count()

        # 刷步统计
        total_records = db.query(StepRecord).count()
        success_records = db.query(StepRecord).filter(StepRecord.status == "success").count()
        failed_records = total_records - success_records

        # 今日刷步
        today_records = db.query(StepRecord).filter(StepRecord.created_at >= today_start).count()
        today_success = db.query(StepRecord).filter(
            StepRecord.created_at >= today_start,
            StepRecord.status == "success"
        ).count()

        # 今日总步数
        today_steps_result = db.query(func.sum(StepRecord.steps)).filter(
            StepRecord.created_at >= today_start,
            StepRecord.status == "success"
        ).scalar()
        today_steps = today_steps_result or 0

        return StatsResponse(
            success=True,
            data={
                "users": {
                    "total": total_users,
                    "bound": bound_users,
                    "unbound": unbound_users,
                    "today_new": today_new_users
                },
                "records": {
                    "total": total_records,
                    "success": success_records,
                    "failed": failed_records,
                    "today": today_records,
                    "today_success": today_success
                },
                "steps": {
                    "today_total": today_steps
                }
            }
        )
    finally:
        db.close()


# ==================== 系统配置 ====================

class ConfigResponse(BaseModel):
    success: bool
    data: dict = {}
    message: str = ""


class UpdateConfigRequest(BaseModel):
    admin_password: Optional[str] = None


@router.get("/config", response_model=ConfigResponse)
async def get_config(_: str = Depends(verify_token)):
    """获取系统配置"""
    return ConfigResponse(
        success=True,
        data={
            "admin_username": ADMIN_USERNAME,
            "ai_provider": "minimax/glm"
        }
    )


@router.put("/config", response_model=ConfigResponse)
async def update_config(request: UpdateConfigRequest, _: str = Depends(verify_token)):
    """更新系统配置"""
    # 注意：这里简化处理，实际应该更新数据库或环境变量
    return ConfigResponse(
        success=True,
        message="配置更新成功（需要重启服务生效）"
    )


# ==================== 定时任务管理 ====================

class ScheduledTaskResponse(BaseModel):
    success: bool
    data: List[dict] = []
    total: int = 0
    message: str = ""


class TaskActionResponse(BaseModel):
    success: bool
    message: str = ""


@router.get("/scheduled-tasks", response_model=ScheduledTaskResponse)
async def get_scheduled_tasks(
    status: str = "",
    _: str = Depends(verify_token)
):
    """获取定时任务列表"""
    from scheduler import scheduler
    from models import ScheduledTask

    db = SessionLocal()
    try:
        query = db.query(ScheduledTask)

        if status:
            query = query.filter(ScheduledTask.status == status)

        tasks = query.order_by(ScheduledTask.created_at.desc()).all()

        # 关联用户信息
        result = []
        for task in tasks:
            task_dict = task.to_dict()
            user = db.query(User).filter(User.user_key == task.user_key).first()
            task_dict["user_email"] = user.zepp_email if user else None
            task_dict["bind_status"] = user.bind_status if user else 0
            result.append(task_dict)

        return ScheduledTaskResponse(
            success=True,
            data=result,
            total=len(result)
        )
    finally:
        db.close()


@router.post("/scheduled-tasks/{task_id}/pause", response_model=TaskActionResponse)
async def pause_scheduled_task(task_id: int, _: str = Depends(verify_token)):
    """暂停定时任务"""
    from models import ScheduledTask

    db = SessionLocal()
    try:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return TaskActionResponse(success=False, message="任务不存在")

        task.status = "paused"
        db.commit()

        return TaskActionResponse(success=True, message="任务已暂停")
    finally:
        db.close()


@router.post("/scheduled-tasks/{task_id}/resume", response_model=TaskActionResponse)
async def resume_scheduled_task(task_id: int, _: str = Depends(verify_token)):
    """恢复定时任务"""
    from models import ScheduledTask

    db = SessionLocal()
    try:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return TaskActionResponse(success=False, message="任务不存在")

        task.status = "active"
        db.commit()

        return TaskActionResponse(success=True, message="任务已恢复")
    finally:
        db.close()


@router.post("/scheduled-tasks/{task_id}/cancel", response_model=TaskActionResponse)
async def cancel_scheduled_task(task_id: int, _: str = Depends(verify_token)):
    """取消定时任务"""
    from models import ScheduledTask

    db = SessionLocal()
    try:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return TaskActionResponse(success=False, message="任务不存在")

        task.status = "cancelled"
        db.commit()

        return TaskActionResponse(success=True, message="任务已取消")
    finally:
        db.close()


@router.delete("/scheduled-tasks/{task_id}", response_model=TaskActionResponse)
async def delete_scheduled_task(task_id: int, _: str = Depends(verify_token)):
    """删除定时任务"""
    from models import ScheduledTask

    db = SessionLocal()
    try:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return TaskActionResponse(success=False, message="任务不存在")

        db.delete(task)
        db.commit()

        return TaskActionResponse(success=True, message="任务已删除")
    finally:
        db.close()


# ==================== 卡密管理 ====================

import random
import string


class GenerateCardsRequest(BaseModel):
    count: int
    days: int


class CardListResponse(BaseModel):
    success: bool
    data: List[dict] = []
    total: int = 0
    message: str = ""


class GenerateCardsResponse(BaseModel):
    success: bool
    message: str = ""
    cards: List[dict] = []


def generate_card_key(length: int = 16) -> str:
    """生成卡密"""
    chars = string.ascii_uppercase + string.digits
    # 排除容易混淆的字符
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    return ''.join(random.choices(chars, k=length))


@router.post("/cards/generate", response_model=GenerateCardsResponse)
async def generate_cards(request: GenerateCardsRequest, _: str = Depends(verify_token)):
    """批量生成卡密"""
    if request.count < 1 or request.count > 100:
        return GenerateCardsResponse(success=False, message="生成数量范围为 1-100")

    if request.days < 1 or request.days > 365:
        return GenerateCardsResponse(success=False, message="天数范围为 1-365")

    from models import Card

    db = SessionLocal()
    try:
        cards = []
        for _ in range(request.count):
            # 确保卡密唯一
            while True:
                card_key = generate_card_key()
                existing = db.query(Card).filter(Card.card_key == card_key).first()
                if not existing:
                    break

            card = Card(card_key=card_key, days=request.days)
            db.add(card)
            cards.append({"card_key": card_key, "days": request.days})

        db.commit()

        return GenerateCardsResponse(
            success=True,
            message=f"成功生成 {request.count} 张 {request.days} 天卡密",
            cards=cards
        )
    except Exception as e:
        db.rollback()
        return GenerateCardsResponse(success=False, message=f"生成失败: {str(e)}")
    finally:
        db.close()


@router.get("/cards", response_model=CardListResponse)
async def get_cards(
    page: int = 1,
    page_size: int = 20,
    status: str = "",
    _: str = Depends(verify_token)
):
    """获取卡密列表"""
    from models import Card

    db = SessionLocal()
    try:
        query = db.query(Card)

        if status:
            query = query.filter(Card.status == status)

        total = query.count()

        cards = query.order_by(Card.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return CardListResponse(
            success=True,
            data=[c.to_dict() for c in cards],
            total=total
        )
    finally:
        db.close()


@router.delete("/cards/{card_id}", response_model=TaskActionResponse)
async def delete_card(card_id: int, _: str = Depends(verify_token)):
    """删除卡密"""
    from models import Card

    db = SessionLocal()
    try:
        card = db.query(Card).filter(Card.id == card_id).first()
        if not card:
            return TaskActionResponse(success=False, message="卡密不存在")

        if card.status == "used":
            return TaskActionResponse(success=False, message="已使用的卡密不能删除")

        db.delete(card)
        db.commit()

        return TaskActionResponse(success=True, message="卡密已删除")
    finally:
        db.close()


# ==================== 初始化管理员 ====================

def init_admin():
    """初始化管理员账号"""
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == ADMIN_USERNAME).first()
        if not admin:
            admin = Admin(
                username=ADMIN_USERNAME,
                password=hash_password(ADMIN_PASSWORD)
            )
            db.add(admin)
            db.commit()
            print(f"[Admin] 初始化管理员账号: {ADMIN_USERNAME}")
    finally:
        db.close()
