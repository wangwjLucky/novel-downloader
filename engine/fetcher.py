"""网络请求模块，封装 requests，支持频率控制、重试、Cookie。"""

from __future__ import annotations

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import settings


class Fetcher:
    """带频率控制和自动重试的 HTTP 请求器。"""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": settings.user_agent})

        # 配置重试策略
        retry = Retry(
            total=settings.retry_times,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        self._last_request_time: float = 0.0
        self._cookies: dict[str, str] = {}

    def set_cookie(self, cookie_str: str) -> None:
        """设置 Cookie 字符串。"""
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                self._cookies[k] = v
        self._session.cookies.update(self._cookies)

    def _rate_limit(self) -> None:
        """请求间隔控制。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < settings.request_interval:
            time.sleep(settings.request_interval - elapsed)

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """发送 GET 请求，自动限速和重试。"""
        self._rate_limit()
        kwargs.setdefault("timeout", settings.request_timeout)
        resp = self._session.get(url, **kwargs)
        resp.encoding = resp.apparent_encoding
        self._last_request_time = time.time()
        return resp

    def get_text(self, url: str, encoding: str | None = None, **kwargs: Any) -> str:
        """发送 GET 请求并返回文本内容。"""
        resp = self.get(url, **kwargs)
        if encoding:
            resp.encoding = encoding
        return resp.text

    def get_json(self, url: str, **kwargs: Any) -> Any:
        """发送 GET 请求并返回 JSON 数据。"""
        resp = self.get(url, **kwargs)
        return resp.json()
