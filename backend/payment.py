# -*- coding: utf-8 -*-
"""
微信支付模块
"""
import hashlib
import hmac
import time
import uuid
import requests
from datetime import datetime
from typing import Dict, Optional
from xml.etree import ElementTree

from config import (
    WX_APPID, WX_MCH_ID, WX_API_KEY, WX_NOTIFY_URL,
    APP_DEBUG
)


def generate_order_no() -> str:
    """生成订单号"""
    # 时间戳 + 随机数
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = uuid.uuid4().hex[:8].upper()
    return f"{timestamp}{random_str}"


def md5_sign(data: dict, key: str) -> str:
    """MD5签名（V2接口）"""
    # 按key排序
    sorted_items = sorted(data.items(), key=lambda x: x[0])
    # 拼接字符串
    sign_str = "&".join([f"{k}={v}" for k, v in sorted_items if v])
    sign_str += f"&key={key}"
    # MD5
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()


def verify_sign(data: dict, key: str, sign: str) -> bool:
    """验证签名"""
    calculated_sign = md5_sign(data, key)
    return calculated_sign == sign


def dict_to_xml(data: dict) -> str:
    """字典转XML"""
    xml = "<xml>"
    for k, v in data.items():
        if v:
            xml += f"<{k}><![CDATA[{v}]]></{k}>"
    xml += "</xml>"
    return xml


def xml_to_dict(xml_str: str) -> dict:
    """XML转字典"""
    root = ElementTree.fromstring(xml_str)
    return {child.tag: child.text for child in root}


class WeChatPay:
    """微信支付类"""

    def __init__(self):
        self.appid = WX_APPID
        self.mch_id = WX_MCH_ID
        self.api_key = WX_API_KEY
        self.notify_url = WX_NOTIFY_URL

        # 统一下单URL
        self.unifiedorder_url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
        # 查询订单URL
        self.orderquery_url = "https://api.mch.weixin.qq.com/pay/orderquery"

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.appid and self.mch_id and self.api_key)

    def create_jsapi_order(
        self,
        order_no: str,
        amount: int,
        description: str,
        openid: str
    ) -> Dict:
        """
        创建JSAPI支付订单

        Args:
            order_no: 商户订单号
            amount: 金额（分）
            description: 商品描述
            openid: 用户openid

        Returns:
            dict: 返回支付参数或错误信息
        """
        if not self.is_configured():
            return {
                "success": False,
                "message": "微信支付未配置"
            }

        # 构建请求参数
        params = {
            "appid": self.appid,
            "mch_id": self.mch_id,
            "nonce_str": uuid.uuid4().hex,
            "body": description,
            "out_trade_no": order_no,
            "total_fee": str(amount),
            "spbill_create_ip": "127.0.0.1",
            "notify_url": self.notify_url,
            "trade_type": "JSAPI",
            "openid": openid
        }

        # 签名
        params["sign"] = md5_sign(params, self.api_key)

        # 发送请求
        try:
            xml_data = dict_to_xml(params)
            if APP_DEBUG:
                print(f"[WeChatPay] 请求参数: {params}")

            response = requests.post(
                self.unifiedorder_url,
                data=xml_data.encode('utf-8'),
                headers={"Content-Type": "application/xml"},
                timeout=30
            )

            result = xml_to_dict(response.content)
            if APP_DEBUG:
                print(f"[WeChatPay] 响应: {result}")

            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                prepay_id = result.get("prepay_id")
                return {
                    "success": True,
                    "prepay_id": prepay_id,
                    "order_no": order_no
                }
            else:
                return {
                    "success": False,
                    "message": result.get("return_msg") or result.get("err_code_des") or "下单失败"
                }

        except Exception as e:
            if APP_DEBUG:
                print(f"[WeChatPay] 异常: {e}")
            return {
                "success": False,
                "message": f"支付请求失败: {str(e)}"
            }

    def get_jsapi_params(self, prepay_id: str) -> Dict:
        """
        获取小程序支付参数

        Args:
            prepay_id: 预支付ID

        Returns:
            dict: 小程序调起支付的参数
        """
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex
        package = f"prepay_id={prepay_id}"

        # 签名参数
        sign_params = {
            "appId": self.appid,
            "nonceStr": nonce_str,
            "package": package,
            "signType": "MD5",
            "timeStamp": timestamp
        }

        pay_sign = md5_sign(sign_params, self.api_key)

        return {
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": package,
            "signType": "MD5",
            "paySign": pay_sign
        }

    def query_order(self, order_no: str) -> Dict:
        """
        查询订单状态

        Args:
            order_no: 商户订单号

        Returns:
            dict: 订单信息
        """
        if not self.is_configured():
            return {"success": False, "message": "微信支付未配置"}

        params = {
            "appid": self.appid,
            "mch_id": self.mch_id,
            "out_trade_no": order_no,
            "nonce_str": uuid.uuid4().hex
        }

        params["sign"] = md5_sign(params, self.api_key)

        try:
            xml_data = dict_to_xml(params)
            response = requests.post(
                self.orderquery_url,
                data=xml_data.encode('utf-8'),
                headers={"Content-Type": "application/xml"},
                timeout=30
            )

            result = xml_to_dict(response.content)

            if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
                trade_state = result.get("trade_state")
                return {
                    "success": True,
                    "trade_state": trade_state,
                    "transaction_id": result.get("transaction_id"),
                    "trade_state_desc": result.get("trade_state_desc")
                }
            else:
                return {
                    "success": False,
                    "message": result.get("return_msg") or result.get("err_code_des") or "查询失败"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"查询失败: {str(e)}"
            }

    def parse_notify(self, xml_data: str) -> Dict:
        """
        解析支付回调通知

        Args:
            xml_data: 回调的XML数据

        Returns:
            dict: 解析后的数据
        """
        try:
            data = xml_to_dict(xml_data)

            # 验证签名
            sign = data.pop("sign", None)
            if sign and verify_sign(data, self.api_key, sign):
                return {
                    "success": True,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "message": "签名验证失败"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"解析失败: {str(e)}"
            }

    @staticmethod
    def success_response() -> str:
        """返回成功响应"""
        return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"

    @staticmethod
    def fail_response(msg: str = "FAIL") -> str:
        """返回失败响应"""
        return f"<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[{msg}]]></return_msg></xml>"


# 单例
wechat_pay = WeChatPay()
