"""命令行入口：解析参数，调度下载任务。"""
from __future__ import annotations

import argparse

from engine.downloader import Downloader
from sites import SITES


def main(argv: list[str] | None = None) -> None:
    """解析命令行参数并执行下载。"""
    parser = argparse.ArgumentParser(
        description="小说下载工具 — 按章节下载整部小说并输出为 TXT/EPUB",
    )
    parser.add_argument("url", nargs="?", help="小说目录页 URL")
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
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="列出所有支持的站点",
    )

    args = parser.parse_args(argv)

    if args.list_sites:
        print("支持的站点：")
        print(f"  {'站点名称':<16} {'匹配域名':<30} {'获取方式':<12} {'编码':<8}")
        print(f"  {'-'*14}  {'-'*28}  {'-'*10}  {'-'*6}")
        for site in SITES:
            print(f"  {site.name:<16} {site.match_url:<30} {site.list_type:<12} {site.encoding:<8}")
        return

    if not args.url:
        parser.error("缺少 URL 参数")

    downloader = Downloader(args.url, cookie=args.cookie)
    output_path = downloader.run(
        output_format=args.output_format, restart=args.restart
    )
    print(f"\n下载完成: {output_path}")


if __name__ == "__main__":
    main()