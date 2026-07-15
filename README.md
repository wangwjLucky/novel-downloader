# 小说下载工具

多站点小说下载命令行工具。输入小说 URL，自动匹配站点、发现章节、下载正文，输出 TXT/EPUB 格式。支持断点续传、多站点可配置规则、加密 API 站点。

## 安装

```bash
# 安装依赖
pip install -r requirements.txt
```

### 依赖说明

| 依赖 | 用途 | 必装 |
|------|------|------|
| `requests` | 常规 HTTP 请求 | 是 |
| `beautifulsoup4` + `lxml` | HTML 内容解析 | 是 |
| `pydantic-settings` | 从 `.env` 加载配置 | 是 |
| `ebooklib` | EPUB 格式输出 | 否（不用 EPUB 可跳过） |
| `pycryptodome` | AES 解密（加密版站点用） | 否 |
| `curl-cffi` | 模拟浏览器 TLS 指纹（加密版站点用） | 否 |

## 快速开始

```bash
# 查看帮助
python cli.py --help

# 下载小说（默认 TXT 格式）
python cli.py "https://www.anpan.cc/mm/6381/"

# 指定输出 EPUB 格式
python cli.py "https://www.anpan.cc/mm/6381/" -f epub

# 传入 Cookie（访问付费章节）
python cli.py "https://book.qq.com/book/xxx/" -c "your_cookie_here"

# 强制重新下载（清除缓存）
python cli.py "https://www.anpan.cc/mm/6381/" --restart

# 也可用 main.py 等价入口
python main.py "https://www.anpan.cc/mm/6381/"
```

## CLI 参数详解

```bash
python cli.py [-h] [-c COOKIE] [-f {txt,epub}] [-r] url
```

| 参数 | 简写 | 说明 | 默认 |
|------|------|------|------|
| `url` | （位置参数） | **小说目录页 URL**（部分站点支持直接粘贴章节 URL） | 必填 |
| `--output-format` | `-f` | 输出格式：`txt` 或 `epub` | `.env` 中 `OUTPUT_FORMAT` |
| `--cookie` | `-c` | HTTP Cookie，用于访问付费/需登录章节 | 空 |
| `--restart` | `-r` | 清除已有缓存，强制重新下载全部章节 | 未设置 |

### 使用示例

**基本下载：**
```bash
python cli.py "https://www.anpan.cc/mm/6381/"
```

**支持传入章节 URL：**
若站点配置了 `book_id_pattern` 和 `list_url_template`，可直接粘贴任意章节 URL，工具会自动定位到目录页：
```bash
# 自动识别 book_id 并构造目录 URL
python cli.py "https://www.anpan.cc/mm/6381/4428585.html"
```

**批量使用（脚本中调用）：**
```python
from engine.downloader import Downloader

dl = Downloader("https://www.anpan.cc/mm/6381/")
output_path = dl.run(output_format="txt")
print(f"输出文件: {output_path}")
```

## 支持站点

| 站点 | 匹配域名 | 获取方式 | 编码 | 说明 |
|------|----------|----------|------|------|
| QQ阅读 | `book.qq.com` | API | UTF-8 | REST API 获取章节 |
| 起点中文网 | `qidian.com` | HTML 解析 | UTF-8 | 解析目录页 `ul.catalog-list` |
| 笔趣阁 | `biquge` | HTML 解析 | GBK | 通用 biquge 系列站点 |
| 笔趣阁(加密版) | `bqg691.cc` / `bqg78.com` / `biquge78.org` | 加密 API | UTF-8 | AES-128-CBC 加密，需 `curl-cffi` |
| anpan.cc | `anpan.cc` | HTML 解析 | UTF-8 | 笔趣阁风格，`table#at` 列表 |
| 番茄小说 | `fanqienovel.com` | API | UTF-8 | REST API 获取章节 |

## 站点配置指南（sites.py）

新增站点只需在 `sites.py` 的 `SITES` 列表中添加 `SiteConfig` 数据类即可，无需改动其他代码。

### SiteConfig 字段说明

```python
@dataclass
class SiteConfig:
    name: str                # 站点显示名称
    match_url: str           # 匹配 URL 的正则表达式
    encoding: str = "utf-8"  # 页面编码（gbk / utf-8）

    # 章节列表获取方式
    list_type: str = "html"              # "html" / "api" / "encrypted_api"
    list_selector: str | None = None     # HTML 模式：CSS 选择器
    list_api_url: str | None = None      # API 模式：URL 模板（{book_id} 占位）
    book_id_pattern: str | None = None   # 从 URL 提取 book_id 的正则
    list_url_template: str | None = None # 从 book_id 构造目录 URL 的模板

    # 正文解析
    content_selector: str | None = None  # 正文内容 CSS 选择器
    title_selector: str | None = None    # 章节标题 CSS 选择器
    remove_selectors: list[str] = []     # 需要移除的广告/干扰元素选择器
    link_prefix: str = ""                # 章节链接前缀（相对 URL 拼接用）
```

### 三种数据获取方式

#### 1. HTML 解析（list_type="html"）

从目录页 HTML 中提取章节链接列表，适用于传统小说网：

```python
SiteConfig(
    name="示例站点",
    match_url=r"example\.com",
    list_type="html",
    list_selector="div.chapter-list a",     # 选中所有章节链接
    content_selector="div#content",          # 正文容器
    title_selector="h1",                     # 章节标题
    remove_selectors=["script", "style", ".ad"],  # 移除干扰元素
    encoding="utf-8",
    link_prefix="https://www.example.com",   # 相对链接拼成绝对 URL
    book_id_pattern=r"book/(\d+)",           # 从 URL 提取 book_id
    list_url_template="https://www.example.com/book/{book_id}/",  # 自动构造目录 URL
)
```

- `list_selector` 使用 CSS 选择器选中所有章节 `<a>` 标签
- `link_prefix` 用于将相对路径拼为完整 URL
- `book_id_pattern` + `list_url_template` 可选，支持从章节 URL 自动定位目录页

#### 2. REST API（list_type="api"）

通过 HTTP API 获取章节列表和内容：

```python
SiteConfig(
    name="API站点",
    match_url=r"api-example\.com",
    list_type="api",
    list_api_url="https://api.example.com/book/{book_id}/chapters",  # {book_id} 自动替换
    book_id_pattern=r"book/(\d+)",
    content_selector="article",    # 正文 CSS 选择器（API 返回 HTML 时用）
    title_selector="h1",
)
```

- API 需返回 JSON，工具自动尝试常见字段路径（`data.chapters`、`data.list`、`chapters`、`list`）
- 每个章节对象支持 `title`/`name` 和 `url`/`link` 字段

#### 3. 加密 API（list_type="encrypted_api"）

适用于使用 AES 加密通信的站点：

```python
SiteConfig(
    name="加密版站点",
    match_url=r"encrypted-site\.com",
    list_type="encrypted_api",
    book_id_pattern=r"book/(\d+)",
    encoding="utf-8",
    content_selector="",  # 内容由 API 返回，不需要选择器
    title_selector="",
    remove_selectors=[],
)
```

- 需要 `pycryptodome` 和 `curl-cffi` 库
- 加密逻辑在 `engine/aes_crypto.py` 中实现
- 使用 `curl_cffi` 模拟 Chrome 120 TLS 指纹绕过反爬

### 新增站点示例

以新增一个标准 biquge 风格站点为例：

```python
SiteConfig(
    name="我的站点",
    match_url=r"mysite\.com",
    list_type="html",
    list_selector="div.list a",
    content_selector="div#bookcontent",
    title_selector="h1",
    remove_selectors=["script", "style"],
    encoding="gbk",
    link_prefix="https://www.mysite.com",
)
```

## 配置（.env）

项目根目录的 `.env` 文件控制运行参数：

```bash
# 输出格式：txt 或 epub
OUTPUT_FORMAT=txt

# 输出目录
OUTPUT_DIR=./books

# 并发下载数（预留，暂未启用）
CONCURRENCY=3

# 请求间隔（秒），避免触发反爬
REQUEST_INTERVAL=1.5

# HTTP 请求超时（秒）
REQUEST_TIMEOUT=30

# 失败重试次数
RETRY_TIMES=3

# 请求 User-Agent
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

**优先级：** CLI 参数 `-f` > `.env` 配置 > 代码默认值。

## 输出文件

默认输出到 `./books/`，文件名格式 `{book_id}.txt` 或 `{book_id}.epub`：

```
books/
├── 6381.txt          # TXT 格式
└── 6381.epub         # EPUB 格式
```

## 缓存与断点续传

下载进度自动缓存，中断后重新运行同一 URL 会自动跳过已完成的章节：

```
cache/
└── {book_id}/
    ├── progress.json        # 下载进度（每章完成状态）
    └── raw/                 # 原始 HTML 缓存
        ├── 0001.html
        ├── 0002.html
        └── ...
```

- **断点续传：** 默认启用，自动检查 `progress.json`，跳过 `done=true` 的章节
- **重新下载：** 加 `--restart` 参数清除整个缓存目录，从零开始

## 项目结构

```
├── cli.py              # 命令行入口（argparse 参数解析）
├── main.py             # 便捷入口（python main.py <URL>）
├── config.py           # 全局配置（pydantic-settings 加载 .env）
├── sites.py            # 站点规则定义（SiteConfig 数据类）
├── .env                # 运行时配置
├── requirements.txt    # Python 依赖
├── engine/
│   ├── fetcher.py      # 网络请求（requests + 频率控制 + 重试 + Cookie）
│   ├── parser.py       # 内容解析（BeautifulSoup，按站点规则提取）
│   ├── downloader.py   # 调度核心：发现章节 → 下载 → 输出
│   ├── progress.py     # 断点续传（progress.json + 原始 HTML 缓存）
│   └── aes_crypto.py   # AES 加密通信（加密版站点使用）
├── formats/
│   ├── txt.py          # TXT 格式输出
│   └── epub.py         # EPUB 格式输出（ebooklib）
├── books/              # 输出文件目录
└── cache/              # 缓存文件目录
```

### 数据流

```
小说 URL → match_site() 匹配站点 → 发现章节列表
    → 检查断点续传进度 → 逐个下载未完成章节
    → 全部完成后调用格式模块输出
```

## 常见问题

### 下载中断后如何继续？

重新执行相同的命令即可。工具会读取 `cache/{book_id}/progress.json`，自动跳过已下载的章节。

### 如何完全重新下载？

```bash
python cli.py <URL> --restart
```

### Cookie 如何获取？

浏览器打开目标小说页面 → F12 开发者工具 → Network 标签 → 点击任意请求 → 复制 `Cookie` 请求头的值。

### 笔趣阁加密版下载失败？

确保安装了 `curl-cffi` 和 `pycryptodome`。该站点需要模拟浏览器 TLS 指纹（Chrome 120）并加密通信。如果遇到 403 错误，工具会自动重试（间隔递增）。

### EPUB 输出乱码？

EPUB 格式使用 XHTML 标准。`ebooklib` 库要求内容为有效的 XHTML，正文中的特殊字符（`&`、`<`、`>` 等）会自动转义。如果仍然乱码，检查站点编码配置是否正确（`gbk` vs `utf-8`）。

### 章节解析为空？

站点改版可能导致 CSS 选择器失效。检查 `sites.py` 中对应站点的 `content_selector` 和 `list_selector`，使用浏览器开发者工具验证当前页面的 DOM 结构。

### 提示"不支持的站点"？

当前支持的所有站点列在本 README 的「支持站点」表中。如需添加新站点，参见「站点配置指南」在 `sites.py` 中添加配置。

### requests 和 curl_cffi 有什么区别？

- `requests`：常规 HTTP 库，用于普通站点的页面抓取
- `curl_cffi`：可模拟浏览器 TLS 指纹，仅加密 API 版笔趣阁需要