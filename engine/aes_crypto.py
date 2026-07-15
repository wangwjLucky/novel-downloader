"""AES 加密工具，用于 bqg691 等站点的加密 API 通信。"""
from __future__ import annotations

import base64
import json
from urllib.parse import quote

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# 从页面 JS 中提取的固定 hash 值
# 由 CryptoJS.MD5(特定字符串).toString() 计算得出
_API_CODE = "394c2c3202da6270a3dc22cf70418a51"
_API_HOST = "apibi.cc"


def encrypt_api_request(data: dict) -> str:
    """将请求数据用 AES-128-CBC 加密，返回 base64 编码的 token。

    Args:
        data: 要加密的请求数据，如 {"id": "557", "chapterid": 1}

    Returns:
        base64 编码的加密字符串
    """
    iv = _API_CODE[:16].encode("utf-8")
    key = _API_CODE[16:32].encode("utf-8")
    plain = json.dumps(data, separators=(",", ":")).encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(plain, AES.block_size))
    return quote(base64.b64encode(encrypted).decode("utf-8"), safe="")


def build_api_url(endpoint: str, data: dict) -> str:
    """构建完整的加密 API URL。"""
    token = encrypt_api_request(data)
    return f"https://{_API_HOST}/api/{endpoint}?token={token}"