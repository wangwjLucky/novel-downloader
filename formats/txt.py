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