# -*- coding: utf-8 -*-
"""
AI 模型客户端 - 支持 MiniMax 和 GLM
"""
import json
import traceback
import requests
from typing import List, Dict, Any
from config import (
    AI_PROVIDER, MINIMAX_API_KEY, MINIMAX_GROUP_ID,
    GLM_API_KEY, SYSTEM_PROMPT, STEALTH_PROMPT, ERROR_MESSAGE, APP_DEBUG
)
from skills import FUNCTIONS, execute_function, skills
from models import get_db_session, SystemConfig


def is_stealth_mode() -> bool:
    """检查是否开启伪装模式"""
    try:
        with get_db_session() as db:
            config = db.query(SystemConfig).filter(
                SystemConfig.config_key == "stealth_mode"
            ).first()
            if config:
                return config.config_value.lower() in ("1", "true", "yes", "on")
            return True  # 默认开启伪装模式，更安全
    except Exception:
        return True  # 出错时默认开启伪装模式


class AIClient:
    """AI 模型客户端"""

    def __init__(self, provider: str = None):
        self.provider = provider or AI_PROVIDER

    def chat(self, user_key: str, messages: List[Dict], user_input: str) -> Dict[str, Any]:
        """
        发送聊天请求

        Args:
            user_key: 用户标识
            messages: 历史消息列表
            user_input: 用户输入

        Returns:
            dict: {
                'success': bool,
                'reply': str,           # AI 回复文本
                'images': list,         # 图片列表 (base64)
                'function_result': dict # 函数执行结果
            }
        """
        # 检查是否开启伪装模式
        stealth = is_stealth_mode()

        # 获取用户状态
        user_status = skills.get_user_status(user_key)

        # 根据模式选择系统提示
        if stealth:
            # 伪装模式：正常AI对话助手
            system_prompt = STEALTH_PROMPT.format(user_key=user_key)
        else:
            # 正常模式：刷步助手
            system_prompt = SYSTEM_PROMPT.format(
                user_key=user_key,
                user_status=user_status
            )

        # 添加用户消息
        messages = messages.copy()
        messages.append({"role": "user", "content": user_input})

        try:
            if self.provider == "minimax":
                return self._chat_minimax(system_prompt, messages, user_key, stealth)
            elif self.provider == "glm":
                return self._chat_glm(system_prompt, messages, user_key, stealth)
            else:
                return {"success": False, "reply": f"不支持的AI提供商: {self.provider}"}
        except Exception as e:
            print(f"[AIClient] chat exception: {e}")
            traceback.print_exc()
            return {
                "success": False,
                "reply": ERROR_MESSAGE,
                "function_result": {
                    "success": False,
                    "message": str(e),
                    "debug_message": traceback.format_exc() if APP_DEBUG else ""
                }
            }

    def _chat_minimax(self, system_prompt: str, messages: List[Dict], user_key: str, stealth: bool = False) -> Dict:
        """MiniMax API 调用"""
        url = f"https://api.minimax.chat/v1/text/chatcompletion_v2"

        headers = {
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json"
        }

        # 转换消息格式
        mm_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            mm_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        payload = {
            "model": "abab6.5s-chat",
            "messages": mm_messages
        }

        # 只在非伪装模式下添加工具
        if not stealth:
            payload["tools"] = [{"type": "function", "function": f} for f in FUNCTIONS]
            payload["tool_choice"] = "auto"

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()

        if "choices" not in data:
            print(f"[AIClient] MiniMax invalid response: {data}")
            return {
                "success": False,
                "reply": ERROR_MESSAGE,
                "function_result": {
                    "success": False,
                    "message": f"MiniMax返回异常: {data}"
                }
            }

        choice = data["choices"][0]
        message = choice.get("message", {})

        # 检查是否有函数调用（仅在非伪装模式下）
        if not stealth:
            tool_calls = message.get("tool_calls", [])
            if tool_calls:
                return self._handle_function_call(tool_calls[0], user_key)

        return {
            "success": True,
            "reply": message.get("content", ""),
            "images": []
        }

    def _chat_glm(self, system_prompt: str, messages: List[Dict], user_key: str, stealth: bool = False) -> Dict:
        """GLM API 调用"""
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

        headers = {
            "Authorization": f"Bearer {GLM_API_KEY}",
            "Content-Type": "application/json"
        }

        # 转换消息格式
        glm_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            glm_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        payload = {
            "model": "glm-4",
            "messages": glm_messages
        }

        # 只在非伪装模式下添加工具
        if not stealth:
            payload["tools"] = [{"type": "function", "function": f} for f in FUNCTIONS]
            payload["tool_choice"] = "auto"

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()

        if "choices" not in data:
            print(f"[AIClient] GLM invalid response: {data}")
            return {
                "success": False,
                "reply": ERROR_MESSAGE,
                "function_result": {
                    "success": False,
                    "message": f"GLM返回异常: {data}"
                }
            }

        choice = data["choices"][0]
        message = choice.get("message", {})

        # 检查是否有函数调用（仅在非伪装模式下）
        if not stealth:
            tool_calls = message.get("tool_calls", [])
            if tool_calls:
                return self._handle_function_call(tool_calls[0], user_key)

        return {
            "success": True,
            "reply": message.get("content", ""),
            "images": []
        }

    def _handle_function_call(self, tool_call: Dict, user_key: str) -> Dict:
        """处理函数调用"""
        function_name = tool_call.get("function", {}).get("name")
        arguments_str = tool_call.get("function", {}).get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {}

        # 确保 user_key 存在
        arguments["user_key"] = user_key
        if APP_DEBUG:
            print(f"[AIClient] function_call name={function_name} args={arguments}")

        # 执行函数
        result = execute_function(function_name, arguments)
        if APP_DEBUG:
            print(f"[AIClient] function_result success={result.get('success')} message={result.get('message')}")

        # 构建回复
        images = []
        reply = result.get("message", "")

        # 处理验证码图片
        if result.get("need_captcha") and result.get("captcha_image"):
            images.append({
                "type": "captcha",
                "data": result["captcha_image"]
            })

        # 处理二维码图片
        if result.get("qrcode_image"):
            images.append({
                "type": "qrcode",
                "data": result["qrcode_image"]
            })

        return {
            "success": result.get("success", False),
            "reply": reply,
            "images": images,
            "function_result": result
        }


# 全局客户端实例
ai_client = AIClient()
