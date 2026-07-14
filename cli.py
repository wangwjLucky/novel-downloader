"""命令行入口：解析参数，调度下载任务。"""
from __future__ import annotations

import argparse

from engine.downloader import Downloader


def main(argv: list[str] | None = None) -> None:
    """解析命令行参数并执行下载。"""
    parser = argparse.ArgumentParser(
        description="小说下载工具 — 按章节下载整部小说并输出为 TXT/EPUB",
    )
    parser.add_argument("url", help="小说目录页 URL")
    parser.add_argument(
        "-c", "--cookie", default="", help="Cookie（用于访问付费/需登录章节）"
    )
    parser.add_argument(
        "-f",
        "--output-format",
        default="",
        choices=["", "txt", "epub"],
        help="输出格式（默认使用 .env 中的配置）",
    )
    parser.add_argument(
        "-r",
        "--restart",
        action="store_true",
        help="强制重新下载（清除已有缓存）",
    )

    args = parser.parse_args(argv)

    downloader = Downloader(args.url, cookie=args.cookie)
    output_path = downloader.run(
        output_format=args.output_format, restart=args.restart
    )
    print(f"\n下载完成: {output_path}")


if __name__ == "__main__":
    main()