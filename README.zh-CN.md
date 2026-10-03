# LinkDigest MCP：抖音、小红书链接转文本 · 爆款拆解

[English](README.md) · 简体中文

把抖音、小红书、TikTok、YouTube、X 的链接变成 AI 能读的文本：**逐字稿、视频画面里的字（带大致时间）、每张图的描述和图上文字（OCR）**、正文、要点和互动数据，可选**爆款拆解**和翻译。

服务托管在 [linkdigest.dev](https://linkdigest.dev)，读取在我们的服务器上完成：

- **不需要你的平台账号或 Cookie**
- 本地不用装 ffmpeg、浏览器，也不用自备语音识别（ASR）的 Key
- 一个 API Key 就能用，注册送 10 积分（一次性），不用绑卡

这个仓库里有什么：

| | |
|---|---|
| [MCP 配置](#mcp-配置) | Cherry Studio、通义灵码、Trae、Cursor、Claude Code、魔搭 MCP 广场 |
| [`python/`](python/) | Python SDK、命令行 `linkdigest`、stdio MCP 服务器 `linkdigest-mcp`。MIT，**零依赖**，Python 3.10+ |
| [`examples/`](examples/) | Dify 工作流、OpenAPI 导入（扣子等）、飞书多维表格、批量导出 CSV |
| `skills/`、`mcp.json`、`.cursor-plugin/` | Claude Code / Cursor 插件和技能说明 |
| `cordis.patch.yml`、`package.json` | DeepSeek Harness（dsh）插件 |
| [`dify/`](dify/) | Dify 插件源码 |

## MCP 配置

远程 MCP（Streamable HTTP），什么都不用装：

```json
{
  "mcpServers": {
    "linkdigest": {
      "type": "streamable_http",
      "url": "https://linkdigest.dev/mcp",
      "headers": {
        "Authorization": "Bearer <LINKDIGEST_API_KEY>"
      }
    }
  }
}
```

只支持 stdio 的客户端，用 [mcp-remote](https://github.com/geelen/mcp-remote) 转接（需要 Node.js）：

```json
{
  "mcpServers": {
    "linkdigest": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://linkdigest.dev/mcp", "--header", "Authorization:${AUTH_HEADER}"],
      "env": {
        "AUTH_HEADER": "Bearer <LINKDIGEST_API_KEY>"
      }
    }
  }
}
```

把 `<LINKDIGEST_API_KEY>` 换成你自己的 Key（`ld_live_` 开头），在 **https://linkdigest.dev/app/keys** 创建。
（`Authorization:${AUTH_HEADER}` 是 mcp-remote 文档推荐的写法：Cursor、Codex CLI 和 Windows 上的 Claude Desktop 不会转义 `args` 里的空格。）

不带 Key 也能列出工具（`tools/list`），调用时才需要 Key。

### 各客户端怎么填

**Cherry Studio**：设置 → MCP → MCP 服务器 → 添加 → 从 JSON 导入，粘贴上面第一段。
Cherry Studio 把 `type` 里带 `http` 的识别为 Streamable HTTP（[源码](https://github.com/CherryHQ/cherry-studio/blob/main/src/renderer/types/mcp.ts)）。

**Trae**：MCP → 添加 → 手动添加，粘贴：

```json
{
  "mcpServers": {
    "linkdigest": {
      "url": "https://linkdigest.dev/mcp",
      "headers": { "Authorization": "Bearer ld_live_..." }
    }
  }
}
```

**Cursor**：同一段写进 `~/.cursor/mcp.json`。或者把本仓库当 Cursor 插件安装（`.cursor-plugin/plugin.json` + `mcp.json` + `skills/`），然后在 shell 里设置 `export LINKDIGEST_API_KEY=ld_live_...`，插件的 `mcp.json` 会读这个变量。

**Claude Code**：

```bash
claude mcp add --transport http linkdigest https://linkdigest.dev/mcp \
  --header "Authorization: Bearer ld_live_..."
```

**通义灵码（Qoder CN）**：它的 MCP 文档只给了 SSE 类型的远程示例，Streamable HTTP 加请求头能不能用，我们还没验证过。最稳的是用 stdio：上面的 mcp-remote，或者下面的 `uvx`。

**魔搭 MCP 广场**：已上架 https://modelscope.cn/mcp/servers/JCAI714/linkdigest （托管，可直接部署）。上面两段 JSON 也是魔搭解析的格式（远程 `streamable_http` 和 `npx mcp-remote`）。

### stdio：用 uvx 跑本仓库的 Python 服务器

不想装 Node.js，或者客户端只支持 stdio，用 [`python/`](python/) 里的 `linkdigest-mcp`。它在本地讲 stdio，把调用转发到 `https://linkdigest.dev/mcp`，工具名、参数和说明与远程完全一致：

```json
{
  "mcpServers": {
    "linkdigest": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/jcaiagent7143-ui/linkdigest-mcp#subdirectory=python", "linkdigest-mcp"],
      "env": {
        "LINKDIGEST_API_KEY": "ld_live_..."
      }
    }
  }
}
```

需要 [uv](https://docs.astral.sh/uv/) 和 git。这个包还没有发布到 PyPI，所以从本仓库的 git 地址安装；在本 README 写明之前，PyPI 上叫 `linkdigest-mcp` 的包都不是我们发布的。

## 它读得出什么

| 内容 | 拿到什么 |
|---|---|
| **小红书图文** | 每张图的描述和**图上文字（OCR）**——很多笔记的正文是写在图里的；正文、话题标签、点赞 / 评论 / 收藏 / 分享 |
| **小红书视频笔记** | 逐字稿、画面文字 |
| **抖音视频** | **完整逐字稿**（Qwen3-ASR 转写）；**画面里的字带大致时间**（按关键帧取帧，标 ≈，误差几秒）；互动数据 |
| **抖音图文** | 每张图的描述和图上文字 |
| **爆款拆解**（`breakdown: true`，+1 积分） | 开头钩子（说的话、屏幕上的字都逐字引用）、带时间的结构节拍、标题公式、封面文字、行动号召、目标人群、4–8 步可复用模板、二创方向、这次看不到的信息 |
| TikTok、YouTube、X、普通网页 | 逐字稿 / 字幕、画面文字、图片描述、正文 |

爆款拆解里的引用会和原文**逐字核对**，对不上的直接删掉，并在 `missing` 里写明删了几条；点赞、评论和话题标签来自平台数据，不由模型生成。

几个值得留意的地方：

- `transcript` 是 `[{t, text}]`。平台自带字幕（YouTube 等）按句带时间；语音识别的逐字稿（抖音等）目前按段返回：170 秒以内的视频是一整段（`t` 为 0），更长的每 170 秒左右一段。想知道内容大概出现在第几秒，看 `on_screen`（画面文字，按关键帧标 ≈）和拆解里的节拍。
- `transcript_source`：`native_captions`（平台自带字幕，准确）、`asr`（语音识别）、`gemini_video`（没有字幕的 YouTube 视频由 Gemini 看视频写出逐字稿和时间）或 `none`。拿 ASR 的结果去引用数字或人名时，最好说明来源。
- `degraded`：哪里没读全，用一句话写明；也会记下这次是怎么读完整的（比如 read via oEmbed、read by Gemini watching the video directly），所以不为空不一定是没读全。

### 为什么不能自己抓

分享链接带 token（`xsec_token`、`app_code_link`），内容在视频和图片里，不在 HTML 里，服务器返回的是下载 App 的引导页或登录墙：

```
$ curl -sL 'https://xhslink.com/o/1WiQ1QI6Uc0' | grep -o '<title>.*</title>'
<title>小红书 - 你的生活兴趣社区</title>
```

这个标题来自一个 36 KB 的 App 引导页（2026-10-04 复查）。笔记的正文、图片、图里的字都不在里面。

## 工具：`digest_url`

| 参数 | 说明 |
|---|---|
| `url` | 帖子链接，带上分享 token。整段分享文案也行，服务端会从里面取出链接 |
| `format` | `markdown`（默认，适合直接读）或 `json`（结构化） |
| `breakdown` | `true` 时加爆款拆解，+1 积分 |
| `translate_to` | 语言代码，如 `en`、`ja`、`zh-CN`：在原文旁边加译文（原文保留），拆解也用这个语言写，+1 积分 |
| `partial_ok` | `true` 时，视频超出额度或时长上限就读开头能读的部分，而不是拒绝 |
| `job_id` | 取回还在处理的任务，见下 |

工具说明里写了 `breakdown` 的用途，对 agent 说「拆解这条抖音」时它可能会自己带上 `breakdown: true`；没带的话，在提示里直接说「加上 breakdown」。

### 长视频：分两次调用

一次调用大约 20 秒内返回。20 秒内读不完的内容（长视频、图片很多的图文笔记）不会报错，而是返回一个任务号（job id）；agent 隔 15 秒左右再调一次 `digest_url`，**只传 `job_id`、不传 `url`**，就能取回结果。重新发 `url` 会从头再读一遍。

通过平台代理的 MCP（比如魔搭）可能还有平台自己的超时，长视频更要靠这个两步调用。Python SDK 和命令行会自动等待，不需要你处理（见下）。

## Python SDK 和命令行

在 [`python/`](python/)，零依赖（只用标准库），Python 3.10+。

```bash
pip install "git+https://github.com/jcaiagent7143-ui/linkdigest-mcp#subdirectory=python"
export LINKDIGEST_API_KEY=ld_live_...
```

```python
from linkdigest import LinkDigest, PaymentRequiredError

ld = LinkDigest()  # 读环境变量 LINKDIGEST_API_KEY

d = ld.digest("https://v.douyin.com/xxxx/", breakdown=True)
print(d.title, d.author, f"{d.credits} 积分", "（缓存，免费）" if d.cached else "")
for seg in d.transcript:            # [{t: 秒, text}]
    print(f"[{seg['t']:>6.1f}s] {seg['text']}")
print(d.breakdown["hook"])          # 爆款拆解的开头钩子
print(d.markdown)                   # 整条内容的 Markdown

# 英文译文 + 只读开头（视频超出时长上限时）
d = ld.digest("https://xhslink.com/o/xxxx", translate_to="en", partial_ok=True)

try:
    ld.digest("https://v.douyin.com/yyyy/", max_credits=3)   # 超过 3 积分就不读，也不扣
except PaymentRequiredError as e:
    print(e.error_code, e.buy_url)  # 付款链接，打开就能付，不用登录
```

- 长视频返回 202 时，SDK 用 `GET /api/v1/digest/{jobId}?wait=20` 自动等结果（默认最多 600 秒，`max_wait=` 可调）。等不到会抛 `JobPendingError`，带 `job_id`，之后用 `ld.collect(job_id)` 取回，不用重新读一遍。
- 错误都有类型：`AuthenticationError`（401）、`PaymentRequiredError`（402，带 `buy_url` / `subscribe_url`）、`UnreadableLinkError`（422，删帖 / 私密 / 需要登录）、`RateLimitError`（429，带 `retry_after`）、`InvalidRequestError`（400）、`ServerError`（5xx）、`NetworkError`。
- `ld.check_key()` 校验 Key，不读链接、不扣积分。
- 走 `HTTPS_PROXY` 等代理环境变量。

命令行：

```bash
linkdigest "https://v.douyin.com/xxxx/"                    # Markdown 输出到 stdout
linkdigest "https://xhslink.com/o/xxxx" --breakdown        # 加爆款拆解
linkdigest "<链接>" --translate en --json > post.json      # 完整 JSON
pbpaste | linkdigest -                                     # 直接粘贴整段分享文案
linkdigest --job <job_id>                                  # 取回还在处理的任务
linkdigest --check-key                                     # 校验 Key
```

花了几个积分、是否命中缓存打印在 stderr，stdout 只有内容，方便接管道。退出码：0 成功，1 出错，2 用法错误或没有 Key，3 积分不够（会打印付款链接），4 等待超时（会打印 job id）。

批量处理一列链接并导出 CSV（Excel / WPS 直接打开）：[`examples/python/links_to_csv.py`](examples/python/links_to_csv.py)。

## 价格

按工作量计费，不按链接数（以 [linkdigest.dev/pricing](https://linkdigest.dev/pricing) 为准）：

- 注册送 **10 积分**，一次性，不按月补，不用绑卡
- 一条图文或短帖 **1 积分**；前 6 张图包含在内，之后每多 6 张图 +1
- 视频：每开始的 1 分钟 **+1**（1 分钟的视频共 2 积分）
- 爆款拆解 **+1**，翻译 **+1**
- **任何人读过的链接再读免费**；读不出内容不收费；超过 `max_credits` 或时长上限被拒绝时也不扣

| 例子 | 积分 | 按加量包折算 |
|---|---|---|
| 一篇文章或一条短帖 | 1 | ≈ ¥0.14 |
| 12 张图的小红书笔记 | 2 | ≈ ¥0.29 |
| 3 分钟的抖音视频 | 4 | ≈ ¥0.58 |
| 3 分钟的抖音视频 + 爆款拆解 | 5 | ≈ ¥0.72 |

充值：

- **加量包 ¥36 = 250 积分**，支持**支付宝**（按人民币结算，标价 $5），一次性，不订阅，永不过期。折合约 ¥0.144 / 积分
- **Dev 月付 $9 = 每月 500 积分**，仅支持银行卡

时长上限：未订阅 Dev 的账号单条视频最长 10 分钟，Dev 最长 30 分钟；超出时默认拒绝且不扣积分，带 `partial_ok: true` 则读开头部分。积分用完时，接口返回 402，里面有不用登录就能打开的付款链接。

## 平台支持

逐条用真实链接验证过，不是照文档写的。

| 平台 | 状态 |
|---|---|
| 小红书 | 支持：图文笔记和视频笔记，不需要登录 |
| 抖音 | 支持：视频和图文 |
| TikTok | 支持：短链可直接用；高峰时平台会限流 |
| YouTube | 支持：有字幕用字幕，没有就由模型看视频转写 |
| X | 支持：带视频或图片的帖子；长文（Articles）只能读到首图 |
| 普通网页 / 文章 | 支持：正文、标题、作者、日期 |
| **B站（哔哩哔哩）** | **不支持**：对我们服务器的地址直接返回 HTTP 412，需要代理，目前没有 |
| **Instagram** | **未验证**：代码已接入，没有端到端验证过，不算支持 |
| **Facebook** | **不支持**：未登录的请求拿不到帖子内容 |

不能下载无水印视频，也不提供视频文件：这个服务只返回文本。

## 速度

实测，不是估算：

- 读过的链接（任何人读过都算）：约 **1 秒**，免费
- 小红书图文笔记：**1–2 分钟**（每张图都要描述和 OCR）
- 带字幕的 YouTube 视频：约 **2.5 分钟**

## 隐私

- 视频和图片只在临时目录里处理，**请求返回前删除，不存储、不提供下载**；保存的是文本结果（缓存最长约 30 天，所以同一链接再读免费）。详见 [linkdigest.dev/privacy](https://linkdigest.dev/privacy)。
- 不需要你的抖音、小红书账号或 Cookie，不会用你的账号去请求平台。
- SDK、命令行和 stdio 服务器只连 `linkdigest.dev`（或你用 `LINKDIGEST_BASE_URL` / `LINKDIGEST_MCP_URL` 指定的地址），不打印 Key。

从中国大陆访问：API 和 MCP 都在 `linkdigest.dev` 这一个域名下（CloudFront）。2026-10-03 用 Globalping 的中国大陆探针测试，`/mcp` 15/15 连通，中位约 0.75 秒（[测量结果](https://api.globalping.io/v1/measurements/2lwssBlFwFu2K3gBp00021FVv)）。

## 其他接入方式

- **REST API**：`POST https://linkdigest.dev/api/v1/digest`；批量 `POST /api/v1/digest/batch`（一次最多 50 条，可带签名 webhook）。中文文档：[linkdigest.dev/zh/docs](https://linkdigest.dev/zh/docs)
- **OpenAPI**：[linkdigest.dev/openapi.json](https://linkdigest.dev/openapi.json)，扣子这类平台可以直接导入成插件，见 [`examples/openapi-import/`](examples/openapi-import/)
- **Dify**：插件市场里的 LinkDigest 插件，见 [`examples/dify/`](examples/dify/)
- **飞书多维表格**：字段捷径已提交飞书审核（2026-10-03），还没有上架；在那之前的做法见 [`examples/feishu-bitable/`](examples/feishu-bitable/)

## 开发

```bash
cd python
uv venv && uv pip install -e . pytest      # 或 python -m venv .venv && pip install -e . pytest
pytest                                     # 全部测试；离线：pytest -m "not live"
```

除了一个测试，其他全部用模拟的 HTTP 层，不联网。唯一联网的测试只对 `https://linkdigest.dev/mcp` 调 `tools/list`（不带 Key，不花积分），并检查 `python/src/linkdigest/tool.py` 里的工具定义和线上逐字一致。

问题和建议：[GitHub Issues](https://github.com/jcaiagent7143-ui/linkdigest-mcp/issues)，或写信到 support@linkdigest.dev。

## 许可证

MIT，见 [LICENSE](LICENSE)。更新记录见 [CHANGELOG.md](CHANGELOG.md)。
