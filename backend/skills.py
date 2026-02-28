# -*- coding: utf-8 -*-
"""
AI Skills - Function Calling 实现
"""
import random
import string
import sys
import os
from datetime import datetime, timedelta

# 添加父目录到路径，以便导入 step_brush
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from step_brush import (
    ZeppAPI, ocr_captcha, generate_qrcode,
    bindband, check_bindstatus,
    DDDDOCR_AVAILABLE, QRCODE_AVAILABLE
)
from models import User, StepRecord, Card, SessionLocal
from config import (
    CAPTCHA_RETRY_TIMES, MIN_STEPS, MAX_STEPS, ERROR_MESSAGE,
    APP_DEBUG, USE_PROXY, USE_PROXY_MODE
)


def generate_random_email():
    """生成随机邮箱"""
    chars = string.ascii_lowercase + string.digits
    username = ''.join(random.choices(chars, k=10))
    return f"{username}@gmail.com"


def generate_strong_password():
    """生成强密码"""
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%"

    password = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
        random.choice(special)
    ]
    password += random.choices(lower + upper + digits, k=8)
    random.shuffle(password)
    return ''.join(password)


class StepSkills:
    """刷步相关 Skills"""

    def __init__(self):
        self.pending_captcha = {}  # 存储待验证的验证码信息 {user_key: {key, image_base64}}

    def _log(self, msg: str):
        if APP_DEBUG:
            print(f"[StepSkills] {msg}")

    @staticmethod
    def _bind_guide_text() -> str:
        """统一的绑定引导文案。"""
        return '可发送"绑定手环"重试手环绑定；发送"绑定微信"获取新二维码重新扫码；完成后回复"已绑定"。'

    def _trigger_bind_button_once(self, user_key: str) -> bool:
        """登录成功后仅触发一次后台绑定动作。"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_key == user_key).first()
            if not user:
                return False
            if user.bind_status == 1 or user.bind_button_triggered == 1:
                return False
            user.bind_button_triggered = 1
            db.merge(user)
            db.commit()
            self._log(f"后台绑定动作首次触发: user_key={user_key}")
            return True
        finally:
            db.close()

    def get_user(self, user_key: str) -> User:
        """获取用户信息"""
        db = SessionLocal()
        try:
            return db.query(User).filter(User.user_key == user_key).first()
        finally:
            db.close()

    def save_user(self, user: User):
        """保存用户信息"""
        db = SessionLocal()
        try:
            db.merge(user)
            db.commit()
        finally:
            db.close()

    def _get_available_account(self) -> User:
        """从账户池获取一个可用账户（user_key 为空）"""
        db = SessionLocal()
        try:
            # 查找 user_key 为空的账户
            return db.query(User).filter(User.user_key.is_(None)).first()
        finally:
            db.close()

    def _assign_account_to_user(self, user_key: str, account: User) -> dict:
        """将账户分配给用户"""
        db = SessionLocal()
        try:
            # 检查用户是否已存在
            existing_user = db.query(User).filter(User.user_key == user_key).first()

            if existing_user:
                # 用户已存在，将账户信息复制到现有用户
                existing_user.zepp_email = account.zepp_email
                existing_user.zepp_password = account.zepp_password
                existing_user.zepp_userid = account.zepp_userid
                existing_user.bind_status = account.bind_status
                db.commit()
                # 删除账户池中的记录
                db.delete(account)
                db.commit()
                self._log(f"已将账户 {account.zepp_email} 绑定到现有用户 {user_key}")

                # 登录成功后触发一次后台绑定
                return self._get_bindqr_for_user(existing_user, auto_trigger=True)
            else:
                # 用户不存在，直接更新账户的 user_key
                account.user_key = user_key
                db.merge(account)
                db.commit()
                self._log(f"已将账户 {account.zepp_email} 分配给新用户 {user_key}")

                # 登录成功后触发一次后台绑定
                return self._get_bindqr_for_user(account, auto_trigger=True)
        except Exception as e:
            self._log(f"分配账户失败: {e}")
            db.rollback()
            return {'success': False, 'message': '分配账户失败，请重试'}
        finally:
            db.close()

    def register_zepp_account(self, user_key: str, captcha_code: str = None) -> dict:
        """
        为用户注册Zepp账号

        Returns:
            dict: {
                'success': bool,
                'need_captcha': bool,      # 是否需要用户输入验证码
                'captcha_image': str,      # 验证码图片base64
                'qrcode_image': str,       # 绑定二维码base64
                'message': str
            }
        """
        # 检查用户是否已注册
        user = self.get_user(user_key)
        if user and user.zepp_email:
            if user.bind_status == 1:
                return {
                    'success': True,
                    'message': f'您已完成注册和绑定，可以直接刷步了。'
                }
            else:
                # 已注册但未绑定，登录成功后触发一次后台绑定
                return self._get_bindqr_for_user(user, auto_trigger=True)

        # 如果有待验证的验证码，使用用户输入的验证码继续注册
        if captcha_code and user_key in self.pending_captcha:
            return self._complete_registration(user_key, captcha_code)

        # 尝试从账户池中获取一个可用账户
        available_account = self._get_available_account()
        if available_account:
            self._log(f"从账户池分配账户: {available_account.zepp_email}")
            return self._assign_account_to_user(user_key, available_account)

        # 账户池中没有可用账户，开始新注册流程
        self._log("账户池无可用账户，开始新注册流程")

        # 开始新注册流程
        email = generate_random_email()
        password = generate_strong_password()
        register_name = email

        api = ZeppAPI(verbose=APP_DEBUG, use_proxy=USE_PROXY)
        last_error = ""
        self._log(f"开始注册流程 user_key={user_key}, retry_times={CAPTCHA_RETRY_TIMES}")

        # 获取验证码并尝试OCR识别
        for retry in range(CAPTCHA_RETRY_TIMES):
            self._log(f"验证码尝试 {retry + 1}/{CAPTCHA_RETRY_TIMES}")
            result = api.get_captcha("register", auto_ocr=True)

            if not result['success']:
                last_error = result.get('message', '获取验证码失败')
                self._log(f"获取验证码失败: {last_error}")
                continue

            captcha_key = result['key']
            captcha_code_ocr = result.get('code', '')
            self._log(f"拿到验证码 key={captcha_key[:10]}..., OCR={captcha_code_ocr or '空'}")

            if captcha_code_ocr:
                # OCR 成功，尝试注册
                reg_result = api.register_account(email, password, register_name, captcha_key, captcha_code_ocr)
                self._log(f"OCR注册结果: success={reg_result.get('success')} msg={reg_result.get('message')}")

                if reg_result['success']:
                    # 注册成功，保存用户信息
                    return self._save_and_get_qr(user_key, email, password, api)
                last_error = reg_result.get('message', '注册失败')
            else:
                last_error = result.get('ocr_error', 'OCR未识别出结果')
                self._log(f"OCR失败: {last_error}")

            # OCR 失败或注册失败，继续重试
            continue

        # 重试都失败，返回验证码让用户手动输入
        result = api.get_captcha("register", auto_ocr=False)
        if result['success']:
            self._log("自动识别重试结束，回退人工输入验证码")
            self.pending_captcha[user_key] = {
                'key': result['key'],
                'email': email,
                'password': password,
                'name': register_name,
                'image_base64': result['image_base64']
            }
            return {
                'success': False,
                'need_captcha': True,
                'captcha_image': result['image_base64'],
                'message': f'验证码识别失败，请查看下图并输入验证码（自动识别失败原因：{last_error}）'
            }

        self._log(f"获取人工验证码也失败: {result.get('message')}")
        return {'success': False, 'message': ERROR_MESSAGE}

    def _complete_registration(self, user_key: str, captcha_code: str) -> dict:
        """使用用户输入的验证码完成注册"""
        pending = self.pending_captcha.get(user_key)
        if not pending:
            return {'success': False, 'message': '验证码已过期，请重新开始注册'}
        self._log(f"使用人工验证码继续注册 user_key={user_key}")

        api = ZeppAPI(verbose=APP_DEBUG, use_proxy=USE_PROXY)
        reg_result = api.register_account(
            pending['email'],
            pending['password'],
            pending.get('name', pending['email']),
            pending['key'],
            captcha_code
        )

        # 清除待验证信息
        del self.pending_captcha[user_key]

        if reg_result['success']:
            return self._save_and_get_qr(user_key, pending['email'], pending['password'], api)

        return {'success': False, 'message': f"注册失败：{reg_result['message']}"}

    def _save_and_get_qr(self, user_key: str, email: str, password: str, api: ZeppAPI) -> dict:
        """保存用户信息、绑定手环、获取微信绑定二维码"""
        # 绑定流程固定使用普通请求，不走代理与伪装IP
        api = ZeppAPI(
            email,
            password,
            verbose=APP_DEBUG,
            use_tls=False,
            use_proxy=False,
            enable_spoof_ip=False
        )

        # 登录获取 userid
        login_result = api.login()

        if not login_result['success']:
            return {'success': False, 'message': f"登录失败：{login_result['message']}"}

        userid = login_result['userid']

        # 保存用户信息
        db = SessionLocal()
        try:
            user = User(
                user_key=user_key,
                zepp_email=email,
                zepp_password=password,
                zepp_userid=userid,
                bind_status=0
            )
            db.merge(user)
            db.commit()
        finally:
            db.close()

        # 1. 调用 bindband 绑定手环（通过第三方API，自动完成）
        self._log(f"调用 bindband 绑定手环: {email}")
        bind_result = bindband(email, password, step=1, verbose=APP_DEBUG, use_proxy=USE_PROXY)
        self._log(f"bindband 结果: {bind_result}")

        bind_msg = ""
        if bind_result['success']:
            bind_msg = "手环已绑定，"
        else:
            bind_msg = f"手环绑定失败({bind_result.get('message', '未知错误')})，{self._bind_guide_text()}"

        # 2. 获取微信绑定二维码（用户扫码绑定微信）
        qr_result = api.get_qrcode_ticket()
        if qr_result['success']:
            ticket = qr_result['ticket']
            if QRCODE_AVAILABLE:
                qrcode_base64 = generate_qrcode(ticket)
                return {
                    'success': True,
                    'qrcode_image': qrcode_base64,
                    'message': f'注册成功！{bind_msg}请使用微信扫描下方二维码绑定微信，完成后回复"已绑定"'
                }

        return {
            'success': True,
            'message': f'注册成功！{bind_msg}请在微信中打开链接绑定：{qr_result.get("ticket", "获取失败")}。{self._bind_guide_text()}'
        }

    def _get_bindqr_for_user_by_key(self, user_key: str, auto_trigger: bool = False) -> dict:
        user = self.get_user(user_key)
        if not user:
            return {'success': False, 'message': '用户不存在'}
        return self._get_bindqr_for_user(user, auto_trigger=auto_trigger)

    def _get_bindqr_for_user(self, user: User, auto_trigger: bool = False) -> dict:
        """为已注册用户绑定手环并获取微信绑定二维码"""
        try:
            api = ZeppAPI(
                user.zepp_email, user.zepp_password,
                verbose=APP_DEBUG,
                use_tls=False,
                use_proxy=False,
                enable_spoof_ip=False
            )

            # 检查是否有缓存的token
            if user.login_token and user.app_token:
                api.login_token = user.login_token
                api.app_token = user.app_token
                api.userid = user.zepp_userid
            else:
                # 需要登录
                login_result = api.login()
                if not login_result['success']:
                    return {'success': False, 'message': f'登录失败：{login_result["message"]}'}

            bind_msg = ""

            # 1. 自动触发绑定手环（仅首次）
            if auto_trigger and user.user_key and self._trigger_bind_button_once(user.user_key):
                bind_result = bindband(user.zepp_email, user.zepp_password, step=1, verbose=APP_DEBUG, use_proxy=USE_PROXY)
                self._log(f"自动绑定手环结果: {bind_result}")
                if bind_result.get("success"):
                    bind_msg = "手环已绑定，"
                else:
                    bind_msg = f"手环绑定失败({bind_result.get('message', '未知错误')})，{self._bind_guide_text()}"

            # 2. 获取微信绑定二维码（始终返回，让用户扫码绑定微信）
            qr_result = api.get_qrcode_ticket(api.userid)
            if qr_result['success'] and QRCODE_AVAILABLE:
                qrcode_base64 = generate_qrcode(qr_result['ticket'])
                message = bind_msg + '请使用微信扫描下方二维码绑定微信，完成后回复"已绑定"'
                return {
                    'success': True,
                    'qrcode_image': qrcode_base64,
                    'message': message
                }

            return {'success': False, 'message': '获取二维码失败，请重试'}
        except Exception as e:
            self._log(f"获取绑定二维码异常: {e}")
            return {'success': False, 'message': ERROR_MESSAGE}

    def get_bindqr(self, user_key: str) -> dict:
        """获取绑定二维码"""
        user = self.get_user(user_key)
        if not user or not user.zepp_email:
            return {'success': False, 'message': '您还没有注册账号，请先说"我要刷步"开始注册'}

        if user.bind_status == 1:
            return {'success': True, 'message': '您已完成绑定，可以直接刷步了'}

        return self._get_bindqr_for_user(user)

    def bind_device(self, user_key: str) -> dict:
        """绑定手环设备（通过第三方API自动完成，无需扫码）"""
        user = self.get_user(user_key)
        if not user or not user.zepp_email:
            return {'success': False, 'message': '您还没有注册账号，请先说"我要刷步"开始注册'}

        # 调用 bindband API 绑定手环
        self._log(f"手动触发绑定手环: {user.zepp_email}")
        bind_result = bindband(user.zepp_email, user.zepp_password, step=1, verbose=APP_DEBUG, use_proxy=USE_PROXY)
        self._log(f"绑定手环结果: {bind_result}")

        if bind_result['success']:
            # 更新 bind_button_triggered 状态
            db = SessionLocal()
            try:
                db_user = db.query(User).filter(User.user_key == user_key).first()
                if db_user:
                    db_user.bind_button_triggered = 1
                    db.merge(db_user)
                    db.commit()
            finally:
                db.close()

            return {
                'success': True,
                'message': '手环绑定成功！接下来请扫码绑定微信，完成后回复"已绑定"'
            }

        return {
            'success': False,
            'message': f'手环绑定失败：{bind_result.get("message", "未知错误")}。{self._bind_guide_text()}'
        }

    def check_bindstatus(self, user_key: str) -> dict:
        """检查绑定状态"""
        user = self.get_user(user_key)
        if not user or not user.zepp_userid:
            return {'success': False, 'message': '您还没有注册账号'}

        # 调用 API 检查绑定状态
        result = check_bindstatus(
            user.zepp_userid,
            verbose=False,
            use_proxy=USE_PROXY if USE_PROXY_MODE else False
        )

        if result['success'] and result['is_bound']:
            # 更新数据库状态
            db = SessionLocal()
            try:
                user.bind_status = 1
                db.merge(user)
                db.commit()
            finally:
                db.close()

            # 调用 bindband 初始化（步数=1）
            bind_result = bindband(user.zepp_email, user.zepp_password, step=1, verbose=False, use_proxy=USE_PROXY)

            if bind_result['success']:
                return {
                    'success': True,
                    'is_bound': True,
                    'message': '绑定成功！账号初始化完成，现在您可以告诉我想要刷多少步了~'
                }
            else:
                return {
                    'success': True,
                    'is_bound': True,
                    'message': '绑定成功！您可以开始刷步了'
                }

        return {
            'success': True,
            'is_bound': False,
            'message': f'暂未检测到绑定，请确认已用微信扫码完成绑定后再试。{self._bind_guide_text()}'
        }

    def brush_step(self, user_key: str, steps: int) -> dict:
        """刷步数"""
        # 验证步数范围
        if steps < MIN_STEPS or steps > MAX_STEPS:
            return {'success': False, 'message': f'步数范围应为 {MIN_STEPS}-{MAX_STEPS}'}

        user = self.get_user(user_key)
        if not user or not user.zepp_email:
            return {'success': False, 'message': '您还没有注册账号，请先说"我要刷步"开始注册'}

        if USE_PROXY_MODE and user.bind_status != 1:
            return {'success': False, 'message': f'您还没有绑定设备，请先完成绑定。{self._bind_guide_text()}'}

        # 检查会员状态
        if not user.vip_expire_at or user.vip_expire_at < datetime.now():
            return {'success': False, 'message': '您的会员已过期，请充值后继续使用。回复"充值"了解详情。'}

        if USE_PROXY_MODE:
            # 使用 Zepp API 刷步（原有流程）
            api = ZeppAPI(user.zepp_email, user.zepp_password, verbose=APP_DEBUG, use_proxy=USE_PROXY)
            api.userid = user.zepp_userid

            # 检查是否有缓存的token
            need_login = True
            if user.login_token and user.app_token and user.token_updated_at:
                # Token在24小时内有效
                from datetime import timedelta
                if datetime.now() - user.token_updated_at < timedelta(hours=24):
                    api.login_token = user.login_token
                    api.app_token = user.app_token
                    need_login = False
                    self._log(f"使用缓存的token，更新时间: {user.token_updated_at}")

            # 先尝试用缓存token刷步
            result = api.update_step(steps)

            # 如果失败且使用了缓存token，可能是token过期，重新登录
            if not result['success'] and not need_login:
                self._log("缓存token可能已过期，重新登录")
                need_login = True
                api.login_token = None
                api.app_token = None

            # 需要重新登录
            if need_login:
                result = api.update_step(steps)

            # 保存token到数据库
            if api.login_token and api.app_token:
                db = SessionLocal()
                try:
                    user.login_token = api.login_token
                    user.app_token = api.app_token
                    user.token_updated_at = datetime.now()
                    db.merge(user)
                    db.commit()
                    self._log("Token已缓存")
                finally:
                    db.close()
        else:
            # 关闭代理模式后，刷步直接走第三方接口：apikey + 账号 + 密码 + 步数
            result = bindband(
                user.zepp_email,
                user.zepp_password,
                step=steps,
                verbose=APP_DEBUG,
                use_proxy=False
            )

            # 直连模式刷步成功后，视为已完成设备绑定
            if result.get('success') and user.bind_status != 1:
                db = SessionLocal()
                try:
                    db_user = db.query(User).filter(User.user_key == user_key).first()
                    if db_user:
                        db_user.bind_status = 1
                        db.merge(db_user)
                        db.commit()
                finally:
                    db.close()

        # 记录刷步历史
        db = SessionLocal()
        try:
            record = StepRecord(
                user_key=user_key,
                steps=steps,
                status='success' if result['success'] else 'failed',
                message=result['message']
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

        if result['success']:
            return {
                'success': True,
                'steps': steps,
                'message': f'刷步成功！已将步数修改为 {steps} 步'
            }

        return {
            'success': False,
            'message': f"刷步失败：{result['message']}。{self._bind_guide_text()}"
        }

    def check_vip(self, user_key: str) -> dict:
        """检查会员状态"""
        user = self.get_user(user_key)
        if not user:
            return {'success': False, 'is_vip': False, 'message': '用户不存在'}

        if user.vip_expire_at and user.vip_expire_at > datetime.now():
            remaining_days = (user.vip_expire_at - datetime.now()).days
            return {
                'success': True,
                'is_vip': True,
                'remaining_days': remaining_days,
                'vip_expire_at': user.vip_expire_at.strftime('%Y-%m-%d %H:%M:%S'),
                'message': f'您的会员有效期至 {user.vip_expire_at.strftime("%Y-%m-%d")}，剩余 {remaining_days} 天'
            }
        else:
            return {
                'success': True,
                'is_vip': False,
                'remaining_days': 0,
                'message': '您的会员已过期，请充值续费。回复"充值"了解详情。'
            }

    def use_card(self, user_key: str, card_key: str) -> dict:
        """使用卡密充值"""
        db = SessionLocal()
        try:
            # 查找卡密
            card = db.query(Card).filter(Card.card_key == card_key).first()
            if not card:
                return {'success': False, 'message': '卡密不存在，请检查后重试'}

            if card.status == 'used':
                return {'success': False, 'message': '该卡密已被使用'}

            # 获取或创建用户
            user = db.query(User).filter(User.user_key == user_key).first()
            if not user:
                return {'success': False, 'message': '用户不存在，请先登录'}

            # 计算新的过期时间
            if user.vip_expire_at and user.vip_expire_at > datetime.now():
                new_expire = user.vip_expire_at + timedelta(days=card.days)
            else:
                new_expire = datetime.now() + timedelta(days=card.days)

            # 更新用户会员时间
            user.vip_expire_at = new_expire

            # 标记卡密为已使用
            card.status = 'used'
            card.used_by = user_key
            card.used_at = datetime.now()

            db.commit()

            return {
                'success': True,
                'message': f'充值成功！已为您延长 {card.days} 天会员，有效期至 {new_expire.strftime("%Y-%m-%d")}',
                'vip_expire_at': new_expire.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            db.rollback()
            return {'success': False, 'message': f'充值失败：{str(e)}'}
        finally:
            db.close()

    def get_user_status(self, user_key: str) -> str:
        """获取用户状态描述"""
        user = self.get_user(user_key)
        if not user or not user.zepp_email:
            return "未注册"
        if not USE_PROXY_MODE:
            return "已注册，可直接刷步"
        if user.bind_status != 1:
            return "已注册，未绑定设备"
        return "已注册，已绑定设备，可刷步"


# 全局实例
skills = StepSkills()


# Function Calling 定义
FUNCTIONS = [
    {
        "name": "register_zepp_account",
        "description": "为用户注册Zepp账号。当用户表达想要刷步、注册等意图时调用此函数。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                },
                "captcha_code": {
                    "type": "string",
                    "description": "用户输入的验证码（仅当需要手动输入验证码时传入）"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "get_bindqr",
        "description": "获取微信绑定二维码",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "bind_device",
        "description": "绑定手环设备。通过第三方API自动完成，无需扫码。当用户说'绑定手环'、'绑定设备'、'触发绑定'等时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "check_bindstatus",
        "description": "检查用户是否已绑定微信。当用户说'已绑定'、'绑定好了'等时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "brush_step",
        "description": "为用户刷步数。重要：只有当用户明确指定了具体步数时才调用（如'刷50000步'、'刷步30000'）。如果用户只说'刷步'或'我要刷步'但没有指定步数，不要调用此函数，应该先询问用户想要刷多少步。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                },
                "steps": {
                    "type": "integer",
                    "description": "目标步数，范围1-98800"
                }
            },
            "required": ["user_key", "steps"]
        }
    },
    {
        "name": "create_scheduled_task",
        "description": "创建定时刷步任务。当用户说'每天xx步'、'定时刷步'、'自动刷步'等时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                },
                "target_steps": {
                    "type": "integer",
                    "description": "每日目标步数"
                },
                "start_hour": {
                    "type": "integer",
                    "description": "开始时间（小时，0-23），默认8"
                },
                "end_hour": {
                    "type": "integer",
                    "description": "结束时间（小时，0-23），默认21"
                }
            },
            "required": ["user_key", "target_steps"]
        }
    },
    {
        "name": "get_scheduled_task",
        "description": "获取用户的定时刷步任务信息。当用户询问定时任务状态时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "update_scheduled_task",
        "description": "更新定时刷步任务。当用户想修改目标步数或时间时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                },
                "target_steps": {
                    "type": "integer",
                    "description": "新的目标步数（可选）"
                },
                "start_hour": {
                    "type": "integer",
                    "description": "新的开始时间（可选）"
                },
                "end_hour": {
                    "type": "integer",
                    "description": "新的结束时间（可选）"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "cancel_scheduled_task",
        "description": "取消定时刷步任务。当用户说'取消定时'、'停止自动刷步'等时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "pause_scheduled_task",
        "description": "暂停定时刷步任务。当用户说'暂停定时'、'暂时停止'等时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "resume_scheduled_task",
        "description": "恢复定时刷步任务。当用户说'恢复定时'、'继续刷步'等时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "check_vip",
        "description": "检查用户会员状态。当用户询问会员、VIP、到期时间等时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                }
            },
            "required": ["user_key"]
        }
    },
    {
        "name": "use_card",
        "description": "使用卡密充值会员。当用户提供卡密说'充值'、'续费'、'使用卡密'等时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_key": {
                    "type": "string",
                    "description": "用户唯一标识"
                },
                "card_key": {
                    "type": "string",
                    "description": "卡密"
                }
            },
            "required": ["user_key", "card_key"]
        }
    }
]


def execute_function(function_name: str, arguments: dict) -> dict:
    """执行函数调用"""
    from scheduler import scheduler

    if function_name == "register_zepp_account":
        return skills.register_zepp_account(
            arguments.get("user_key"),
            arguments.get("captcha_code")
        )
    elif function_name == "get_bindqr":
        return skills.get_bindqr(arguments.get("user_key"))
    elif function_name == "bind_device":
        return skills.bind_device(arguments.get("user_key"))
    elif function_name == "check_bindstatus":
        return skills.check_bindstatus(arguments.get("user_key"))
    elif function_name == "brush_step":
        return skills.brush_step(
            arguments.get("user_key"),
            arguments.get("steps")
        )
    elif function_name == "create_scheduled_task":
        return scheduler.create_task(
            arguments.get("user_key"),
            arguments.get("target_steps"),
            arguments.get("start_hour", 8),
            arguments.get("end_hour", 21)
        )
    elif function_name == "get_scheduled_task":
        task = scheduler.get_task(arguments.get("user_key"))
        if task:
            status_text = {"active": "执行中", "paused": "已暂停", "cancelled": "已取消"}.get(task.get("status"), task.get("status"))
            return {
                "success": True,
                "task": task,
                "message": f"您有一个定时任务：每天 {task.get('start_hour')}:00-{task.get('end_hour')}:00 完成 {task.get('target_steps')} 步，状态：{status_text}，当前进度：{task.get('current_steps', 0)} 步"
            }
        return {"success": False, "message": "您还没有设置定时任务"}
    elif function_name == "update_scheduled_task":
        return scheduler.update_task(
            arguments.get("user_key"),
            arguments.get("target_steps"),
            arguments.get("start_hour"),
            arguments.get("end_hour")
        )
    elif function_name == "cancel_scheduled_task":
        return scheduler.cancel_task(arguments.get("user_key"))
    elif function_name == "pause_scheduled_task":
        return scheduler.pause_task(arguments.get("user_key"))
    elif function_name == "resume_scheduled_task":
        return scheduler.resume_task(arguments.get("user_key"))
    elif function_name == "check_vip":
        return skills.check_vip(arguments.get("user_key"))
    elif function_name == "use_card":
        return skills.use_card(
            arguments.get("user_key"),
            arguments.get("card_key")
        )
    else:
        return {"success": False, "message": f"未知函数: {function_name}"}
