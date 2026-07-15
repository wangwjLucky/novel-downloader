"""HTML/API 内容解析模块，按站点规则提取章节列表和正文。"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from sites import SiteConfig


class ParseError(Exception):
    """解析失败时抛出。"""


def parse_chapter_list(
    html: str, site: SiteConfig, base_url: str = ""
) -> list[tuple[int, str, str]]:
    """从 HTML 目录页解析出章节列表。

    返回: [(序号, 章节标题, 章节URL), ...]
    """
    soup = BeautifulSoup(html, "lxml")
    if not site.list_selector:
        raise ParseError(f"站点 {site.name} 未配置 list_selector")

    links = soup.select(site.list_selector)
    chapters: list[tuple[int, str, str]] = []
    seen = set()

    for i, a_tag in enumerate(links, 1):
        if not isinstance(a_tag, Tag):
            continue
        href = a_tag.get("href", "")
        title = a_tag.get_text(strip=True)
        if not href or not title:
            continue

        # 去重
        if title in seen:
            continue
        seen.add(title)

        # 拼接完整 URL
        if href.startswith("http"):
            full_url = href
        elif site.link_prefix:
            full_url = site.link_prefix.rstrip("/") + "/" + href.lstrip("/")
        else:
            full_url = base_url.rstrip("/") + "/" + href.lstrip("/")

        chapters.append((i, title, full_url))

    if not chapters:
        raise ParseError(f"未解析到任何章节，请检查选择器: {site.list_selector}")

    return chapters


def parse_chapter_content(html: str, site: SiteConfig) -> tuple[str, str]:
    """解析单章正文。

    返回: (章节标题, 正文文本)
    """
    soup = BeautifulSoup(html, "lxml")

    # 提取标题
    title = ""
    if site.title_selector:
        el = soup.select_one(site.title_selector)
        if el:
            title = el.get_text(strip=True)

    # 提取正文
    if site.content_selector:
        el = soup.select_one(site.content_selector)
        if not el:
            raise ParseError(f"未找到正文内容，请检查选择器: {site.content_selector}")
    else:
        el = soup.body
        if not el:
            raise ParseError("页面无 body 元素")

    # 移除广告等干扰元素
    for sel in site.remove_selectors:
        for tag in el.select(sel):
            tag.decompose()

    text = el.get_text("\n", strip=True)
    return title, text


def parse_chapter_content_from_api(
    api_data: dict, site: SiteConfig
) -> tuple[str, str]:
    """从加密 API 的 JSON 响应中解析章节内容。

    返回: (章节标题, 正文文本)
    """
    title = api_data.get("chaptername", "")
    text = api_data.get("txt", "")
    # API 返回的正文用 \n 分隔段落，直接使用
    return title, text


def clean_title(title: str) -> str:
    """清理章节标题中的多余空白。"""
    import re

    title = re.sub(r"\s+", " ", title).strip()
    return title
