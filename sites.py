"""站点规则定义。每个站点配置选择器、API、编码等信息。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SiteConfig:
    """站点解析规则。"""
    name: str
    match_url: str                       # 匹配 URL 的正则
    encoding: str = "utf-8"
    # 章节列表获取方式
    list_type: str = "html"              # "html" 或 "api"
    list_selector: str | None = None     # HTML 模式：CSS 选择器
    list_api_url: str | None = None      # API 模式：URL 模板
    book_id_pattern: str | None = None   # 从 URL 提取 book_id 的正则
    # 章节内容解析
    content_selector: str | None = None
    title_selector: str | None = None
    remove_selectors: list[str] = field(default_factory=list)
    # 章节链接前缀（用于拼接完整 URL）
    link_prefix: str = ""


# 内置站点规则
SITES: list[SiteConfig] = [
    # ── QQ 阅读 ──────────────────────────────────────
    SiteConfig(
        name="QQ阅读",
        match_url=r"book\.qq\.com",
        list_type="api",
        list_api_url="https://book.qq.com/api/book/{book_id}/chapters",
        book_id_pattern=r"book\.qq\.com/[^/]+/([^?]+)",
        content_selector="div.read-content",
        title_selector="h1",
        remove_selectors=["script", "style", ".ad", ".recommend"],
    ),
    # ── 起点中文网 ────────────────────────────────────
    SiteConfig(
        name="起点中文网",
        match_url=r"qidian\.com",
        list_type="html",
        list_selector="ul.catalog-list a",
        content_selector="div.read-content",
        title_selector="h1",
        remove_selectors=["script", "style", ".ad"],
        link_prefix="https://www.qidian.com",
    ),
    # ── 笔趣阁 ────────────────────────────────────────
    SiteConfig(
        name="笔趣阁",
        match_url=r"biquge",
        list_type="html",
        list_selector="dd a",
        content_selector="div#content",
        title_selector="h1",
        remove_selectors=["script", "style"],
        encoding="gbk",
    ),
    # ── 笔趣阁(加密API版) ────────────────────────────
    # bqg691.cc / bqg78.com / biquge78.org 等使用 apibi.cc 加密 API
    SiteConfig(
        name="笔趣阁(加密版)",
        match_url=r"bqg691\.cc|bqg78\.com|biquge78\.org",
        list_type="encrypted_api",
        book_id_pattern=r"book/(\d+)",
        encoding="utf-8",
        # 章节内容从加密 API 获取，不需要 HTML 选择器
        content_selector="",
        title_selector="",
        remove_selectors=[],
    ),
    # ── 番茄小说 ──────────────────────────────────────
    SiteConfig(
        name="番茄小说",
        match_url=r"fanqienovel\.com",
        list_type="api",
        list_api_url="https://api.fanqienovel.com/api/book/{book_id}/chapters",
        book_id_pattern=r"book/(\d+)",
        content_selector="article",
        title_selector="h1",
        remove_selectors=["script", "style"],
    ),
]


def match_site(url: str) -> SiteConfig | None:
    """根据 URL 匹配对应的站点配置。"""
    for site in SITES:
        if re.search(site.match_url, url, re.IGNORECASE):
            return site
    return None


def extract_book_id(url: str, site: SiteConfig) -> str | None:
    """从 URL 中提取 book_id。"""
    if site.book_id_pattern:
        m = re.search(site.book_id_pattern, url)
        if m:
            return m.group(1)
    return None
