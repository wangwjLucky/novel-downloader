# 多站点小说下载工具 — 设计文档

## 概述

通用型小说下载命令行工具。输入小说入口 URL，自动发现所有章节，下载正文内容，输出 TXT 或 EPUB 格式。支持多站点可配置规则、断点续传、并发控制。

## 项目结构

```
novel-downloader/
├── .env                        # 运行时配置
├── config.py                   # pydantic-settings 加载 .env
├── sites.py                    # 站点规则定义（Python 数据类）
├── engine/
│   ├── __init__.py
│   ├── fetcher.py              # 网络请求 + 频率控制/重试
│   ├── parser.py               # 按规则解析 HTML/API
│   ├── downloader.py           # 调度：发现章节 → 下载 → 暂存
│   ├── progress.py             # 断点续传（进度缓存）
│   └── aes_crypto.py           # AES 加密（bqg691 等加密 API 站点）
├── formats/
│   ├── __init__.py
│   ├── txt.py                  # TXT 输出
│   └── epub.py                 # EPUB 输出
├── cli.py                      # 命令行入口
├── main.py                     # 便捷入口
├── requirements.txt
└── CLAUDE.md                   # 项目说明
```

## 架构与数据流

```
输入 URL → 站点识别(sites.py) → 发现章节列表(parser.py / API)
                                  │
                          断点续传检查(progress.py)
                                  │
                          逐个下载(fetcher.py + parser.py / aes_crypto.py)
                                  │
                          更新进度缓存(progress.py)
                                  │
                          输出 TXT/EPUB(formats/)
```

### 章节列表获取方式

支持三种 `list_type` 模式：

| 模式 | 说明 | 适用站点 |
|------|------|----------|
| `html` | 解析 HTML 目录页的 CSS 选择器 | 起点中文网、笔趣阁、anpan.cc |
| `api` | 调用标准 JSON API | QQ 阅读、番茄小说 |
| `encrypted_api` | 调用 AES 加密 API（curl_cffi 模拟浏览器指纹） | bqg691.cc 等 |

## 全局配置 (.env → config.py)

```ini
OUTPUT_FORMAT=txt           # txt / epub
OUTPUT_DIR=./books          # 输出目录
CONCURRENCY=3               # 并发下载数
REQUEST_INTERVAL=1.0        # 请求间隔(秒)
REQUEST_TIMEOUT=30          # 请求超时
RETRY_TIMES=3               # 重试次数
USER_AGENT=Mozilla/5.0 ...  # 默认 UA
```

## 站点规则 (sites.py)

每个站点用 `SiteConfig` 数据类定义规则，集中管理：

| 字段 | 说明 |
|------|------|
| `name` | 站点名称 |
| `match_url` | 用于匹配 URL 的正则 |
| `encoding` | 页面编码 |
| `list_type` | 章节列表方式: `html` / `api` |
| `list_selector` | HTML 模式：CSS 选择器 |
| `list_api_url` | API 模式：API URL 模板 |
| `book_id_pattern` | 从 URL 提取 book_id 的正则 |
| `content_selector` | 正文内容 CSS 选择器 |
| `title_selector` | 章节标题 CSS 选择器（可选） |
| `remove_selectors` | 需移除的广告等内容 |
| `list_url_template` | 从 book_id 自动构造目录页 URL（可选） |
| `hook` | 可选的自定义处理函数名 |
| `encoding` | 页面编码 |

### 站点适配方案

- **QQ 阅读** (`book.qq.com`)：API 模式获取章节列表，HTML 解析正文
- **起点中文网** (`book.qidian.com`)：HTML 模式解析目录页，需处理反爬
- **番茄小说** (`fanqienovel.com`)：API 模式，需处理签名参数
- **笔趣阁类** (`*biquge*`)：HTML 模式，注意 GBK 编码
- **笔趣阁(加密版)** (`bqg691.cc / bqg78.com / biquge78.org`)：AES 加密 API + `curl_cffi` 模拟浏览器指纹
- **anpan.cc**：HTML 模式，`list_url_template` 自动构造目录 URL

## 核心模块职责

### engine/fetcher.py
- 基于 `requests` + `urllib3` 的 Session 封装
- 请求间隔控制（`time.sleep` 按 `REQUEST_INTERVAL`）
- 自动重试（指数退避，最多 `RETRY_TIMES` 次）
- Cookie / Session 保持

### engine/parser.py
- 基于 `BeautifulSoup4` + `lxml`
- `parse_chapter_list(soup, config)` → `list[(index, title, url)]`
- `parse_content(html, config)` → `(title, text)`
- 自动清理广告（remove_selectors）
- 章节标题规范化

### engine/downloader.py
- `discover_chapters(url)` — 识别站点 → 解析章节列表（支持 html/api/encrypted_api 三种模式）
- `download_all(chapters, book_id)` — 遍历下载，跳过已完成的
- `_discover_from_encrypted_api()` — 通过 AES 加密 API 获取章节列表
- `_download_chapter_encrypted()` — 通过加密 API 逐章下载（curl_cffi + 限速重试）
- 完成后调用 formatter 输出

### engine/aes_crypto.py
- AES-128-CBC 加密工具，用于 `list_type=encrypted_api` 站点
- `encrypt_api_request(data)` — 将请求数据加密为 base64 token
- `build_api_url(endpoint, data)` — 构建完整加密 API URL
- 加密密钥从站点 JS 中提取的固定 hash 值

### engine/progress.py
- 进度缓存到 `cache/{book_id}/progress.json`
- 每章下载完成立即更新
- `load_progress(book_id)` / `save_progress(book_id, data)`
- 原始 HTML 缓存到 `cache/{book_id}/raw/{index}.html`

### formats/txt.py
- 每章以 `第X章 标题\n\n正文内容\n\n` 格式写入
- 支持单文件（合并全部章节）或每章独立文件
- UTF-8 编码

### formats/epub.py
- 基于 `ebooklib` 生成标准 EPUB
- 每章一个 XHTML 文件
- 自动生成目录 (NCX + nav.xhtml)
- 封面页（书名 + 作者）

## 断点续传机制

1. 首次运行创建 `progress.json`，记录所有章节信息
2. 每章下载完成后 `done: true`
3. 重新运行时加载进度，跳过已完成的章节
4. 中途中断不丢失已下载内容
5. 支持 `--restart` 参数强制重新下载

## 命令行接口

```bash
novel-downloader <url>                           # 默认 txt 输出
novel-downloader <url> --format epub             # 输出 EPUB
novel-downloader <url> --output ./mybooks        # 指定输出目录
novel-downloader <url> --restart                 # 强制重新下载
novel-downloader --list-sites                    # 列出支持的站点
novel-downloader --version                       # 版本信息
```

## 错误处理

| 场景 | 行为 |
|------|------|
| 网络超时 | 自动重试（指数退避） |
| 章节解析失败 | 跳过该章，记录日志，继续下载 |
| 站点不匹配 | 报错提示支持的站点列表 |
| 服务器 4xx/5xx | 重试 3 次，失败则跳过 |
| 磁盘写入失败 | 终止并报错 |

## 依赖

```
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.1
pydantic-settings>=2.0
ebooklib>=0.18
pycryptodome>=3.20        # AES 加密（加密 API 站点）
curl_cffi>=0.7            # 模拟浏览器指纹（加密 API 站点）
```