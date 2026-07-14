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
)
from engine.progress import ProgressManager
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

        print(f"站点: {site.name}")
        print(f"Book ID: {book_id}")

    def run(self, output_format: str = "", restart: bool = False) -> str:
        """执行完整下载流程。

        Args:
            output_format: 输出格式，txt/epub，默认使用 settings.output_format
            restart: 是否强制重新下载

        Returns:
            输出文件路径
        """
        # 延迟导入格式模块（对应 formats/ 包可能在后续任务中创建）
        from formats.txt import export_txt
        from formats.epub import export_epub

        # 1. 发现章节
        chapters = self._discover_chapters()

        # 2. 初始化进度
        if restart:
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

        print(f"\n输出文件: {output_path}")
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
            print(f"  第{index}章下载失败: {e}", file=sys.stderr)