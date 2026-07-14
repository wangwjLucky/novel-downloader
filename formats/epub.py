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