# -*- coding: utf-8 -*-
"""
Zepp Life (小米运动) 刷步工具
整合登录、绑定二维码、刷步功能
"""

import urllib.parse
import uuid
import json
import random
import string
import ipaddress
from collections import Counter
import re
import time
import math
import requests
import base64
from io import BytesIO

try:
    from Crypto.Cipher import AES
except ImportError:
    raise ImportError("请先安装依赖: pip install pycryptodome")

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

try:
    import ddddocr
    from PIL import Image, ImageEnhance, ImageFilter
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False

try:
    import tls_client
    TLS_CLIENT_AVAILABLE = True
except ImportError:
    TLS_CLIENT_AVAILABLE = False


def encrypt_login_data(plain: bytes) -> bytes:
    """AES-128-CBC 加密登录数据"""
    key = b'xeNtBVqzDc6tuNTh'
    iv = b'MAAAYAAAAAAAAABg'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pad_len = AES.block_size - (len(plain) % AES.block_size)
    padded = plain + bytes([pad_len]) * pad_len
    return cipher.encrypt(padded)


def get_access_token(location: str) -> str:
    """从重定向URL中提取access token"""
    code_pattern = re.compile(r"(?<=access=).*?(?=&)")
    result = code_pattern.findall(location)
    return result[0] if result else None


class ZeppAPI:
    """Zepp Life API 封装类"""

    def __init__(
        self,
        user: str = None,
        password: str = None,
        verbose: bool = False,
        use_tls: bool = True,
        use_proxy: bool = False,
        enable_spoof_ip: bool = True
    ):
        self.user = None
        self.password = password
        self.verbose = verbose
        self.device_id = str(uuid.uuid4())
        self.userid = None
        self.login_token = None
        self.app_token = None
        self.use_proxy = use_proxy
        self.proxy_url = None
        self.use_tls = use_tls and TLS_CLIENT_AVAILABLE
        self.enable_spoof_ip = enable_spoof_ip
        self._tls_session = None

        # 如果启用代理，获取代理
        if self.use_proxy:
            self._fetch_proxy()

        # 初始化提示
        if self.use_tls:
            if self.use_proxy and self.proxy_url:
                self.log("使用 tls-client + 代理")
            else:
                self.log("使用 tls-client")
        else:
            self.log("使用普通 requests")

        if user:
            self.user = user if ("+86" in user or "@" in user) else f"+86{user}"
            self.is_phone = "+86" in self.user

    def _fetch_proxy(self):
        """从代理 API 获取代理"""
        try:
            from config import PROXY_API_URL
            self.log(f"正在获取代理...")
            resp = requests.get(PROXY_API_URL, timeout=10)
            proxy_text = resp.text.strip()

            # 解析格式: host:port:username:password
            parts = proxy_text.split(':')
            if len(parts) >= 4:
                host = parts[0]
                port = parts[1]
                username = parts[2]
                password = parts[3]
                self.proxy_url = f"http://{username}:{password}@{host}:{port}"
                self.log(f"获取代理成功: {host}:{port}")
            else:
                self.log(f"获取代理失败，格式错误: {proxy_text}")
                self.use_proxy = False
        except Exception as e:
            self.log(f"获取代理异常: {e}")
            self.use_proxy = False

    def log(self, msg: str):
        """打印日志"""
        if self.verbose:
            print(f"[LOG] {msg}")

    @staticmethod
    def _random_public_ipv4() -> str:
        """生成随机公网 IPv4，避免保留/私有网段。"""
        while True:
            ip = ipaddress.IPv4Address(random.getrandbits(32))
            if not (ip.is_private or ip.is_multicast or ip.is_loopback or ip.is_reserved or ip.is_unspecified):
                return str(ip)

    def _add_spoof_ip_headers(self, headers: dict) -> tuple[dict, str]:
        """为请求头附加伪装IP信息。"""
        fake_ip = self._random_public_ipv4()
        merged = dict(headers or {})
        merged.update({
            "X-Forwarded-For": fake_ip,
            "X-Real-IP": fake_ip,
            "Client-IP": fake_ip,
            "CF-Connecting-IP": fake_ip,
            "True-Client-IP": fake_ip,
        })
        return merged, fake_ip

    def _request_with_retry(self, method: str, url: str, max_retries: int = 4, use_proxy=True, **kwargs):
        """
        请求包装：遇到 429 时指数退避重试，避免短时间触发限流。
        支持 tls-client 和普通 requests 两种模式。
        """
        last_resp = None
        for attempt in range(max_retries):
            try:
                if self.use_tls:
                    # 使用 tls-client
                    resp = self._tls_request(method, url, use_proxy=use_proxy, **kwargs)
                else:
                    # 使用普通 requests
                    if use_proxy and self.use_proxy and self.proxy_url:
                        kwargs['proxies'] = {
                            'http': self.proxy_url,
                            'https': self.proxy_url
                        }
                    resp = requests.request(method, url, **kwargs)
            except Exception as e:
                # 代理链路常见错误：握手失败/EOF/连接中断，自动切换代理重试
                if use_proxy and self.use_proxy:
                    self.log(f"请求异常，尝试切换代理后重试({attempt + 1}/{max_retries}): {e}")
                    self._fetch_proxy()
                    time.sleep(min(2.0, 0.3 * (attempt + 1)))
                    continue
                raise

            last_resp = resp
            if resp.status_code != 429:
                return resp

            sleep_s = min(8.0, math.pow(2, attempt)) + random.uniform(0.1, 0.9)
            self.log(f"请求被限流(429)，{attempt + 1}/{max_retries} 次，{sleep_s:.1f}s 后重试: {url}")
            if use_proxy and self.use_proxy:
                self._fetch_proxy()
            time.sleep(sleep_s)

        return last_resp

    def _tls_request(self, method: str, url: str, use_proxy=True, **kwargs):
        """使用 tls-client 发送请求（支持代理）。"""
        # 处理 data 参数
        data = kwargs.get('data')
        if data is not None and isinstance(data, dict):
            kwargs['data'] = urllib.parse.urlencode(data)

        # 处理 timeout
        timeout = kwargs.pop('timeout', 30)
        kwargs.setdefault('timeout_seconds', timeout)

        # 处理 allow_redirects
        allow_redirects = kwargs.pop('allow_redirects', True)
        kwargs['allow_redirects'] = allow_redirects

        if self._tls_session is None:
            self._tls_session = tls_client.Session(
                client_identifier="chrome112",
                random_tls_extension_order=True
            )

        method_upper = method.upper()

        def _send_with(extra_kwargs: dict):
            merged = {**kwargs, **extra_kwargs}
            if method_upper == 'GET':
                return self._tls_session.get(url, **merged)
            if method_upper == 'POST':
                return self._tls_session.post(url, **merged)
            return self._tls_session.execute_request(method_upper, url, **merged)

        if use_proxy and self.use_proxy and self.proxy_url:
            # 优先使用 tls-client 的 proxy 参数，不兼容时回退为 proxies。
            try:
                return _send_with({'proxy': self.proxy_url})
            except TypeError:
                return _send_with({'proxies': {'http': self.proxy_url, 'https': self.proxy_url}})

        return _send_with({})

    def _request(self, method: str, url: str, use_proxy=True, **kwargs):
        """通用请求方法，自动选择 tls-client 或 requests"""
        if self.use_tls:
            return self._tls_request(method, url, use_proxy=use_proxy, **kwargs)
        else:
            # 普通请求也支持代理
            if use_proxy and self.use_proxy and self.proxy_url:
                kwargs['proxies'] = {
                    'http': self.proxy_url,
                    'https': self.proxy_url
                }
            return requests.request(method, url, **kwargs)

    # ==================== 登录相关 ====================

    def login(self) -> dict:
        """
        登录Zepp账号，获取userid、login_token等信息

        Returns:
            dict: {
                'success': bool,
                'userid': str,
                'login_token': str,
                'app_token': str,
                'message': str
            }
        """
        if not self.user or not self.password:
            return {'success': False, 'message': '请提供用户名和密码'}

        self.log(f"开始登录, 账号: {self.user}, 设备ID: {self.device_id}")

        try:
            # 第一步: 获取access code
            url1 = "https://api-user.zepp.com/v2/registrations/tokens"
            headers1 = {
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "user-agent": "MiFit6.14.0 (M2007J1SC; Android 12; Density/2.75)",
                "app_name": "com.xiaomi.hm.health",
                "appname": "com.xiaomi.hm.health",
                "appplatform": "android_phone",
                "x-hm-ekv": "1",
                "hm-privacy-ceip": "false"
            }
            if self.enable_spoof_ip:
                headers1, fake_ip1 = self._add_spoof_ip_headers(headers1)
                self.log(f"[步骤1] 伪装IP: {fake_ip1}")

            login_data = {
                'emailOrPhone': self.user,
                'password': self.password,
                'state': 'REDIRECTION',
                'client_id': 'HuaMi',
                'country_code': 'CN',
                'token': 'access',
                'redirect_uri': 'https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html',
            }

            query = urllib.parse.urlencode(login_data)
            cipher_data = encrypt_login_data(query.encode('utf-8'))
            self.log(f"登录数据加密完成, 长度: {len(cipher_data)}")

            self.log(f"[步骤1] 请求: POST {url1}")
            r1 = self._request("POST", url1, data=cipher_data, headers=headers1, allow_redirects=False, timeout=15)
            self.log(f"[步骤1] 响应状态码: {r1.status_code}")

            if r1.status_code != 303:
                self.log(f"[步骤1] 响应内容: {r1.text[:500]}")
                return {'success': False, 'message': f'登录第一步失败, status: {r1.status_code}'}

            location = r1.headers.get("Location", "")
            self.log(f"[步骤1] 重定向Location: {location[:100]}...")
            code = get_access_token(location)
            if not code:
                return {'success': False, 'message': '获取access token失败'}
            self.log(f"[步骤1] 获取access code成功: {code[:20]}...")

            # 第二步: 获取login_token
            url2 = "https://account.huami.com/v2/client/login"
            headers2 = {
                "app_name": "com.xiaomi.hm.health",
                "x-request-id": str(uuid.uuid4()),
                "accept-language": "zh-CN",
                "appname": "com.xiaomi.hm.health",
                "cv": "50818_6.14.0",
                "v": "2.0",
                "appplatform": "android_phone",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
            if self.enable_spoof_ip:
                headers2, fake_ip2 = self._add_spoof_ip_headers(headers2)
                self.log(f"[步骤2] 伪装IP: {fake_ip2}")

            if self.is_phone:
                data2 = {
                    "app_name": "com.xiaomi.hm.health",
                    "app_version": "6.14.0",
                    "code": code,
                    "country_code": "CN",
                    "device_id": self.device_id,
                    "device_model": "phone",
                    "grant_type": "access_token",
                    "third_name": "huami_phone",
                }
            else:
                data2 = {
                    "allow_registration=": "false",
                    "app_name": "com.xiaomi.hm.health",
                    "app_version": "6.14.0",
                    "code": code,
                    "country_code": "CN",
                    "device_id": self.device_id,
                    "device_model": "android_phone",
                    "dn": "account.zepp.com,api-user.zepp.com,api-mifit.zepp.com,api-watch.zepp.com",
                    "grant_type": "access_token",
                    "lang": "zh_CN",
                    "os_version": "1.5.0",
                    "source": "com.xiaomi.hm.health:6.14.0:50818",
                    "third_name": "email",
                }

            self.log(f"[步骤2] 请求: POST {url2}")
            r2 = self._request("POST", url2, data=data2, headers=headers2, timeout=15)
            self.log(f"[步骤2] 响应状态码: {r2.status_code}")
            self.log(f"[步骤2] 响应内容: {r2.text[:500]}")
            r2_json = r2.json()

            if "token_info" not in r2_json:
                return {'success': False, 'message': f'登录失败: {r2.text[:200]}'}

            self.login_token = r2_json["token_info"]["login_token"]
            self.userid = r2_json["token_info"]["user_id"]
            self.log(f"[步骤2] 登录成功! userid: {self.userid}")

            # 第三步: 获取app_token
            self.app_token = self._get_app_token(self.login_token)

            return {
                'success': True,
                'userid': self.userid,
                'login_token': self.login_token,
                'app_token': self.app_token,
                'message': '登录成功'
            }

        except Exception as e:
            self.log(f"登录异常: {str(e)}")
            return {'success': False, 'message': f'登录异常: {str(e)}'}

    def _get_app_token(self, login_token: str) -> str:
        """获取app_token"""
        url = f"https://account-cn.huami.com/v1/client/app_tokens?app_name=com.xiaomi.hm.health&dn=api-user.huami.com,api-mifit.huami.com,app-analytics.huami.com&login_token={login_token}"
        headers = {'User-Agent': 'MiFit/5.3.0 (iPhone; iOS 14.7.1; Scale/3.00)'}
        if self.enable_spoof_ip:
            headers, fake_ip3 = self._add_spoof_ip_headers(headers)
            self.log(f"[步骤3] 伪装IP: {fake_ip3}")
        self.log(f"[步骤3] 请求: GET app_token")
        response = self._request("GET", url, headers=headers, timeout=15)
        self.log(f"[步骤3] 响应状态码: {response.status_code}")
        resp_json = response.json()
        app_token = resp_json['token_info']['app_token']
        self.log(f"[步骤3] 获取app_token成功")
        return app_token

    # ==================== 图片验证码相关 ====================

    @staticmethod
    def _captcha_random_suffix() -> str:
        """生成验证码 random 后缀：两位字母 + 两位数字"""
        letters = ''.join(random.choices(string.ascii_letters, k=2))
        digits = ''.join(random.choices(string.digits, k=2))
        return f"{letters}{digits}"

    def get_captcha(self, captcha_type: str = "register", save_path: str = None,
                    auto_ocr: bool = False) -> dict:
        """
        获取图片验证码

        Args:
            captcha_type: 验证码类型 (register/login 等)
            save_path: 图片保存路径
            auto_ocr: 是否自动OCR识别

        Returns:
            dict: {
                'success': bool,
                'key': str,           # captcha-key，后续请求需要带上
                'code': str,          # OCR识别结果（auto_ocr=True时）
                'image_path': str,    # 图片保存路径
                'image_base64': str,  # 图片base64
                'message': str
            }
        """
        try:
            # 验证码接口对代理质量敏感，每次请求前刷新代理，避免重复命中坏节点
            if self.use_proxy:
                self._fetch_proxy()

            random_num = self._captcha_random_suffix()

            url = f"https://api-user.huami.com/captcha/{captcha_type}?random={random_num}"
            self.log(f"获取验证码: {url}")

            response = self._request_with_retry("GET", url, timeout=10, use_proxy=True)
            self.log(f"响应状态码: {response.status_code}")
            self.log(f"响应头: {dict(response.headers)}")

            if response.status_code == 200:
                # 从响应头获取 captcha-key（兼容大小写）
                captcha_key = None
                headers_lower = {k.lower(): v for k, v in response.headers.items()}
                captcha_key = headers_lower.get('captcha-key')

                # 如果没有直接找到，尝试从 Set-Cookie 中解析
                if not captcha_key:
                    set_cookie = headers_lower.get('set-cookie', '')
                    if 'captcha-key=' in set_cookie:
                        # 解析 cookie 值
                        import re
                        match = re.search(r'captcha-key=([^;]+)', set_cookie)
                        if match:
                            captcha_key = match.group(1)

                self.log(f"captcha-key: {captcha_key}")

                if not captcha_key:
                    return {'success': False, 'message': '响应头中没有captcha-key'}

                # 保存图片
                image_data = response.content
                image_base64 = base64.b64encode(image_data).decode()

                result = {
                    'success': True,
                    'key': captcha_key,
                    'image_base64': f"data:image/png;base64,{image_base64}",
                    'message': '获取验证码成功'
                }

                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(image_data)
                    result['image_path'] = save_path
                    self.log(f"验证码图片已保存: {save_path}")

                # 自动OCR识别
                if auto_ocr:
                    if DDDDOCR_AVAILABLE:
                        try:
                            code = ocr_captcha(image_data)
                            result['code'] = code
                            self.log(f"OCR识别结果: {code}")
                        except Exception as e:
                            self.log(f"OCR识别失败: {e}")
                            result['ocr_error'] = str(e)
                    else:
                        result['ocr_error'] = 'ddddocr未安装'

                return result
            else:
                return {'success': False, 'message': f'获取验证码失败: {response.status_code}'}

        except Exception as e:
            self.log(f"获取验证码异常: {str(e)}")
            return {'success': False, 'message': f'获取验证码异常: {str(e)}'}

    def verify_captcha(self, captcha_type: str, key: str, code: str) -> dict:
        """
        校验图片验证码

        Args:
            captcha_type: 验证码类型
            key: captcha-key
            code: 用户输入的验证码

        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            url = f"https://api-user.huami.com/captcha/{captcha_type}?key={key}&code={code}"
            self.log(f"校验验证码: {url}")

            response = self._request("POST", url, timeout=10)
            self.log(f"响应状态码: {response.status_code}")
            self.log(f"响应内容: {response.text}")

            if response.status_code == 200:
                return {'success': True, 'message': '验证码校验成功'}
            else:
                return {'success': False, 'message': f'验证码校验失败: {response.text}'}

        except Exception as e:
            return {'success': False, 'message': f'验证码校验异常: {str(e)}'}

    def register_account(self, account: str, password: str, name: str,
                         captcha_key: str, captcha_code: str) -> dict:
        """
        注册新账号

        Args:
            account: 手机号或邮箱
            password: 密码
            name: 用户名/昵称
            captcha_key: 验证码key
            captcha_code: 用户输入的验证码

        Returns:
            dict: {'success': bool, 'code': str, 'message': str}
        """
        try:
            # 处理账号格式
            if '@' not in account:
                prefix_account = urllib.parse.quote(f"+86{account}")
            else:
                prefix_account = account

            url1 = f"https://api-user.huami.com/registrations/{prefix_account}"
            data1 = {
                'app_name': 'com.huami.webapp',
                'country_code': 'CN',
                'countryState': '',
                'password': password,
                'name': name,
                'code': captcha_code,
                'key': captcha_key,
                'client_id': 'HuaMi',
                'redirect_uri': 'https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html',
                'state': 'REDIRECTION',
                'token': 'access',
                'json_response': 'true'
            }
            headers = {
                'app_name': 'com.huami.webapp',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }

            # 第一步: 注册并拿到重定向里的 access code
            self.log(f"注册账号(步骤1): {url1}")
            self.log(f"[注册步骤1] 请求参数: {data1}")
            response1 = self._request_with_retry(
                "POST",
                url1,
                data=urllib.parse.urlencode(data1),
                headers=headers,
                timeout=15,
                max_retries=5
            )
            self.log(f"[注册步骤1] 状态码: {response1.status_code}")
            self.log(f"[注册步骤1] 响应: {response1.text[:500]}")

            if response1.status_code not in (200, 201):
                return {'success': False, 'message': f'注册失败(步骤1): {response1.text[:200]}'}

            resp1_json = response1.json()
            data_url = resp1_json.get('data', '')
            if not data_url:
                return {'success': False, 'message': f'注册失败(步骤1无data): {response1.text[:200]}'}

            parsed = urllib.parse.urlparse(data_url)
            qs = urllib.parse.parse_qs(parsed.query)
            access_code = (qs.get('access') or [''])[0]
            if not access_code:
                return {'success': False, 'message': f'注册失败(步骤1无access): {data_url[:200]}'}

            # 第二步: 用 access code 换 token_info
            url2 = "https://account.huami.com/v1/client/register"
            data2 = {
                'app_name': 'com.huami.webapp',
                'app_version': '4.3.0',
                'code': access_code,
                'countryState': '',
                'country_code': 'CN',
                'device_id': '02:00:00:00:00:00',
                'device_model': 'web',
                'grant_type': 'access_token',
                'third_name': 'huami',
            }
            self.log(f"注册账号(步骤2): {url2}")
            response2 = self._request_with_retry(
                "POST",
                url2,
                data=urllib.parse.urlencode(data2),
                headers=headers,
                timeout=15,
                max_retries=3
            )
            self.log(f"[注册步骤2] 状态码: {response2.status_code}")
            self.log(f"[注册步骤2] 响应: {response2.text[:500]}")

            if response2.status_code not in (200, 201):
                return {'success': False, 'message': f'注册失败(步骤2): {response2.text[:200]}'}

            resp2_json = response2.json()
            if resp2_json.get('result') != 'ok' or 'token_info' not in resp2_json:
                return {'success': False, 'message': f'注册失败(步骤2返回异常): {response2.text[:200]}'}

            return {
                'success': True,
                'code': access_code,
                'message': '注册成功'
            }

        except Exception as e:
            return {'success': False, 'message': f'注册异常: {str(e)}'}

    # ==================== 二维码绑定相关 ====================

    def get_qrcode_ticket(self, userid: str = None) -> dict:
        """
        获取绑定二维码的ticket

        Args:
            userid: Zepp账户的userid，如果不传则使用登录后的userid

        Returns:
            dict: {
                'success': bool,
                'ticket': str,  # 二维码ticket，可用于生成二维码
                'message': str
            }
        """
        userid = userid or self.userid
        if not userid:
            return {'success': False, 'message': '请先登录或提供userid'}

        try:
            api_url = "https://weixin.amazfit.com/v1/bind/qrcode.json"
            params = {
                'wxname': 'md',
                'brandName': 'amazfit',
                'userid': userid
            }

            self.log(f"获取二维码ticket - userid: {userid}")
            response = self._request("GET", api_url, params=params, timeout=10)
            self.log(f"响应状态码: {response.status_code}")
            self.log(f"响应内容: {response.text}")

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1 and 'data' in data:
                    ticket = data['data'].get('ticket')
                    if ticket:
                        self.log(f"获取ticket成功: {ticket}")
                        return {
                            'success': True,
                            'ticket': ticket,
                            'message': '获取二维码成功'
                        }

            return {'success': False, 'message': f'获取二维码失败: {response.text[:200]}'}

        except Exception as e:
            self.log(f"获取二维码异常: {str(e)}")
            return {'success': False, 'message': f'获取二维码异常: {str(e)}'}

    def check_bind_status(self, userid: str = None) -> dict:
        """
        检查Zepp账号绑定状态

        Args:
            userid: Zepp账户的userid

        Returns:
            dict: {
                'success': bool,
                'is_bound': bool,
                'message': str
            }
        """
        userid = userid or self.userid
        if not userid:
            return {'success': False, 'is_bound': False, 'message': '请先登录或提供userid'}

        try:
            api_url = "https://weixin.amazfit.com/v1/info/users.json"
            params = {
                'wxname': 'md',
                'userid': userid
            }

            self.log(f"检查绑定状态 - userid: {userid}")
            response = self._request("GET", api_url, params=params, timeout=10)
            self.log(f"响应状态码: {response.status_code}")
            self.log(f"响应内容: {response.text}")

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1 and 'data' in data:
                    is_bind = data['data'].get('isbind', 0)
                    is_bound = is_bind == 1
                    self.log(f"绑定状态: {is_bound}")
                    return {
                        'success': True,
                        'is_bound': is_bound,
                        'message': '已绑定' if is_bound else '未绑定'
                    }

            return {'success': False, 'is_bound': False, 'message': f'检查绑定状态失败: {response.text[:200]}'}

        except Exception as e:
            self.log(f"检查绑定状态异常: {str(e)}")
            return {'success': False, 'is_bound': False, 'message': f'检查绑定状态异常: {str(e)}'}

    # ==================== 第三方API绑定/刷步 ====================

    def bindband_via_api(self, user: str = None, password: str = None,
                         step: int = 1, apikey: str = None) -> dict:
        """
        通过第三方API绑定手环并刷步（api.nan.run）

        Args:
            user: 手机号或邮箱（不传则使用初始化时的账号）
            password: 密码
            step: 步数，默认1（仅用于绑定时传1）
            apikey: API密钥

        Returns:
            dict: {
                'success': bool,
                'userid': str,
                'step': int,
                'message': str
            }
        """
        user = user or (self.user.replace('+86', '') if self.user else None)
        password = password or self.password

        if not user or not password:
            return {'success': False, 'message': '请提供用户名和密码'}

        # 部署 key 必须来自环境配置（NANRUN_API_KEY）
        if not apikey:
            try:
                from config import NANRUN_API_KEY
                apikey = NANRUN_API_KEY
            except Exception:
                try:
                    from backend.config import NANRUN_API_KEY
                    apikey = NANRUN_API_KEY
                except Exception:
                    apikey = ""

        if not apikey:
            return {
                'success': False,
                'message': '未配置部署key：请在 .env 中设置 NANRUN_API_KEY'
            }

        try:
            url = "https://api.nan.run/api/xiaomisport"
            params = {
                'apikey': apikey,
                'user': user,
                'pass': password,
                'step': step
            }

            self.log(f"调用第三方API: {url}")
            self.log(f"参数: user={user}, step={step}")
            self.log(f"部署key: {'*' * max(0, len(apikey) - 6)}{apikey[-6:]}")

            # 绑定接口强制走普通 requests 直连，不使用代理与 TLS 指纹
            response = requests.get(url, params=params, timeout=30)
            self.log(f"响应状态码: {response.status_code}")
            self.log(f"响应内容: {response.text}")

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    return {'success': False, 'message': f'接口返回非JSON: {response.text[:200]}'}

                code = data.get('code')
                msg = data.get('msg', '未知错误')
                is_success = str(code) == '200'
                if is_success:
                    user_id = data.get('user_id') or data.get('userid') or data.get('uid')
                    self.userid = user_id
                    return {
                        'success': True,
                        'userid': user_id,
                        'step': data.get('step'),
                        'message': msg or '成功'
                    }
                else:
                    return {
                        'success': False,
                        'message': msg or '未知错误'
                    }
            else:
                return {'success': False, 'message': f'HTTP错误: {response.status_code}'}

        except Exception as e:
            self.log(f"API调用异常: {str(e)}")
            return {'success': False, 'message': f'调用异常: {str(e)}'}

    # ==================== 刷步相关 ====================

    def _build_data_json(self, step: int, today: str) -> str:
        """构建步数数据JSON"""
        distance = int(step * 0.6)
        calories = int(step * 0.04)

        data = [{
            "data_hr": "/////0v///9W////S////17///9J/2n//0v/////////R/////9F/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+",
            "date": today,
            "data": [{
                "start": 0,
                "stop": 1439,
                "value": "UA8AUBQAUAwAUBoAUAEAYCcAUBkAUB4AUBgAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAAfgAA"
            }],
            "tz": "32",
            "did": f"DA932FFFFE{random.randint(100000, 999999):06X}",
            "src": 24
        }]

        summary = {
            "v": 6,
            "slp": {
                "st": int(time.time()) - 28800,
                "ed": int(time.time()) - 28800,
                "dp": 0, "lt": 0, "wk": 0,
                "usrSt": -1440, "usrEd": -1440,
                "wc": 0, "is": 0, "lb": 0, "to": 0, "dt": 0, "rhr": 0, "ss": 0
            },
            "stp": {
                "ttl": step,
                "dis": distance,
                "cal": calories,
                "wk": 0,
                "rn": 0,
                "runDist": 0,
                "runCal": 0,
                "stage": []
            },
            "goal": 8000,
            "tz": "28800"
        }

        result = [{
            "data_hr": data[0]["data_hr"],
            "date": today,
            "data": data[0]["data"],
            "summary": json.dumps(summary, separators=(',', ':')),
            "source": 24,
            "type": 0
        }]

        return urllib.parse.quote(json.dumps(result, separators=(',', ':')))

    def update_step(self, step: int) -> dict:
        """
        更新步数

        Args:
            step: 目标步数

        Returns:
            dict: {
                'success': bool,
                'step': int,
                'message': str
            }
        """
        self.log(f"========== 开始刷步: {step} 步 ==========")

        # 如果还没登录，先登录
        if not self.login_token or not self.app_token:
            login_result = self.login()
            if not login_result['success']:
                return {'success': False, 'step': step, 'message': login_result['message']}

        today = time.strftime("%Y-%m-%d")
        t = str(int(time.time() * 1000))
        self.log(f"[步骤4] 日期: {today}, 时间戳: {t}")

        data_json = self._build_data_json(step, today)
        self.log(f"[步骤4] data_json长度: {len(data_json)}")

        url = f'https://api-mifit-cn.huami.com/v1/data/band_data.json?&t={t}'
        headers = {
            "apptoken": self.app_token,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = f'userid={self.userid}&last_sync_data_time=1597306380&device_type=0&last_deviceid=DA932FFFFE8816E7&data_json={data_json}'
        self.log(f"[步骤4] 请求: POST {url}")

        response = self._request("POST", url, data=data, headers=headers, timeout=15)
        self.log(f"[步骤4] 响应状态码: {response.status_code}")
        self.log(f"[步骤4] 响应内容: {response.text}")

        result = response.json()
        code = result.get('code', 0)
        msg = result.get('message', 'unknown')

        self.log(f"========== 刷步完成 ==========")

        # code=1 或 message=ok/success 都算成功
        if code == 1 or msg in ('ok', 'success'):
            return {'success': True, 'step': step, 'message': f'步数修改成功: {step}'}
        else:
            return {'success': False, 'step': step, 'message': f'刷步失败: {msg}'}


# ==================== 验证码OCR识别 ====================

def ocr_captcha(image_data: bytes) -> str:
    """
    识别验证码图片

    Args:
        image_data: 图片二进制数据

    Returns:
        str: 识别结果
    """
    if not DDDDOCR_AVAILABLE:
        raise ImportError("请先安装依赖: pip install ddddocr pillow")

    # 确保数据是bytes
    if isinstance(image_data, str):
        image_data = image_data.encode('utf-8')

    # 检查数据是否有效
    if not image_data or len(image_data) < 100:
        raise ValueError(f"图片数据无效，长度: {len(image_data) if image_data else 0}")

    # 预处理图片
    img = Image.open(BytesIO(image_data))

    # 处理透明通道
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # 图片预处理增强 OCR 准确率
    # 1. 放大图片 (2倍)
    width, height = img.size
    img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)

    # 2. 转灰度
    img = img.convert('L')

    # 3. 增强对比度
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # 4. 锐化
    img = img.filter(ImageFilter.SHARPEN)

    # 5. 二值化处理
    threshold = 128
    img = img.point(lambda x: 255 if x > threshold else 0)

    # 转为bytes
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    # OCR识别 - 多次尝试取最常见结果
    ocr = ddddocr.DdddOcr(show_ad=False)
    results = []
    for _ in range(3):
        buf.seek(0)
        result = ocr.classification(buf.read())
        if result:
            results.append(result.lower().strip())

    # 返回最常见的结果
    if results:
        counter = Counter(results)
        return counter.most_common(1)[0][0]

    return ""


# ==================== 二维码生成 ====================

def generate_qrcode(data: str, save_path: str = None) -> str:
    """
    生成二维码

    Args:
        data: 二维码内容
        save_path: 保存路径，如果不传则返回base64

    Returns:
        str: 如果save_path为空，返回base64字符串；否则返回保存路径
    """
    if not QRCODE_AVAILABLE:
        raise ImportError("请先安装依赖: pip install qrcode[pil]")

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    if save_path:
        img.save(save_path)
        return save_path
    else:
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"


# ==================== 便捷函数 ====================

def get_zepp_info(user: str, password: str, verbose: bool = False, qrcode_path: str = None) -> dict:
    """
    获取Zepp账号信息（userid和绑定二维码ticket）

    Args:
        user: 手机号或邮箱
        password: 密码
        verbose: 是否打印详细日志
        qrcode_path: 二维码保存路径，如果传入则生成二维码图片

    Returns:
        dict: {
            'success': bool,
            'userid': str,
            'ticket': str,
            'qrcode': str,  # 二维码图片路径或base64
            'message': str
        }
    """
    api = ZeppAPI(user, password, verbose)

    # 登录
    login_result = api.login()
    if not login_result['success']:
        return login_result

    # 获取二维码ticket
    qr_result = api.get_qrcode_ticket()

    result = {
        'success': qr_result['success'],
        'userid': api.userid,
        'ticket': qr_result.get('ticket'),
        'login_token': api.login_token,
        'app_token': api.app_token,
        'message': qr_result['message']
    }

    # 如果需要生成二维码图片
    if qr_result['success'] and qr_result.get('ticket') and QRCODE_AVAILABLE:
        try:
            qrcode_data = generate_qrcode(qr_result['ticket'], qrcode_path)
            result['qrcode'] = qrcode_data
        except Exception as e:
            result['qrcode_error'] = str(e)

    return result


def bindband(user: str, password: str, step: int = 1, verbose: bool = False, use_proxy: bool = False) -> dict:
    """
    通过第三方API绑定手环

    Args:
        user: 手机号或邮箱
        password: 密码
        step: 步数，默认1
        verbose: 是否打印详细日志
        use_proxy: 保留参数（绑定接口固定不走代理）

    Returns:
        dict: {'success': bool, 'userid': str, 'message': str}
    """
    # 绑定接口固定普通请求：不启用代理，不启用 TLS 客户端
    api = ZeppAPI(verbose=verbose, use_tls=False, use_proxy=False, enable_spoof_ip=False)
    return api.bindband_via_api(user, password, step)


def check_bindstatus(userid: str, verbose: bool = False, use_proxy: bool = False) -> dict:
    """
    检查绑定状态

    Args:
        userid: Zepp账户的userid
        verbose: 是否打印详细日志
        use_proxy: 是否使用代理

    Returns:
        dict: {
            'success': bool,
            'is_bound': bool,
            'message': str
        }
    """
    api = ZeppAPI(verbose=verbose, use_tls=False, use_proxy=False, enable_spoof_ip=False)
    return api.check_bind_status(userid)


def brush_step(user: str, password: str, step: int, verbose: bool = False) -> dict:
    """
    刷步数主函数

    Args:
        user: 手机号或邮箱
        password: 密码
        step: 目标步数
        verbose: 是否打印详细日志

    Returns:
        dict: {
            'success': bool,
            'step': int,
            'message': str
        }
    """
    try:
        api = ZeppAPI(user, password, verbose)
        return api.update_step(step)
    except Exception as e:
        import traceback
        if verbose:
            traceback.print_exc()
        return {'success': False, 'step': step, 'message': f'刷步失败: {str(e)}'}


# ==================== 命令行入口 ====================

def print_help():
    print("""
Zepp Life 刷步工具

用法:
  python step_brush.py <命令> [参数] [选项]

命令:
  login <手机号> <密码>              登录并获取账号信息(userid, ticket)
  qrcode <ticket_url> [保存路径]    根据ticket生成二维码图片
  bindstatus <userid>               检查绑定状态
  brush <手机号> <密码> <步数>       刷步数

  bindband <账号> <密码> [步数]      通过第三方API绑定手环(步数默认1)
  captcha [类型]                    获取图片验证码 (类型: register/login)
  register <手机号> <密码> <昵称>    注册新账号 (需要先获取验证码)

选项:
  -v, --verbose                     显示详细日志
  --qr                              登录时同时生成二维码图片

示例:
  python step_brush.py login 13800138000 password123 -v --qr
  python step_brush.py qrcode "http://we.qq.com/d/xxx" ./qr.png
  python step_brush.py bindstatus 1234567890
  python step_brush.py brush 13800138000 password123 20000 -v

  # 绑定手环（第三方API，自动绑定无需扫码）:
  python step_brush.py bindband email@example.com password123

  # 注册流程:
  python step_brush.py captcha register     # 获取验证码图片+自动OCR识别
  python step_brush.py register 13800138000 password123 nickname <key> <code>
""")


if __name__ == "__main__":
    import sys
    import os

    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    gen_qr = "--qr" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ["-v", "--verbose", "--qr"]]

    if len(args) == 0:
        print_help()
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == "login" and len(args) == 3:
        user, password = args[1], args[2]
        print(f"正在登录账号 {user[:3]}***{user[-4:]}...")

        qrcode_path = None
        if gen_qr:
            qrcode_path = os.path.join(os.path.dirname(__file__) or '.', 'bind_qrcode.png')

        result = get_zepp_info(user, password, verbose, qrcode_path)
        if result['success']:
            print(f"\n登录成功!")
            print(f"  userid: {result['userid']}")
            print(f"  ticket: {result['ticket']}")
            if result.get('qrcode'):
                print(f"  二维码已保存: {result['qrcode']}")
        else:
            print(f"\n登录失败: {result['message']}")

    elif cmd == "bindband" and len(args) >= 3:
        user, password = args[1], args[2]
        step = int(args[3]) if len(args) > 3 else 1
        print(f"正在通过第三方API绑定手环 {user}...")
        result = bindband(user, password, step, verbose)
        if result['success']:
            print(f"\n成功!")
            print(f"  userid: {result.get('userid')}")
            print(f"  步数: {result.get('step')}")
            print(f"  消息: {result['message']}")
        else:
            print(f"\n失败: {result['message']}")

    elif cmd == "captcha":
        captcha_type = args[1] if len(args) > 1 else "register"
        save_path = f"captcha_{captcha_type}.png"
        auto_ocr = "--ocr" in sys.argv or "-o" in sys.argv
        print(f"正在获取 {captcha_type} 验证码...")

        api = ZeppAPI(verbose=verbose)
        result = api.get_captcha(captcha_type, save_path, auto_ocr=True)

        if result['success']:
            print(f"\n获取成功!")
            print(f"  captcha-key: {result['key']}")
            print(f"  图片已保存: {result.get('image_path', save_path)}")

            if result.get('code'):
                print(f"  OCR识别结果: {result['code']}")
                print(f"\n注册命令:")
                print(f"  python step_brush.py register <手机号> <密码> <昵称> {result['key']} {result['code']}")
            elif result.get('ocr_error'):
                print(f"  OCR识别失败: {result['ocr_error']}")
                print(f"\n请查看验证码图片，手动输入验证码:")
                print(f"  python step_brush.py register <手机号> <密码> <昵称> {result['key']} <验证码>")
            else:
                print(f"\n请查看验证码图片，然后使用以下命令注册:")
                print(f"  python step_brush.py register <手机号> <密码> <昵称> {result['key']} <验证码>")
        else:
            print(f"\n获取失败: {result['message']}")

    elif cmd == "register" and len(args) == 6:
        account, password, name, captcha_key, captcha_code = args[1], args[2], args[3], args[4], args[5]
        print(f"正在注册账号 {account}...")

        api = ZeppAPI(verbose=verbose)
        result = api.register_account(account, password, name, captcha_key, captcha_code)

        if result['success']:
            print(f"\n注册成功!")
            print(f"  code: {result.get('code')}")
        else:
            print(f"\n注册失败: {result['message']}")

    elif cmd == "qrcode" and len(args) >= 2:
        ticket = args[1]
        save_path = args[2] if len(args) > 2 else 'bind_qrcode.png'
        print(f"正在生成二维码...")
        if not QRCODE_AVAILABLE:
            print("错误: 请先安装依赖: pip install qrcode[pil]")
            sys.exit(1)
        try:
            result = generate_qrcode(ticket, save_path)
            print(f"二维码已保存: {result}")
        except Exception as e:
            print(f"生成失败: {e}")

    elif cmd == "bindstatus" and len(args) == 2:
        userid = args[1]
        print(f"正在检查绑定状态 userid: {userid}...")
        result = check_bindstatus(userid, verbose)
        if result['success']:
            status = "已绑定" if result['is_bound'] else "未绑定"
            print(f"\n绑定状态: {status}")
        else:
            print(f"\n检查失败: {result['message']}")

    elif cmd == "brush" and len(args) == 4:
        user, password, step = args[1], args[2], int(args[3])
        print(f"正在为账号 {user[:3]}***{user[-4:]} 刷步 {step}...")
        result = brush_step(user, password, step, verbose)
        if result['success']:
            print(f"\n成功: {result['message']}")
        else:
            print(f"\n失败: {result['message']}")

    else:
        print_help()
