# 多站点小说下载工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 构建一个命令行小说下载工具，输入小说入口 URL，自动发现章节并下载为 TXT/EPUB

**Architecture:** 配置驱动 + 分层架构。`sites.py` 定义各站点解析规则，`engine/` 负责网络请求和内容解析，`formats/` 负责输出格式。核心调度在 `downloader.py` 中完成。

**Tech Stack:** Python 3.10+, requests, BeautifulSoup4, lxml, pydantic-settings, ebooklib

---

### Task 1: 项目基础骨架

**Files:**
- Create: `requirements.txt`
- Create: `.env`
- Create: `config.py`
- Create: `sites.py`

- [x] **Step 1: 创建 requirements.txt**

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.1.0
pydantic-settings>=2.0.0
ebooklib>=0.18
```

- [x] **Step 2: 创建 .env**

```ini
OUTPUT_FORMAT=txt
OUTPUT_DIR=./books
CONCURRENCY=3
REQUEST_INTERVAL=1.5
REQUEST_TIMEOUT=30
RETRY_TIMES=3
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

- [x] **Step 3: 创建 config.py**

```python
"""全局配置，从 .env 加载。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    output_format: str = "txt"
    output_dir: str = "./books"
    concurrency: int = 3
    request_interval: float = 1.5
    request_timeout: int = 30
    retry_times: int = 3
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


settings = Settings()
```

- [x] **Step 4: 创建 sites.py**

```python
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
```

- [x] **Step 5: 创建 engine/__init__.py 和 formats/__init__.py**

```python
# engine/__init__.py 和 formats/__init__.py 均为空文件
```

- [x] **Step 6: 提交**

```bash
git add -A && git commit -m "feat: 项目基础骨架（配置、站点规则、依赖）"
```

---

### Task 2: 网络请求模块 (fetcher)

**Files:**
- Create: `engine/fetcher.py`

- [x] **Step 1: 创建 fetcher.py**

```python
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
```

- [x] **Step 2: 提交**

```bash
git add -A && git commit -m "feat: 网络请求模块 fetcher（频率控制、重试、Cookie）"
```

---

### Task 3: 内容解析模块 (parser)

**Files:**
- Create: `engine/parser.py`

- [x] **Step 1: 创建 parser.py**

```python
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


def parse_chapter_content(
    html: str, site: SiteConfig
) -> tuple[str, str]:
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
            raise ParseError(
                f"未找到正文内容，请检查选择器: {site.content_selector}"
            )
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


def clean_title(title: str) -> str:
    """清理章节标题中的多余空白。"""
    import re
    title = re.sub(r"\s+", " ", title).strip()
    return title
```

- [x] **Step 2: 提交**

```bash
git add -A && git commit -m "feat: 内容解析模块 parser（章节列表+正文提取）"
```

---

### Task 4: 断点续传模块 (progress)

**Files:**
- Create: `engine/progress.py`

- [x] **Step 1: 创建 progress.py**

```python
"""断点续传：进度缓存管理。"""
from __future__ import annotations

import json
import os
from pathlib import Path


class ProgressManager:
    """管理下载进度，支持断点续传。"""

    def __init__(self, book_id: str, cache_dir: str = "./cache") -> None:
        self._book_dir = Path(cache_dir) / _sanitize(book_id)
        self._book_dir.mkdir(parents=True, exist_ok=True)
        self._progress_file = self._book_dir / "progress.json"
        self._raw_dir = self._book_dir / "raw"
        self._data: dict = {}

    def load(self) -> list[dict]:
        """加载已有进度，返回章节列表。"""
        if self._progress_file.exists():
            with open(self._progress_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            return self._data.get("chapters", [])
        return []

    def init_chapters(self, chapters: list[tuple[int, str, str]]) -> None:
        """初始化章节列表（仅首次）。"""
        existing = self.load()
        if existing:
            return  # 已有进度，不覆盖

        self._data = {
            "url": "",
            "chapters": [
                {"index": idx, "title": title, "url": url, "done": False}
                for idx, title, url in chapters
            ],
        }
        self._save()

    def mark_done(self, index: int) -> None:
        """标记章节为已完成。"""
        for ch in self._data.get("chapters", []):
            if ch["index"] == index:
                ch["done"] = True
                break
        self._save()

    def is_done(self, index: int) -> bool:
        """检查章节是否已下载完成。"""
        for ch in self._data.get("chapters", []):
            if ch["index"] == index and ch["done"]:
                return True
        return False

    def get_pending(self) -> list[dict]:
        """获取未完成的章节列表。"""
        return [ch for ch in self._data.get("chapters", []) if not ch["done"]]

    def save_raw_html(self, index: int, html: str) -> None:
        """缓存章节原始 HTML。"""
        raw_dir = self._raw_dir
        raw_dir.mkdir(parents=True, exist_ok=True)
        file_path = raw_dir / f"{index:04d}.html"
        file_path.write_text(html, encoding="utf-8")

    def _save(self) -> None:
        with open(self._progress_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @property
    def all_chapters(self) -> list[dict]:
        return self._data.get("chapters", [])


def _sanitize(name: str) -> str:
    """清理字符串，使其适合作为目录名。"""
    import re
    return re.sub(r'[<>:"/\\|?*]', "_", name)
```

- [x] **Step 2: 提交**

```bash
git add -A && git commit -m "feat: 断点续传模块 progress（进度缓存 + 原始HTML缓存）"
```

---

### Task 5: 下载调度核心 (downloader)

**Files:**
- Create: `engine/downloader.py`

- [x] **Step 1: 创建 downloader.py**

```python
"""下载调度核心：协调 fetcher、parser、progress 完成整本下载。"""
from __future__ import annotations

import sys
from pathlib import Path

from config import settings
from engine.fetcher import Fetcher
from engine.parser import (
    ParseError,
    parse_chapter_content,
    parse_chapter_list,
    clean_title,
)
from engine.progress import ProgressManager
from formats.txt import export_txt
from formats.epub import export_epub
from sites import match_site, extract_book_id


class Downloader:
    """小说下载调度器。"""

    def __init__(self, url: str, cookie: str = "") -> None:
        self._url = url
        self._fetcher = Fetcher()
        if cookie:
            self._fetcher.set_cookie(cookie)

        # 匹配站点
        site = match_site(url)
        if not site:
            raise ValueError(
                f"不支持的站点: {url}\n"
                f"支持的站点: {[s.name for s in __import__('sites').SITES]}"
            )
        self._site = site

        # 提取 book_id
        book_id = extract_book_id(url, site) or "default"
        self._book_id = book_id
        self._progress = ProgressManager(book_id)

        print(f"📖 站点: {site.name}")
        print(f"📄 Book ID: {book_id}")

    def run(self, output_format: str = "", restart: bool = False) -> str:
        """执行完整下载流程。

        Args:
            output_format: 输出格式，txt/epub，默认使用 settings.output_format
            restart: 是否强制重新下载

        Returns:
            输出文件路径
        """
        # 1. 发现章节
        chapters = self._discover_chapters()

        # 2. 初始化进度
        if restart:
            # 删除旧进度
            import shutil
            shutil.rmtree(self._progress._book_dir, ignore_errors=True)
            self._progress = ProgressManager(self._book_id)
        self._progress.init_chapters(chapters)

        # 3. 下载未完成的章节
        pending = self._progress.get_pending()
        if not pending:
            print("所有章节已下载完成，直接输出。")
        else:
            total = len(pending)
            print(f"\n共 {len(chapters)} 章，待下载 {total} 章")
            for i, ch in enumerate(pending, 1):
                self._download_chapter(ch["index"], ch["title"], ch["url"])
                print(f"  [{i}/{total}] 第{ch['index']}章 - {ch['title']}")

        # 4. 输出文件
        fmt = output_format or settings.output_format
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        all_chapters = self._progress.all_chapters

        # 收集所有章节内容
        contents: list[tuple[str, str]] = []  # [(标题, 正文), ...]
        for ch in all_chapters:
            if not ch["done"]:
                continue
            raw_file = self._progress._raw_dir / f"{ch['index']:04d}.html"
            if raw_file.exists():
                html = raw_file.read_text(encoding="utf-8")
                try:
                    title, text = parse_chapter_content(html, self._site)
                    title = title or ch["title"]
                    contents.append((title, text))
                except ParseError:
                    contents.append((ch["title"], "【内容解析失败】"))
            else:
                contents.append((ch["title"], "【原始内容未找到】"))

        if fmt == "epub":
            output_path = output_dir / f"{self._book_id}.epub"
            export_epub(contents, str(output_path), self._book_id)
        else:
            output_path = output_dir / f"{self._book_id}.txt"
            export_txt(contents, str(output_path))

        print(f"\n✅ 输出文件: {output_path}")
        return str(output_path)

    def _discover_chapters(self) -> list[tuple[int, str, str]]:
        """发现全部章节列表。"""
        site = self._site

        if site.list_type == "api":
            return self._discover_from_api()
        else:
            return self._discover_from_html()

    def _discover_from_api(self) -> list[tuple[int, str, str]]:
        """通过 API 获取章节列表。"""
        site = self._site
        api_url = site.list_api_url
        if not api_url:
            raise ParseError(f"站点 {site.name} 未配置 API URL")

        url = api_url.format(book_id=self._book_id)
        print(f"请求API: {url}")
        data = self._fetcher.get_json(url)

        # 尝试常见 JSON 结构
        chapters_data = (
            data.get("data", {}).get("chapters")
            or data.get("data", {}).get("list")
            or data.get("chapters")
            or data.get("list")
            or data
        )

        if isinstance(chapters_data, list):
            result: list[tuple[int, str, str]] = []
            for i, ch in enumerate(chapters_data, 1):
                if isinstance(ch, dict):
                    title = ch.get("title", ch.get("name", f"第{i}章"))
                    ch_url = ch.get("url", ch.get("link", ""))
                    if ch_url and not ch_url.startswith("http"):
                        ch_url = f"https://book.qq.com{ch_url}"
                    result.append((i, title, ch_url))
                elif isinstance(ch, str):
                    result.append((i, ch, ""))
            return result

        raise ParseError("无法解析API返回的章节列表")

    def _discover_from_html(self) -> list[tuple[int, str, str]]:
        """从 HTML 目录页解析章节列表。"""
        html = self._fetcher.get_text(self._url, encoding=self._site.encoding)
        return parse_chapter_list(html, self._site, self._url)

    def _download_chapter(self, index: int, title: str, url: str) -> None:
        """下载单个章节。"""
        if self._progress.is_done(index):
            return

        try:
            html = self._fetcher.get_text(url, encoding=self._site.encoding)
            self._progress.save_raw_html(index, html)
            self._progress.mark_done(index)
        except Exception as e:
            print(f"  ⚠️  第{index}章下载失败: {e}", file=sys.stderr)
```

- [x] **Step 2: 提交**

```bash
git add -A && git commit -m "feat: 下载调度核心 downloader"
```

---

### Task 6: TXT 输出模块

**Files:**
- Create: `formats/txt.py`

- [x] **Step 1: 创建 txt.py**

```python
"""TXT 格式输出，合并所有章节为一个文本文件。"""
from __future__ import annotations


def export_txt(contents: list[tuple[str, str]], output_path: str) -> None:
    """将章节内容输出为 TXT 文件。

    Args:
        contents: [(标题, 正文), ...]
        output_path: 输出文件路径
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for title, text in contents:
            f.write(f"\n{'='*60}\n")
            f.write(f"{title}\n")
            f.write(f"{'='*60}\n\n")
            f.write(text)
            f.write("\n\n")
```

- [x] **Step 2: 提交**

```bash
git add -A && git commit -m "feat: TXT 输出模块"
```

---

### Task 7: EPUB 输出模块

**Files:**
- Create: `formats/epub.py`

- [x] **Step 1: 安装依赖**

```bash
pip install ebooklib
```

- [x] **Step 2: 创建 epub.py**

```python
"""EPUB 格式输出，使用 ebooklib 生成标准 EPUB 文件。"""
from __future__ import annotations

from ebooklib import epub


def export_epub(
    contents: list[tuple[str, str]],
    output_path: str,
    book_title: str = "小说",
    book_author: str = "未知",
) -> None:
    """将章节内容输出为 EPUB 文件。

    Args:
        contents: [(标题, 正文), ...]
        output_path: 输出文件路径
        book_title: 书名
        book_author: 作者
    """
    book = epub.EpubBook()
    book.set_identifier("id_" + book_title)
    book.set_title(book_title)
    book.set_language("zh-CN")
    book.add_author(book_author)

    chapters = []
    for i, (title, text) in enumerate(contents):
        # 创建章节
        chap = epub.EpubHtml(
            title=title,
            file_name=f"chap_{i+1:04d}.xhtml",
            lang="zh-CN",
        )
        # 将文本转为 HTML 段落
        paragraphs = text.split("\n")
        html_body = "".join(f"<p>{p}</p>" for p in paragraphs if p.strip())
        chap.content = f"<h1>{title}</h1>\n{html_body}"
        book.add_item(chap)
        chapters.append(chap)

    # 生成目录
    book.toc = chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 设置封面
    style = "body { font-family: SimSun, serif; }"
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style.encode("utf-8"),
    )
    book.add_item(nav_css)

    # 生成 spine
    book.spine = ["nav"] + chapters

    # 写入文件
    epub.write_epub(output_path, book, {})
```

- [x] **Step 3: 提交**

```bash
git add -A && git commit -m "feat: EPUB 输出模块"
```

---

### Task 8: 命令行入口 (cli.py)

**Files:**
- Create: `cli.py`

- [x] **Step 1: 创建 cli.py**

```python
"""命令行入口。"""
from __future__ import annotations

import argparse
import sys

from engine.downloader import Downloader
from sites import SITES


def main() -> None:
    parser = argparse.ArgumentParser(
        description="多站点小说下载工具 - 根据 URL 下载整部小说"
    )
    parser.add_argument("url", nargs="?", help="小说入口 URL")
    parser.add_argument("--format", "-f", choices=["txt", "epub"], help="输出格式")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--cookie", help="浏览器 Cookie 字符串（用于已购章节）")
    parser.add_argument("--restart", action="store_true", help="强制重新下载")
    parser.add_argument(
        "--list-sites", action="store_true", help="列出支持的站点"
    )

    args = parser.parse_args()

    if args.list_sites:
        print("支持的站点:")
        for site in SITES:
            print(f"  - {site.name} ({site.match_url})")
        return

    if not args.url:
        parser.print_help()
        sys.exit(1)

    try:
        dl = Downloader(args.url, cookie=args.cookie or "")
        output_path = dl.run(
            output_format=args.format or "",
            restart=args.restart,
        )
        print(f"\n下载完成: {output_path}")
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [x] **Step 2: 创建 main.py（可选入口）**

```python
"""便捷入口：python main.py"""
from cli import main

if __name__ == "__main__":
    main()
```

- [x] **Step 3: 提交**

```bash
git add -A && git commit -m "feat: 命令行入口 CLI"
```

---

### Task 9: 集成测试与验证

**Files:**
- Create: `.gitignore`

- [x] **Step 1: 创建 .gitignore**

```
__pycache__/
*.pyc
.env
cache/
books/
*.egg-info/
dist/
build/
```

- [x] **Step 2: 安装依赖并验证**

```bash
cd D:/pyWorkspace/novel-downloader
pip install -r requirements.txt
```

- [x] **Step 3: 测试运行（使用帮助）**

```bash
python cli.py --list-sites
python cli.py --help
```

- [x] **Step 4: 初始化 git 并提交**

```bash
git init
git add -A
git commit -m "feat: 多站点小说下载工具初始版本"
```

---

### Task 10: AES 加密模块（加密 API 站点支持）

**Files:**
- Create: `engine/aes_crypto.py`
- Modify: `engine/parser.py`（新增 `parse_chapter_content_from_api`）
- Modify: `engine/downloader.py`（新增 `_discover_from_encrypted_api` / `_download_chapter_encrypted`）
- Modify: `sites.py`（新增 `list_type="encrypted_api"` 和 `list_url_template` 字段）
- Modify: `requirements.txt`（新增 `pycryptodome`, `curl_cffi`）

- [x] **Step 1: 创建 aes_crypto.py** — AES-128-CBC 加密工具，用于 bqg691 等加密 API 站点
- [x] **Step 2: 扩展 parser.py** — 新增 `parse_chapter_content_from_api()` 解析加密 API JSON 响应
- [x] **Step 3: 扩展 downloader.py** — 新增 `_discover_from_encrypted_api()` 和 `_download_chapter_encrypted()` 方法，使用 `curl_cffi` 模拟浏览器指纹
- [x] **Step 4: 更新 sites.py** — SiteConfig 新增 `list_url_template` 字段；新增 `list_type="encrypted_api"` 支持；新增"笔趣阁(加密版)"站点配置（bqg691.cc 等）
- [x] **Step 5: 提交**

```bash
git add -A && git commit -m "feat: 支持加密 API 站点（bqg691.cc 等）"
```

### Task 11: anpan.cc 站点支持

**Files:**
- Modify: `sites.py`

- [x] **Step 1: 更新 sites.py** — 新增 anpan.cc 站点配置，HTML 模式 + `list_url_template` 自动构造目录 URL
- [x] **Step 2: 提交**

```bash
git add -A && git commit -m "feat: 支持 anpan.cc 站点并添加 list_url_template 自动构造目录 URL"
```

### Task 12: CLI 增强与文档完善

**Files:**
- Modify: `cli.py`
- Create: `CLAUDE.md`
- Modify: `README.md`

- [x] **Step 1: 改进 cli.py** — `--list-sites` 表格化输出站点信息；支持 `main(argv)` 参数注入便于测试
- [x] **Step 2: 创建 CLAUDE.md** — 项目说明文档
- [x] **Step 3: 更新 README.md** — 完善使用说明、站点配置指南、CLI 参数详解
- [x] **Step 4: 更新加密 API 主机地址** — 修正为 www.bqg691.cc
- [x] **Step 5: 提交**

```bash
git add -A && git commit -m "docs: 完善 README / feat: 改进 CLI --list-sites"
```