"""断点续传：进度缓存管理。"""

from __future__ import annotations

import json
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
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._raw_dir / f"{index:04d}.html"
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
