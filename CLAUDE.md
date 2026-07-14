# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

多站点小说下载命令行工具。输入小说 URL，自动发现章节、下载正文，输出 TXT/EPUB 格式。支持断点续传、多站点可配置规则。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python cli.py <小说目录页URL>
python cli.py <URL> -f epub          # 输出 EPUB
python cli.py <URL> --restart        # 强制重新下载
python cli.py <URL> -c "cookie值"    # 传入 Cookie
python cli.py --list-sites           # 列出支持的站点
python main.py <URL>                 # 等价入口
```

## 项目结构

```
├── cli.py              # 命令行入口（argparse 解析参数）
├── main.py             # 便捷入口（python main.py）
├── config.py           # 全局配置，从 .env 加载（pydantic-settings）
├── sites.py            # 站点规则定义（SiteConfig 数据类）
├── engine/
│   ├── fetcher.py      # 网络请求（requests + 频率控制 + 重试 + Cookie）
│   ├── parser.py       # 内容解析（BeautifulSoup，按站点规则提取）
│   ├── downloader.py   # 调度核心：发现章节 → 下载 → 调用格式输出
│   └── progress.py     # 断点续传（progress.json + 原始 HTML 缓存）
├── formats/
│   ├── txt.py          # TXT 格式输出
│   └── epub.py         # EPUB 格式输出（ebooklib）
├── .env                # 运行时配置
└── requirements.txt
```

## 架构要点

- **配置驱动**：每个站点用 `sites.py` 中的 `SiteConfig` 数据类定义匹配规则、选择器、API 模板等，新增站点只需添加配置
- **数据流**：`URL → 站点识别 → 发现章节列表 → 断点续传检查 → 逐个下载 → 输出 TXT/EPUB`
- **断点续传**：进度缓存在 `cache/{book_id}/progress.json`，原始 HTML 缓存在 `cache/{book_id}/raw/`
- **站点适配**：支持 HTML 解析（CSS 选择器）和 API 两种章节列表获取方式；内置 QQ 阅读、起点中文网、笔趣阁、番茄小说规则