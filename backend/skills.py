# -*- coding: utf-8 -*-
"""
AI Skills - Function Calling 实现
"""
import random
import string
import sys
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

# 添加父目录到路径，以便导入 step_brush
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from step_brush import (
    ZeppAPI, ocr_captcha, generate_qrcode,
    bindband, check_bindstatus,
    DDDDOCR_AVAILABLE, QRCODE_AVAILABLE
)
from models import User, StepRecord, Card, SessionLocal, get_db_session
from config import (
    CAPTCHA_RETRY_TIMES, MIN_STEPS, MAX_STEPS, ERROR_MESSAGE,
    APP_DEBUG, USE_PROXY, USE_PROXY_MODE, CAPTCHA_PENDING_EXPIRE
)
from time_utils import get_china_now


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器，用于网络请求失败时自动重试

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间倍数（每次重试后延迟增加）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    # 如果成功，直接返回
                    if result.get('success'):
                        return result
                    # 如果是业务逻辑失败（如参数错误），不重试
                    error_msg = result.get('message', '')
                    if any(keyword in error_msg for keyword in ['未配置', '不存在', '无效', '格式错误', '参数']):
                        return result
                    # 网络超时或临时失败，准备重试
                    last_error = error_msg
                    if attempt < max_retries - 1:
                        print(f"[Retry] {func.__name__} 第 {attempt + 1} 次失败: {error_msg}，{current_delay}秒后重试")
                        time.sleep(current_delay)
                        current_delay *= backoff
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        print(f"[Retry] {func.__name__} 第 {attempt + 1} 次异常: {e}，{current_delay}秒后重试")
                        time.sleep(current_delay)
                        current_delay *= backoff
            # 所有重试都失败
            return {'success': False, 'message': f'请求失败（已重试{max_retries}次）: {last_error}'}
        return wrapper
    return decorator


# 带重试的 bindband 调用
@retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
def _bindband_with_retry(email: str, password: str, step: int, verbose: bool, use_proxy: bool) -> dict:
    """带重试机制的绑定手环/刷步接口"""
    return bindband(email, password, step=step, verbose=verbose, use_proxy=use_proxy)


@retry_on_failure(max_retries=5, delay=1.0, backoff=1.5)
def _bind_device_with_retry(email: str, password: str, verbose: bool) -> dict:
    """绑定手环专用接口：固定直连且增加重试。"""
    return bindband(email, password, step=1, verbose=verbose, use_proxy=False)


def _login_with_proxy(email: str, password: str, verbose: bool) -> dict:
    """Zepp 登录统一强制走代理，避免登录接口被限流。"""
    api = ZeppAPI(
        email,
        password,
        verbose=verbose,
        use_tls=False,
        use_proxy=True,
    )
    result = api.login()
    if not result.get("success"):
        return result
    return {
        "success": True,
        "userid": result.get("userid"),
        "login_token": api.login_token,
        "app_token": api.app_token,
        "api": api,
        "message": result.get("message", "ok"),
    }


def generate_random_email():
    """生成随机邮箱"""
    chars = string.ascii_lowercase + string.digits
    username = ''.join(random.choices(chars, k=10))
    return f"{username}@gmail.com"


def generate_strong_password():
    """生成仅由小写字母组成的密码"""
    return ''.join(random.choices(string.ascii_lowercase, k=12))


class StepSkills:
    """刷步相关 Skills"""

    def __init__(self):
        # 存储待验证的验证码信息 {user_key: {key, image_base64, timestamp}}
        self.pending_captcha: Dict[str, Dict[str, Any]] = {}

    def _log(self, msg: str):
        if APP_DEBUG:
            print(f"[StepSkills] {msg}")

    def _cleanup_expired_captcha(self):
        """清理过期的验证码pending记录"""
        now = time.time()
        expired_keys = [
            k for k, v in self.pending_captcha.items()
            if now - v.get('timestamp', 0) > CAPTCHA_PENDING_EXPIRE
        ]
        for k in expired_keys:
            del self.pending_captcha[k]
            self._log(f"已清理过期验证码记录: {k}")

    @staticmethod
    def _bind_guide_text() -> str:
        """统一的绑定引导文案。"""
        return '可发送"绑定手环"重试手环绑定；发送"绑定微信"获取新二维码重新扫码；完成后回复"已绑定"。'

    def _trigger_bind_button_once(self, user_key: str) -> bool:
        """登录成功后仅触发一次后台绑定动作。"""
        with get_db_session() as db:
            user = db.query(User).filter(User.user_key == user_key).first()
            if not user:
                return False
            if user.bind_status == 1 or user.bind_button_triggered == 1:
                return False
            user.bind_button_triggered = 1
            self._log(f"后台绑定动作首次触发: user_key={user_key}")
            return True

    def get_user(self, user_key: str) -> Optional[Dict[str, Any]]:
        """获取用户信息（返回字典，避免会话分离问题）"""
        with get_db_session() as db:
            user = db.query(User).filter(User.user_key == user_key).first()
            if user:
                # 在会话内访问所有属性，返回字典
                return {
                    'user_key': user.user_key,
                    'zepp_email': user.zepp_email,
                    'zepp_password': user.zepp_password,
                    'zepp_userid': user.zepp_userid,
                    'bind_status': user.bind_status,
                    'bind_button_triggered': user.bind_button_triggered,
                    'vip_expire_at': user.vip_expire_at,
                    'login_token': user.login_token,
                    'app_token': user.app_token,
                    'token_updated_at': user.token_updated_at,
                }
            return None

    def get_user_object(self, user_key: str) -> Optional[User]:
        """获取用户ORM对象（仅用于在同一会话内操作）"""
        with get_db_session() as db:
            user = db.query(User).filter(User.user_key == user_key).first()
            return user

    def save_user(self, user: User):
        """保存用户信息"""
        with get_db_session() as db:
            db.merge(user)

    def _user_to_snapshot(self, user: User) -> Dict[str, Any]:
        """将 ORM 用户对象转换为脱离 session 也可安全使用的快照。"""
        return {
            'id': user.id,
            'user_key': user.user_key,
            'zepp_email': user.zepp_email,
            'zepp_password': user.zepp_password,
            'zepp_userid': user.zepp_userid,
            'bind_status': user.bind_status,
            'bind_button_triggered': user.bind_button_triggered,
            'vip_expire_at': user.vip_expire_at,
            'login_token': user.login_token,
            'app_token': user.app_token,
            'token_updated_at': user.token_updated_at,
        }

    def _get_available_account(self) -> Optional[Dict[str, Any]]:
        """从账户池获取一个可用账户快照（user_key 为空）。"""
        with get_db_session() as db:
            account = db.query(User).filter(User.user_key.is_(None)).first()
            if not account:
                return None
            return self._user_to_snapshot(account)

    def _assign_account_to_user(self, user_key: str, account: Dict[str, Any]) -> dict:
        """将账户分配给用户"""
        try:
            with get_db_session() as db:
                account_id = account.get('id')
                db_account = db.query(User).filter(
                    User.id == account_id,
                    User.user_key.is_(None)
                ).first()
                if not db_account:
                    return {'success': False, 'message': '账户池中的账号已被分配，请重试'}

                # 检查用户是否已存在
                existing_user = db.query(User).filter(User.user_key == user_key).first()

                if existing_user:
                    # 用户已存在，将账户信息复制到现有用户
                    existing_user.zepp_email = db_account.zepp_email
                    existing_user.zepp_password = db_account.zepp_password
                    existing_user.zepp_userid = db_account.zepp_userid
                    existing_user.bind_status = db_account.bind_status
                    # 删除账户池中的记录
                    db.delete(db_account)
                    self._log(f"已将账户 {db_account.zepp_email} 绑定到现有用户 {user_key}")
                    db.flush()  # 确保删除操作生效

                    # 登录成功后触发一次后台绑定
                    return self._get_bindqr_for_user(existing_user, auto_trigger=True)
                else:
                    # 用户不存在，直接更新账户的 user_key
                    db_account.user_key = user_key
                    self._log(f"已将账户 {db_account.zepp_email} 分配给新用户 {user_key}")

                    # 登录成功后触发一次后台绑定
                    return self._get_bindqr_for_user(db_account, auto_trigger=True)
        except Exception as e:
            self._log(f"分配账户失败: {e}")
            return {'success': False, 'message': '分配账户失败，请重试'}

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
        # 清理过期的验证码记录
        self._cleanup_expired_captcha()

        # 检查用户是否已注册
        user = self.get_user(user_key)
        if user and user.get('zepp_email'):
            if user.get('bind_status') == 1:
                return {
                    'success': True,
                    'message': f'您已完成注册和绑定，可以直接刷步了。'
                }
            else:
                # 已注册但未绑定，登录成功后触发一次后台绑定
                return self._get_bindqr_for_user_dict(user, auto_trigger=True)

        # 如果有待验证的验证码，使用用户输入的验证码继续注册
        if captcha_code and user_key in self.pending_captcha:
            return self._complete_registration(user_key, captcha_code)

        # 尝试从账户池中获取一个可用账户
        available_account = self._get_available_account()
        if available_account:
            self._log(f"从账户池分配账户: {available_account.get('zepp_email')}")
            return self._assign_account_to_user(user_key, available_account)

        # 账户池中没有可用账户，开始新注册流程
        self._log("账户池无可用账户，开始新注册流程")

        # 开始新注册流程
        email = generate_random_email()
        password = generate_strong_password()
        register_name = email

        # 注册流程强制使用代理
        api = ZeppAPI(verbose=APP_DEBUG, use_tls=False, use_proxy=True)
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
                'image_base64': result['image_base64'],
                'timestamp': time.time()  # 添加时间戳用于过期清理
            }
            return {
                'success': False,
                'need_captcha': True,
                'captcha_image': result['image_base64'],
                'message': f'验证码识别失败，请查看下图并输入验证码（自动识别失败原因：{last_error}）'
            }

        self._log(f"获取人工验证码也失败: {result.get('message')}")
        return {
            'success': False,
            'message': f"获取验证码失败：{result.get('message', last_error or ERROR_MESSAGE)}"
        }

    def _complete_registration(self, user_key: str, captcha_code: str) -> dict:
        """使用用户输入的验证码完成注册"""
        pending = self.pending_captcha.get(user_key)
        if not pending:
            return {'success': False, 'message': '验证码已过期，请重新开始注册'}
        self._log(f"使用人工验证码继续注册 user_key={user_key}")

        # 注册流程强制使用代理
        api = ZeppAPI(verbose=APP_DEBUG, use_tls=False, use_proxy=True)
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
        try:
            # 登录时使用代理（避免限流）
            login_result = _login_with_proxy(email, password, verbose=APP_DEBUG)
            if not login_result['success']:
                return {'success': False, 'message': f"登录失败：{login_result['message']}"}

            api = login_result['api']
            userid = login_result['userid']

            # 保存用户信息
            try:
                with get_db_session() as db:
                    db_user = db.query(User).filter(User.user_key == user_key).first()
                    if db_user:
                        # 已存在用户：覆盖 Zepp 账号信息
                        db_user.zepp_email = email
                        db_user.zepp_password = password
                        db_user.zepp_userid = userid
                        db_user.bind_status = 0
                        db_user.bind_button_triggered = 0
                        if api.login_token and api.app_token:
                            db_user.login_token = api.login_token
                            db_user.app_token = api.app_token
                            db_user.token_updated_at = get_china_now()
                    else:
                        # 不存在用户：新建
                        db_user = User(
                            user_key=user_key,
                            zepp_email=email,
                            zepp_password=password,
                            zepp_userid=userid,
                            bind_status=0,
                            login_token=api.login_token if api.login_token else None,
                            app_token=api.app_token if api.app_token else None,
                            token_updated_at=get_china_now() if (api.login_token and api.app_token) else None
                        )
                        db.add(db_user)
            except Exception as e:
                self._log(f"保存用户信息异常: {e}")
                return {'success': False, 'message': f'保存账号信息失败：{str(e)}'}

            # 1. 调用 bindband 绑定手环（通过第三方API，自动完成）
            self._log(f"调用 bindband 绑定手环: {email}")
            bind_result = _bind_device_with_retry(email, password, verbose=APP_DEBUG)
            self._log(f"bindband 结果: success={bind_result.get('success')}, message={bind_result.get('message')}")

            bind_msg = ""
            if bind_result['success']:
                # 更新绑定状态
                with get_db_session() as db:
                    db_user = db.query(User).filter(User.user_key == user_key).first()
                    if db_user:
                        if bind_result.get('userid'):
                            db_user.zepp_userid = bind_result.get('userid')
                        # 如果不使用代理模式，绑定成功即视为完成
                        if not USE_PROXY_MODE:
                            db_user.bind_status = 1
                            db_user.bind_button_triggered = 1
                bind_msg = "手环已绑定，"
            else:
                # 如果是API Key未配置，给出更明确的提示
                error_msg = bind_result.get('message', '未知错误')
                if '未配置部署key' in error_msg or 'NANRUN_API_KEY' in error_msg:
                    bind_msg = f"手环绑定失败(服务端未配置API Key)，请联系管理员。{self._bind_guide_text()}"
                else:
                    bind_msg = f"手环绑定失败({error_msg})，{self._bind_guide_text()}"

            # 如果不使用代理模式，绑定成功后直接返回，不需要扫码
            if not USE_PROXY_MODE and bind_result['success']:
                return {
                    'success': True,
                    'message': f'注册成功！手环已绑定。您现在可以开始刷步了，告诉我想要刷多少步。'
                }

            # 2. 获取微信绑定二维码（用户扫码绑定微信）- 仅代理模式需要
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
        except Exception as e:
            self._log(f"_save_and_get_qr 异常: {e}")
            return {'success': False, 'message': f'注册后处理失败：{str(e)}'}

    def _get_bindqr_for_user_by_key(self, user_key: str, auto_trigger: bool = False) -> dict:
        user = self.get_user(user_key)
        if not user:
            return {'success': False, 'message': '用户不存在'}
        return self._get_bindqr_for_user_dict(user, auto_trigger=auto_trigger)

    def _cache_user_tokens_best_effort(self, user_key: str, login_token: str, app_token: str) -> None:
        """缓存用户 token；失败只记录日志，不影响主流程。"""
        if not user_key or not login_token or not app_token:
            return

        try:
            with get_db_session() as db:
                db_user = db.query(User).filter(User.user_key == user_key).first()
                if db_user:
                    db_user.login_token = login_token
                    db_user.app_token = app_token
                    db_user.token_updated_at = get_china_now()
        except Exception as e:
            self._log(f"缓存token失败 user_key={user_key}: {e}")

    @staticmethod
    def _is_retryable_brush_message(message: str) -> bool:
        text = (message or "").lower()
        retryable_keywords = [
            "timeout",
            "timed out",
            "connection reset",
            "reset by peer",
            "awaiting headers",
            "proxy",
            "tlsclient",
            "tls client",
            "connection aborted",
            "temporary failure",
            "temporarily unavailable",
            "network",
            "eof",
        ]
        return any(keyword in text for keyword in retryable_keywords)

    def _safe_update_step(self, api: ZeppAPI, steps: int) -> dict:
        try:
            return api.update_step(steps)
        except Exception as e:
            self._log(f"刷步请求异常: {e}")
            return {'success': False, 'message': str(e)}

    def _refresh_api_login(self, api: ZeppAPI, user: Dict[str, Any]) -> dict:
        login_result = _login_with_proxy(
            user.get('zepp_email'),
            user.get('zepp_password'),
            verbose=APP_DEBUG,
        )
        if not login_result['success']:
            return login_result

        api.userid = login_result.get('userid')
        api.login_token = login_result.get('login_token')
        api.app_token = login_result.get('app_token')
        return {'success': True}

    def _update_step_with_retry(self, api: ZeppAPI, user: Dict[str, Any], steps: int,
                                max_retries: int = 3, used_cached_token: bool = False) -> dict:
        result = self._safe_update_step(api, steps)
        if result.get('success'):
            return result

        for attempt in range(2, max_retries + 1):
            should_retry = self._is_retryable_brush_message(result.get('message', ''))
            if not used_cached_token and not should_retry:
                break

            if used_cached_token and attempt == 2:
                self._log("缓存token可能已过期，重新登录")
            else:
                self._log(
                    f"刷步第 {attempt - 1}/{max_retries} 次失败，"
                    f"准备进行第 {attempt}/{max_retries} 次重试: {result.get('message', '未知错误')}"
                )

            login_result = self._refresh_api_login(api, user)
            if not login_result.get('success'):
                result = {'success': False, 'message': login_result.get('message', '登录失败')}
                if not self._is_retryable_brush_message(result.get('message', '')):
                    break
                continue

            used_cached_token = False
            result = self._safe_update_step(api, steps)
            if result.get('success'):
                return result

        return result

    def _get_bindqr_for_user_dict(self, user: Dict[str, Any], auto_trigger: bool = False) -> dict:
        """为已注册用户绑定手环并获取微信绑定二维码（使用字典参数）"""
        try:
            user_key = user.get('user_key')

            # 如果不使用代理模式，直接调用第三方API绑定
            if not USE_PROXY_MODE:
                bind_result = _bind_device_with_retry(
                    user.get('zepp_email'),
                    user.get('zepp_password'),
                    verbose=APP_DEBUG,
                )
                self._log(f"直连模式绑定手环结果: {bind_result}")

                if bind_result.get('success'):
                    with get_db_session() as db:
                        db_user = db.query(User).filter(User.user_key == user_key).first()
                        if db_user:
                            db_user.bind_status = 1
                            db_user.bind_button_triggered = 1
                            if bind_result.get('userid'):
                                db_user.zepp_userid = bind_result.get('userid')

                    return {
                        'success': True,
                        'message': '绑定成功！您现在可以开始刷步了，告诉我想要刷多少步。'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'绑定失败：{bind_result.get("message", "未知错误")}'
                    }

            # 代理模式：需要获取微信绑定二维码
            api = ZeppAPI(
                user.get('zepp_email'), user.get('zepp_password'),
                verbose=APP_DEBUG,
                use_tls=False,
                use_proxy=USE_PROXY
            )

            # 检查是否有缓存的token
            if user.get('login_token') and user.get('app_token'):
                api.login_token = user.get('login_token')
                api.app_token = user.get('app_token')
                api.userid = user.get('zepp_userid')
            else:
                login_result = _login_with_proxy(
                    user.get('zepp_email'),
                    user.get('zepp_password'),
                    verbose=APP_DEBUG,
                )
                if not login_result['success']:
                    return {'success': False, 'message': f'登录失败：{login_result["message"]}'}
                api.userid = login_result.get('userid')
                api.login_token = login_result.get('login_token')
                api.app_token = login_result.get('app_token')
                # 登录成功后缓存token，减少后续重复登录；缓存失败不应阻断二维码返回。
                self._cache_user_tokens_best_effort(user_key, api.login_token, api.app_token)

            bind_msg = ""

            # 1. 自动触发绑定手环（仅首次）
            if auto_trigger and user_key and self._trigger_bind_button_once(user_key):
                bind_result = _bind_device_with_retry(
                    user.get('zepp_email'),
                    user.get('zepp_password'),
                    verbose=APP_DEBUG,
                )
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
            traceback.print_exc()
            return {'success': False, 'message': f'获取绑定二维码失败：{str(e)}'}

    def _get_bindqr_for_user(self, user: User, auto_trigger: bool = False) -> dict:
        """为已注册用户绑定手环并获取微信绑定二维码"""
        # 转换为字典后调用
        user_dict = {
            'user_key': user.user_key,
            'zepp_email': user.zepp_email,
            'zepp_password': user.zepp_password,
            'zepp_userid': user.zepp_userid,
            'bind_status': user.bind_status,
            'bind_button_triggered': user.bind_button_triggered,
            'vip_expire_at': user.vip_expire_at,
            'login_token': user.login_token,
            'app_token': user.app_token,
            'token_updated_at': user.token_updated_at,
        }
        return self._get_bindqr_for_user_dict(user_dict, auto_trigger=auto_trigger)

    def get_bindqr(self, user_key: str) -> dict:
        """获取绑定二维码"""
        user = self.get_user(user_key)
        if not user or not user.get('zepp_email'):
            return {'success': False, 'message': '您还没有注册账号，请先说"我要刷步"开始注册'}

        if user.get('bind_status') == 1:
            return {'success': True, 'message': '您已完成绑定，可以直接刷步了'}

        return self._get_bindqr_for_user_dict(user)

    def bind_device(self, user_key: str) -> dict:
        """绑定手环设备（通过第三方API自动完成，无需扫码）"""
        user = self.get_user(user_key)
        if not user or not user.get('zepp_email'):
            return {'success': False, 'message': '您还没有注册账号，请先说"我要刷步"开始注册'}

        # 调用 bindband API 绑定手环
        self._log(f"手动触发绑定手环: {user.get('zepp_email')}")
        bind_result = _bind_device_with_retry(
            user.get('zepp_email'),
            user.get('zepp_password'),
            verbose=APP_DEBUG,
        )
        self._log(f"绑定手环结果: {bind_result}")

        if bind_result['success']:
            # 更新绑定状态
            with get_db_session() as db:
                db_user = db.query(User).filter(User.user_key == user_key).first()
                if db_user:
                    db_user.bind_button_triggered = 1
                    # 如果不使用代理模式（直连第三方API），绑定成功即视为完成绑定
                    if not USE_PROXY_MODE:
                        db_user.bind_status = 1
                        if bind_result.get('userid'):
                            db_user.zepp_userid = bind_result.get('userid')

            if not USE_PROXY_MODE:
                return {
                    'success': True,
                    'message': '手环绑定成功！您现在可以开始刷步了，告诉我想要刷多少步。'
                }
            else:
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
        if not user or not user.get('zepp_email'):
            return {'success': False, 'message': '您还没有注册账号'}

        # 如果不使用代理模式（直连第三方API），绑定状态由 bind_device 设置
        # 只要用户有 zepp_email 就认为已绑定
        if not USE_PROXY_MODE:
            with get_db_session() as db:
                db_user = db.query(User).filter(User.user_key == user_key).first()
                if db_user:
                    db_user.bind_status = 1
                    db_user.bind_button_triggered = 1

            return {
                'success': True,
                'is_bound': True,
                'message': '绑定成功！您现在可以开始刷步了，告诉我想要刷多少步。'
            }

        # 代理模式：需要检查微信绑定状态
        if not user.get('zepp_userid'):
            return {'success': False, 'message': '您还没有注册账号'}

        # 调用 API 检查绑定状态
        result = check_bindstatus(
            user.get('zepp_userid'),
            verbose=False,
            use_proxy=USE_PROXY if USE_PROXY_MODE else False
        )

        if result['success'] and result['is_bound']:
            # 更新数据库状态
            with get_db_session() as db:
                db_user = db.query(User).filter(User.user_key == user_key).first()
                if db_user:
                    db_user.bind_status = 1

            # 调用 bindband 初始化（步数=1）
            bind_result = _bind_device_with_retry(
                user.get('zepp_email'),
                user.get('zepp_password'),
                verbose=False,
            )

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
        if not user or not user.get('zepp_email'):
            return {'success': False, 'message': '您还没有注册账号，请先说"我要刷步"开始注册'}

        if user.get('bind_status') != 1:
            return {'success': False, 'message': f'您还没有绑定设备，请先完成绑定。{self._bind_guide_text()}'}

        # 检查会员状态
        vip_expire_at = user.get('vip_expire_at')
        if not vip_expire_at or vip_expire_at < get_china_now():
            return {'success': False, 'message': '您的会员已过期，请充值后继续使用。回复"充值"了解详情。'}

        result = _bindband_with_retry(
            user.get('zepp_email'),
            user.get('zepp_password'),
            step=steps,
            verbose=APP_DEBUG,
            use_proxy=False
        )

        # 记录刷步历史
        with get_db_session() as db:
            record = StepRecord(
                user_key=user_key,
                steps=steps,
                status='success' if result['success'] else 'failed',
                message=result['message']
            )
            db.add(record)

        if result['success']:
            return {
                'success': True,
                'steps': steps,
                'message': f'完成！已设置 {steps} 步'
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

        vip_expire_at = user.get('vip_expire_at')
        if vip_expire_at and vip_expire_at > get_china_now():
            remaining_days = (vip_expire_at - get_china_now()).days
            return {
                'success': True,
                'is_vip': True,
                'remaining_days': remaining_days,
                'vip_expire_at': vip_expire_at.strftime('%Y-%m-%d %H:%M:%S'),
                'message': f'您的会员有效期至 {vip_expire_at.strftime("%Y-%m-%d")}，剩余 {remaining_days} 天'
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
        try:
            with get_db_session() as db:
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
                if user.vip_expire_at and user.vip_expire_at > get_china_now():
                    new_expire = user.vip_expire_at + timedelta(days=card.days)
                else:
                    new_expire = get_china_now() + timedelta(days=card.days)

                # 更新用户会员时间
                user.vip_expire_at = new_expire

                # 标记卡密为已使用
                card.status = 'used'
                card.used_by = user_key
                card.used_at = get_china_now()

                return {
                    'success': True,
                    'message': f'充值成功！已为您延长 {card.days} 天会员，有效期至 {new_expire.strftime("%Y-%m-%d")}',
                    'vip_expire_at': new_expire.strftime('%Y-%m-%d %H:%M:%S')
                }
        except Exception as e:
            return {'success': False, 'message': f'充值失败：{str(e)}'}

    def get_user_status(self, user_key: str) -> str:
        """获取用户状态描述"""
        user = self.get_user(user_key)
        if not user or not user.get('zepp_email'):
            return "未注册"
        if not USE_PROXY_MODE:
            return "已注册，可直接刷步"
        if user.get('bind_status') != 1:
            return "已注册，未绑定设备"
        return "已注册，已绑定设备，可刷步"

    def unbind_zepp_account(self, user_key: str) -> dict:
        """
        解绑当前Zepp账号，准备重新绑定新账号

        清除用户的Zepp账号信息，重置绑定状态，让用户可以重新注册新账号
        """
        user = self.get_user(user_key)
        if not user:
            return {'success': False, 'message': '用户不存在，请先登录'}

        if not user.get('zepp_email'):
            return {'success': False, 'message': '您还没有绑定Zepp账号，无需解绑。直接说"我要刷步"即可注册新账号。'}

        old_email = user.get('zepp_email')

        # 清除Zepp账号信息和绑定状态
        try:
            with get_db_session() as db:
                db_user = db.query(User).filter(User.user_key == user_key).first()
                if db_user:
                    db_user.zepp_email = None
                    db_user.zepp_password = None
                    db_user.zepp_userid = None
                    db_user.bind_status = 0
                    db_user.bind_button_triggered = 0
                    db_user.login_token = None
                    db_user.app_token = None
                    db_user.token_updated_at = None

            self._log(f"用户 {user_key} 已解绑Zepp账号: {old_email}")

            return {
                'success': True,
                'message': f'已解绑账号 {old_email}。现在您可以重新注册新账号，请回复"我要刷步"或"注册"开始新账号绑定。'
            }
        except Exception as e:
            self._log(f"解绑失败: {e}")
            return {'success': False, 'message': f'解绑失败：{str(e)}'}

    def rebind_zepp_account(self, user_key: str, captcha_code: str = None) -> dict:
        """
        换绑Zepp账号 - 解绑旧账号并注册新账号

        这是unbind + register的组合操作，方便用户一键换绑
        """
        # 先解绑旧账号
        user = self.get_user(user_key)
        if user and user.get('zepp_email'):
            unbind_result = self.unbind_zepp_account(user_key)
            if not unbind_result.get('success'):
                return unbind_result

        # 然后注册新账号
        return self.register_zepp_account(user_key, captcha_code)


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
        "description": "绑定手环设备。通过第三方API自动完成，无需扫码。当用户说'绑定手环'、'绑定设备'等时调用。注意：如果用户说'已绑定'、'绑定好了'，应该调用 check_bindstatus 而不是这个函数。",
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
        "description": "检查用户是否已绑定微信。当用户说'已绑定'、'绑定好了'、'绑定完成'、'已经绑定了'等表示绑定完成的意图时调用此函数来确认绑定状态。重要：这是唯一能确认微信绑定成功并更新绑定状态的函数。",
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
        "name": "get_scheduled_task_detail",
        "description": "获取定时刷步任务详情，包含每小时刷步计划。当用户说'定时任务详情'、'查看刷步计划'、'我的定时任务'等时调用。",
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
    },
    {
        "name": "unbind_zepp_account",
        "description": "解绑当前Zepp账号。当用户说'解绑账号'、'解除绑定'、'换绑账号'、'重新绑定'、'注销账号'等时调用。解绑后用户可以注册新的Zepp账号。",
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
        "name": "rebind_zepp_account",
        "description": "换绑Zepp账号（解绑旧账号+注册新账号）。当用户说'换绑zepp账号'、'更换账号'、'重新注册'、'绑定新账号'等时调用。这是一个一步完成解绑和重新注册的操作。",
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
    }
]


def execute_function(function_name: str, arguments: dict) -> dict:
    """执行函数调用"""
    from scheduler import scheduler
    try:
        if function_name == "register_zepp_account":
            result = skills.register_zepp_account(
                arguments.get("user_key"),
                arguments.get("captcha_code")
            )
        elif function_name == "get_bindqr":
            result = skills.get_bindqr(arguments.get("user_key"))
        elif function_name == "bind_device":
            result = skills.bind_device(arguments.get("user_key"))
        elif function_name == "check_bindstatus":
            result = skills.check_bindstatus(arguments.get("user_key"))
        elif function_name == "brush_step":
            result = skills.brush_step(
                arguments.get("user_key"),
                arguments.get("steps")
            )
        elif function_name == "create_scheduled_task":
            result = scheduler.create_task(
                arguments.get("user_key"),
                arguments.get("target_steps"),
                arguments.get("start_hour", 8),
                arguments.get("end_hour", 21)
            )
        elif function_name == "get_scheduled_task":
            task = scheduler.get_task(arguments.get("user_key"))
            if task:
                status_text = {"active": "执行中", "paused": "已暂停", "cancelled": "已取消"}.get(task.get("status"), task.get("status"))
                result = {
                    "success": True,
                    "task": task,
                    "message": f"您有一个定时任务：每天 {task.get('start_hour')}:00-{task.get('end_hour')}:00 完成 {task.get('target_steps')} 步，状态：{status_text}，当前进度：{task.get('current_steps', 0)} 步"
                }
            else:
                result = {"success": False, "message": "您还没有设置定时任务"}
        elif function_name == "get_scheduled_task_detail":
            result = scheduler.get_task_detail(arguments.get("user_key"))
        elif function_name == "update_scheduled_task":
            result = scheduler.update_task(
                arguments.get("user_key"),
                arguments.get("target_steps"),
                arguments.get("start_hour"),
                arguments.get("end_hour")
            )
        elif function_name == "cancel_scheduled_task":
            result = scheduler.cancel_task(arguments.get("user_key"))
        elif function_name == "pause_scheduled_task":
            result = scheduler.pause_task(arguments.get("user_key"))
        elif function_name == "resume_scheduled_task":
            result = scheduler.resume_task(arguments.get("user_key"))
        elif function_name == "check_vip":
            result = skills.check_vip(arguments.get("user_key"))
        elif function_name == "use_card":
            result = skills.use_card(
                arguments.get("user_key"),
                arguments.get("card_key")
            )
        elif function_name == "unbind_zepp_account":
            result = skills.unbind_zepp_account(arguments.get("user_key"))
        elif function_name == "rebind_zepp_account":
            result = skills.rebind_zepp_account(
                arguments.get("user_key"),
                arguments.get("captcha_code")
            )
        else:
            result = {"success": False, "message": f"未知函数: {function_name}"}

        if not result.get("success", False):
            print(f"[Skills] function={function_name} failed args={arguments} result={result}")
        return result
    except Exception as e:
        print(f"[Skills] function={function_name} exception args={arguments} error={e}")
        traceback.print_exc()
        return {
            "success": False,
            "message": f"{function_name} 执行异常：{str(e)}",
            "debug_message": traceback.format_exc()
        }
