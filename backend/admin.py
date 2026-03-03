# -*- coding: utf-8 -*-
"""
后台管理 API
"""
import hashlib
import time
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import func

from models import Admin, User, StepRecord, SessionLocal, init_db, get_db_session, ScheduledTask, Card, SystemConfig, VipPackage, PaymentOrder
from config import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_SECRET_KEY, APP_DEBUG, AD_REWARD_DAYS, AD_DAILY_LIMIT

# 配置日志
logger = logging.getLogger(__name__)
if APP_DEBUG:
    logging.basicConfig(level=logging.DEBUG)

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
    with get_db_session() as db:
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


@router.get("/users/{user_key}", response_model=UserDetailResponse)
async def get_user_detail(user_key: str, _: str = Depends(verify_token)):
    """获取用户详情"""
    with get_db_session() as db:
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


class BindQRResponse(BaseModel):
    success: bool
    qrcode: Optional[str] = None
    message: str = ""


@router.get("/users/{user_key}/bindqr", response_model=BindQRResponse)
async def get_user_bindqr(user_key: str, _: str = Depends(verify_token)):
    """获取用户绑定二维码"""
    with get_db_session() as db:
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


class BindStatusResponse(BaseModel):
    success: bool
    is_bound: bool = False
    message: str = ""


@router.post("/users/{user_key}/bindstatus", response_model=BindStatusResponse)
async def refresh_bindstatus(user_key: str, _: str = Depends(verify_token)):
    """刷新用户绑定状态"""
    with get_db_session() as db:
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
        api = ZeppAPI(verbose=APP_DEBUG, use_tls=False, use_proxy=True)
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
            try:
                with get_db_session() as db:
                    user = User(
                        user_key=None,  # 批量注册的账户，user_key 为空，等待分配
                        zepp_email=email,
                        zepp_password=password,
                        zepp_userid=user_data['userid'],
                        bind_status=0
                    )
                    db.add(user)

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
                logger.error(f"[BatchRegister] 保存用户失败: {e}")
                failed += 1
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
    with get_db_session() as db:
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


# ==================== 统计数据 ====================

class StatsResponse(BaseModel):
    success: bool
    data: dict = {}


@router.get("/stats", response_model=StatsResponse)
async def get_stats(_: str = Depends(verify_token)):
    """获取统计数据"""
    with get_db_session() as db:
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


# ==================== 系统配置 ====================

class ConfigResponse(BaseModel):
    success: bool
    data: dict = {}
    message: str = ""


class UpdateConfigRequest(BaseModel):
    admin_password: Optional[str] = None
    ad_reward_days: Optional[int] = None
    ad_daily_limit: Optional[int] = None


def get_or_create_config(db, key: str, default_value: str, description: str = "") -> SystemConfig:
    """获取或创建配置项"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if not config:
        config = SystemConfig(
            config_key=key,
            config_value=str(default_value),
            description=description
        )
        db.add(config)
    return config


@router.get("/config", response_model=ConfigResponse)
async def get_config(_: str = Depends(verify_token)):
    """获取系统配置"""
    with get_db_session() as db:
        # 获取广告奖励配置
        ad_reward_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "ad_reward_days"
        ).first()
        ad_limit_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "ad_daily_limit"
        ).first()

        ad_reward_days = int(ad_reward_config.config_value) if ad_reward_config else AD_REWARD_DAYS
        ad_daily_limit = int(ad_limit_config.config_value) if ad_limit_config else AD_DAILY_LIMIT

        return ConfigResponse(
            success=True,
            data={
                "admin_username": ADMIN_USERNAME,
                "ai_provider": "minimax/glm",
                "ad_reward_days": ad_reward_days,
                "ad_daily_limit": ad_daily_limit
            }
        )


@router.put("/config", response_model=ConfigResponse)
async def update_config(request: UpdateConfigRequest, _: str = Depends(verify_token)):
    """更新系统配置"""
    with get_db_session() as db:
        if request.ad_reward_days is not None:
            if request.ad_reward_days < 1 or request.ad_reward_days > 30:
                return ConfigResponse(success=False, message="广告奖励天数范围为 1-30")
            config = get_or_create_config(db, "ad_reward_days", AD_REWARD_DAYS, "观看广告奖励天数")
            config.config_value = str(request.ad_reward_days)

        if request.ad_daily_limit is not None:
            if request.ad_daily_limit < 1 or request.ad_daily_limit > 20:
                return ConfigResponse(success=False, message="每日观看次数范围为 1-20")
            config = get_or_create_config(db, "ad_daily_limit", AD_DAILY_LIMIT, "每日观看广告次数上限")
            config.config_value = str(request.ad_daily_limit)

        return ConfigResponse(
            success=True,
            message="配置更新成功"
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

    with get_db_session() as db:
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


@router.post("/scheduled-tasks/{task_id}/pause", response_model=TaskActionResponse)
async def pause_scheduled_task(task_id: int, _: str = Depends(verify_token)):
    """暂停定时任务"""
    with get_db_session() as db:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return TaskActionResponse(success=False, message="任务不存在")

        task.status = "paused"

        return TaskActionResponse(success=True, message="任务已暂停")


@router.post("/scheduled-tasks/{task_id}/resume", response_model=TaskActionResponse)
async def resume_scheduled_task(task_id: int, _: str = Depends(verify_token)):
    """恢复定时任务"""
    with get_db_session() as db:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return TaskActionResponse(success=False, message="任务不存在")

        task.status = "active"

        return TaskActionResponse(success=True, message="任务已恢复")


@router.post("/scheduled-tasks/{task_id}/cancel", response_model=TaskActionResponse)
async def cancel_scheduled_task(task_id: int, _: str = Depends(verify_token)):
    """取消定时任务"""
    with get_db_session() as db:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return TaskActionResponse(success=False, message="任务不存在")

        task.status = "cancelled"

        return TaskActionResponse(success=True, message="任务已取消")


@router.delete("/scheduled-tasks/{task_id}", response_model=TaskActionResponse)
async def delete_scheduled_task(task_id: int, _: str = Depends(verify_token)):
    """删除定时任务"""
    with get_db_session() as db:
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            return TaskActionResponse(success=False, message="任务不存在")

        db.delete(task)

        return TaskActionResponse(success=True, message="任务已删除")


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

    try:
        with get_db_session() as db:
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

            return GenerateCardsResponse(
                success=True,
                message=f"成功生成 {request.count} 张 {request.days} 天卡密",
                cards=cards
            )
    except Exception as e:
        return GenerateCardsResponse(success=False, message=f"生成失败: {str(e)}")


@router.get("/cards", response_model=CardListResponse)
async def get_cards(
    page: int = 1,
    page_size: int = 20,
    status: str = "",
    _: str = Depends(verify_token)
):
    """获取卡密列表"""
    with get_db_session() as db:
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


@router.delete("/cards/{card_id}", response_model=TaskActionResponse)
async def delete_card(card_id: int, _: str = Depends(verify_token)):
    """删除卡密"""
    with get_db_session() as db:
        card = db.query(Card).filter(Card.id == card_id).first()
        if not card:
            return TaskActionResponse(success=False, message="卡密不存在")

        if card.status == "used":
            return TaskActionResponse(success=False, message="已使用的卡密不能删除")

        db.delete(card)

        return TaskActionResponse(success=True, message="卡密已删除")


# ==================== VIP套餐管理 ====================

class PackageRequest(BaseModel):
    name: str
    days: int
    price: int
    original_price: Optional[int] = None
    sort_order: int = 0
    status: int = 1


class PackageListResponse(BaseModel):
    success: bool
    data: List[dict] = []
    total: int = 0


@router.get("/packages", response_model=PackageListResponse)
async def get_packages(_: str = Depends(verify_token)):
    """获取套餐列表"""
    with get_db_session() as db:
        packages = db.query(VipPackage).order_by(VipPackage.sort_order.asc()).all()
        return PackageListResponse(
            success=True,
            data=[p.to_dict() for p in packages],
            total=len(packages)
        )


@router.post("/packages", response_model=TaskActionResponse)
async def create_package(request: PackageRequest, _: str = Depends(verify_token)):
    """创建套餐"""
    with get_db_session() as db:
        package = VipPackage(
            name=request.name,
            days=request.days,
            price=request.price,
            original_price=request.original_price,
            sort_order=request.sort_order,
            status=request.status
        )
        db.add(package)
        return TaskActionResponse(success=True, message="套餐创建成功")


@router.put("/packages/{package_id}", response_model=TaskActionResponse)
async def update_package(package_id: int, request: PackageRequest, _: str = Depends(verify_token)):
    """更新套餐"""
    with get_db_session() as db:
        package = db.query(VipPackage).filter(VipPackage.id == package_id).first()
        if not package:
            return TaskActionResponse(success=False, message="套餐不存在")

        package.name = request.name
        package.days = request.days
        package.price = request.price
        package.original_price = request.original_price
        package.sort_order = request.sort_order
        package.status = request.status

        return TaskActionResponse(success=True, message="套餐更新成功")


@router.delete("/packages/{package_id}", response_model=TaskActionResponse)
async def delete_package(package_id: int, _: str = Depends(verify_token)):
    """删除套餐"""
    with get_db_session() as db:
        package = db.query(VipPackage).filter(VipPackage.id == package_id).first()
        if not package:
            return TaskActionResponse(success=False, message="套餐不存在")

        db.delete(package)
        return TaskActionResponse(success=True, message="套餐已删除")


# ==================== 订单管理 ====================

class OrderListResponse(BaseModel):
    success: bool
    data: List[dict] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


@router.get("/orders", response_model=OrderListResponse)
async def get_orders(
    page: int = 1,
    page_size: int = 20,
    status: str = "",
    user_key: str = "",
    _: str = Depends(verify_token)
):
    """获取订单列表"""
    with get_db_session() as db:
        query = db.query(PaymentOrder)

        if status:
            query = query.filter(PaymentOrder.status == status)

        if user_key:
            query = query.filter(PaymentOrder.user_key.contains(user_key))

        total = query.count()

        orders = query.order_by(PaymentOrder.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return OrderListResponse(
            success=True,
            data=[o.to_dict() for o in orders],
            total=total,
            page=page,
            page_size=page_size
        )


# ==================== 初始化管理员 ====================

def init_admin():
    """初始化管理员账号"""
    with get_db_session() as db:
        admin = db.query(Admin).filter(Admin.username == ADMIN_USERNAME).first()
        if not admin:
            admin = Admin(
                username=ADMIN_USERNAME,
                password=hash_password(ADMIN_PASSWORD)
            )
            db.add(admin)
            logger.info(f"[Admin] 初始化管理员账号: {ADMIN_USERNAME}")
            print(f"[Admin] 初始化管理员账号: {ADMIN_USERNAME}")
