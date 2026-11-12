# LinkDigest MCP：小红书 MCP / 抖音 MCP / B站 MCP / 公众号链接读取（MCP 服务器 + API）

[English](README.md) · 简体中文

**一个托管的 MCP 服务器和 REST API：把小红书、抖音、B站、公众号、微博的链接读成 AI Agent 能用的文本**——逐字稿、视频画面里的字（带大致时间）、每张图的描述和图上文字（OCR）、正文、要点和互动数据。小宇宙 / Apple 播客、TikTok、YouTube、X、Instagram 也能读。读取在 [linkdigest.dev](https://linkdigest.dev) 的服务器上完成，**不需要你的平台账号或 Cookie**，本地不用装 ffmpeg、浏览器或语音识别。

30 秒接入（Claude Code、Cursor、Cherry Studio、Trae 等支持远程 MCP 的客户端）：

```json
{
  "mcpServers": {
    "linkdigest": {
      "type": "streamable_http",
      "url": "https://linkdigest.dev/mcp",
      "headers": { "Authorization": "Bearer <LINKDIGEST_API_KEY>" }
    }
  }
}
```

Key 在 [linkdigest.dev/app/keys](https://linkdigest.dev/signin?next=/app/keys) 创建，注册送 10 积分（一次性），不用绑卡。只支持 stdio 的客户端用 `uvx linkdigest-mcp`（见下文）。

**B站视频 → Markdown 笔记**（带时间的大纲、要点、逐字稿；分P 批量）：单文件命令行小工具 [`examples/bilibili`](examples/bilibili/)。

| 平台 | 贴什么链接 | 读出来什么 |
|---|---|---|
| **小红书** | 笔记链接、`xhslink.com` 分享短链 | 正文、话题、互动数据；每张图的描述和图上文字（OCR）；视频笔记的逐字稿；分享页显示的热门评论 |
| **抖音** | `v.douyin.com` 短链、整段分享口令、`douyin.com/video/…` | 带时间的逐字稿、画面里的字（带大致时间）；图文作品每张图的描述和文字 |
| **B站** | `bilibili.com/video/BV…`（`?p=N` 读第 N P）、`b23.tv` | 带时间的逐字稿和画面文字，不依赖 CC 字幕；标题、UP 主、播放 / 点赞等数据 |
| **公众号** | `mp.weixin.qq.com/s/…` | 正文（保留小标题、列表和链接的 Markdown）、公众号名、发布时间、每张配图的描述和文字 |
| **微博** | 微博正文链接 | 正文、转评赞、配图和视频、话题、分享页显示的热评 |

五个 MCP 工具：`digest_url`（读一条链接）、`compare_links`（一批链接出一页对比）、`search_links`（按关键词找小红书 / 抖音 / YouTube / X 的帖子和网页）、`check_balance`、`list_batches`。不下载视频，不提供视频文件；私密、已删除、需要登录才能看的内容读不了，读不出不扣积分。数据怎么来的见 [数据来源与合规](https://linkdigest.dev/zh/shuju-laiyuan)。

这个仓库里有什么：

| | |
|---|---|
| [MCP 配置](#mcp-配置) | Cherry Studio、通义灵码、Trae、Cursor、Claude Code、魔搭 MCP 广场 |
| [`python/`](python/) | Python SDK、命令行 `linkdigest`、stdio MCP 服务器 `linkdigest-mcp`。MIT，**零依赖**，Python 3.10+ |
| [`examples/`](examples/) | Dify 工作流、OpenAPI 导入（扣子等）、飞书多维表格、批量导出 CSV |
| `skills/`、`mcp.json`、`.cursor-plugin/` | Claude Code / Cursor 插件和技能说明 |
| `cordis.patch.yml`、`package.json` | DeepSeek Harness（dsh）插件 |
| [`dify/`](dify/) | Dify 插件源码 |

## 这个仓库里有什么

开源的部分：Python SDK、`linkdigest` 命令行和 `linkdigest-mcp` 本地（stdio）MCP 服务器（[`python/`](python/)，MIT；SDK 里带 LangChain 工具和 LlamaIndex 读取器），
Dify 插件源码（[`dify/`](dify/)），Agent 技能（[`skills/`](skills/)），示例，以及官方 MCP 注册表条目（[`server.json`](server.json)）。
`https://linkdigest.dev/mcp` 和 API 背后的托管服务由 LinkDigest 运营，读取引擎不开源。

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
      "args": ["linkdigest-mcp"],
      "env": {
        "LINKDIGEST_API_KEY": "ld_live_..."
      }
    }
  }
}
```

需要 [uv](https://docs.astral.sh/uv/)。这个包已发布到 PyPI：[`linkdigest-mcp`](https://pypi.org/project/linkdigest-mcp/)，由本仓库的 release 工作流构建上传（trusted publisher，带 attestation）。

## Agent 技能（OpenClaw、Hermes、Claude Code、Cursor 等）

[`skills/`](skills) 里有 25 个现成的 Agent Skill，每个只做一件事：一份 `SKILL.md` 加一个只用 Python 标准库的脚本。读单条链接的技能（下表标 ★）没有 `LINKDIGEST_API_KEY` 也能先看摘要，每个地址每天 2 条；有 Key（注册送 10 积分，不用绑卡）给完整逐字稿和逐图文字。

**视频总结 / 视频转文字 skill**

| 技能 | 做什么 |
| --- | --- |
| `bilibili-video-to-text` | B站视频总结 skill：BV 链接或 b23.tv 短链 → 分段带时间的逐字稿、画面上的字、要点 |
| `bilibili-course-notes` ★ | B站网课笔记 skill：一节课或整套分P 课程 → Markdown 笔记（带时间的大纲、附原话的要点、`[mm:ss]` 逐字稿，每 P 一个文件） |
| `video-to-mindmap` | 视频转思维导图 skill：长视频的带时间大纲 → markmap 能画的 Markdown（分支标起止时间） |
| `douyin-batch-to-text` | 抖音批量视频转文字 skill：一批抖音链接（一个博主的一整套视频）整批读完，每条一个 Markdown 文件 + 索引表；默认只要口播文案 |
| `xiaohongshu-batch-export` | 小红书笔记批量导出 skill：一批笔记导出成 Markdown——正文、每张图上的字（OCR）、视频逐字稿、热评——附索引表 |
| `douyin-video-to-text` ★ | 抖音文案提取 skill：口播逐字稿、画面字幕、章节、要点、点赞评论数 |
| `linkdigest-video-transcript` ★ | 抖音 / 小红书 / TikTok / YouTube / B站视频转文字（口播逐字稿 + 画面文字） |
| `linkdigest-youtube-summary` ★ | YouTube 视频总结和带时间戳的逐字稿，可译成中文 |
| `tiktok-transcript` ★ | TikTok 视频逐字稿、画面字幕、要点（英文说明） |
| `long-video-transcript` ★ | 长视频转文字：讲座、课程、直播回放，最长 2 小时，每 2 分钟 1 积分 |
| `podcast-to-text` | 播客转文字：小宇宙、Apple Podcasts 单集 → 带时间的逐字稿、shownotes、要点 |

**小红书 skill**

| 技能 | 做什么 |
| --- | --- |
| `xiaohongshu-note-to-text` ★ | 小红书笔记转文字：正文、每张图里的字（OCR）、视频笔记的逐字稿、分享页热评 |
| `linkdigest-xhs-note-ocr` ★ | 小红书图文笔记提取，连图片里的字 |
| `xiaohongshu-search-to-text` | 按话题搜小红书笔记，再把挑中的读成文字 |
| `xiaohongshu-consumer-insight` | 小红书消费者洞察：受众、卖点、顾虑、购买意向，每条附核对过的原话 |
| `xiaohongshu-douyin-compare` | 2–10 条小红书 / 抖音链接写成一页对比：共同主题、钩子、空白 |
| `xiaohongshu-daily-draft` | 赛道日报 + 一篇照着能发的稿，发到邮箱；不碰你的账号，不替你发 |
| `linkdigest-xiaohongshu-douyin-reader` ★ | 用英文读小红书 / 抖音（英文说明） |

**抖音 skill**

| 技能 | 做什么 |
| --- | --- |
| `douyin-search-to-text` | 按关键词搜抖音视频，再把挑中的转成文字 |
| `linkdigest-viral-breakdown` ★ | 爆款拆解：钩子、结构节拍、标题公式，引用逐字核对原文 |
| `linkdigest-script-rewrite` ★ | 提取对标视频的口播稿和结构，再仿写自己的脚本 |

**公众号、微博、Instagram 和通用**

| 技能 | 做什么 |
| --- | --- |
| `linkdigest-wechat-article-reader` ★ | 微信公众号文章提取：全文 Markdown + 每张图的文字 |
| `weibo-to-text` ★ | 微博转文字：正文、图上的字、视频逐字稿、前几条热评 |
| `instagram-to-text` | Instagram reel 和帖子转文字（英文说明） |
| `linkdigest` | 通用：任何一条抓不到内容的社交链接或网页 |

**选品和调研**

| 技能 | 做什么 |
| --- | --- |
| `xiaohongshu-pain-point-radar` | 痛点雷达：一个品类在小红书 + 抖音上被抱怨什么、看重什么、搜什么，代码数出每条出现在几篇里（N/M），原话逐字核对，有人搜、没人讲的列成「机会」 |
| `overseas-pain-points` | 出海痛点：同样的事放在 YouTube + TikTok，中文报告，英文原话保留 |

**痛点雷达**（2026-11-07）是一次 REST 调用：`POST https://linkdigest.dev/api/v1/radar`，`{"topic": "扫地机器人", "market": "cn"}`（出海用 `"global"`），再轮询 `GET /api/v1/radar/{id}`；速查 12 篇约 41–47 积分，通常 10–20 分钟。每周更新的公开样例：[国内品类库](https://linkdigest.dev/zh/tongdian-leida) · [出海品类库](https://linkdigest.dev/zh/chuhai-tongdian)。

```bash
# skills CLI 支持的 Agent（Claude Code、Cursor、Codex、OpenClaw、Trae 等）
npx skills add jcaiagent7143-ui/linkdigest-mcp --skill linkdigest-xhs-note-ocr

# Hermes Agent
hermes skills install jcaiagent7143-ui/linkdigest-mcp/skills/linkdigest-xhs-note-ocr
hermes skills install clawhub/linkdigest-xhs-note-ocr   # 或从 ClawHub 安装

# OpenClaw（ClawHub）
clawhub install jackchew7143/linkdigest-xhs-note-ocr
```

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
pip install linkdigest-mcp          # PyPI；或装本仓库：pip install "git+https://github.com/jcaiagent7143-ui/linkdigest-mcp#subdirectory=python"
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

## LangChain

`LinkDigestTool` 是一个 LangChain 工具（`digest_url`）：模型传入链接，拿回这条内容的 Markdown——带时间的逐字稿、画面文字、要点和 Coverage（读到了多少）。通过 ToolCall 调用时，完整 JSON 在 ToolMessage 的 `artifact` 里。积分不够（402）会变成一句带付款链接的话交给模型；长视频没读完会返回 job id，模型下一次调用时取回，不会重复扣费。

```python
# pip install "linkdigest-mcp[langchain]" langchain
from langchain.agents import create_agent
from linkdigest.integrations.langchain import LinkDigestTool

agent = create_agent("anthropic:claude-sonnet-5-5", tools=[LinkDigestTool(max_credits=10)])
agent.invoke({"messages": [{"role": "user", "content": "这条视频卖的是什么？https://v.douyin.com/xxxx/"}]})
```

`LinkDigestTool(output="json")` 改为给模型精简的 JSON。示例：[`examples/python/langchain_agent.py`](examples/python/langchain_agent.py)。

## LlamaIndex

`LinkDigestReader` 把链接变成 LlamaIndex 的 `Document`：正文是 Markdown，metadata 是扁平字段（`platform`、`title`、`author`、`source_url`、`posted_at`、`credits`、`coverage_*`），任何向量库都能直接存。读不了的链接记一条日志后跳过（`errors="raise"` 则直接报错）。

```python
# pip install "linkdigest-mcp[llamaindex]" llama-index
from llama_index.core import VectorStoreIndex
from linkdigest.integrations.llamaindex import LinkDigestReader

docs = LinkDigestReader(depth="script").load_data(["https://v.douyin.com/xxxx/", "https://b23.tv/xxxx"])
VectorStoreIndex.from_documents(docs).as_query_engine().query("这些视频有什么共同点？")
```

`depth="script"` 只读口播，最便宜。示例：[`examples/python/llamaindex_reader.py`](examples/python/llamaindex_reader.py)。

## 链接解析（离线、免费、不要 Key）

`linkdigest.links` 从粘贴的分享文字里找出真正的链接，并说出它指向哪一条帖子：平台、帖子 ID、干净的帖子地址。不要 API Key，不联网。`resolve()` 还会跟随短链接（v.douyin.com、xhslink.com、b23.tv、t.co、vt.tiktok.com……），只读跳转：不读页面内容、不带 cookie、最多 5 跳、User-Agent 如实写明身份。

```python
from linkdigest.links import extract_url, identify, resolve

text = "7.32 复制打开抖音，看看【…的作品】 https://v.douyin.com/G8Oggg_IXMA/ E@u.Ib 复制此链接"
extract_url(text)                     # 'https://v.douyin.com/G8Oggg_IXMA/'
identify("https://m.bilibili.com/video/BV1stVH66E6G?p=2&share_source=copy").canonical_url  # '…/BV1stVH66E6G/?p=2'
resolve(text).post_id                 # '7680883233307342947'（只读了一次跳转）
```

命令行：`linkdigest-links "<分享文字>"` 输出 JSON（`--offline` 不跟随跳转）。支持抖音、小红书（xsec_token 原样保留）、B站、微博（mid 转 bid）、YouTube、TikTok、X、Instagram、快手、公众号文章和播客单集。规则和免费的[链接解析页](https://linkdigest.dev/zh/lianjie-jiexi)一致。`pip install linkdigest-mcp`（0.2.5 及以上）。

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

- **入门包 ¥9.9 = 50 积分**，支持**支付宝**（或刷卡 $1.50），一次性，不订阅，永不过期
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
| B站（哔哩哔哩） | 支持：`bilibili.com/video/BV…`、`b23.tv` 短链；带时间的逐字稿和画面文字，不依赖 CC 字幕 |
| 微博 | 支持：正文、转评赞、画面文字和分享页显示的热评 |
| 公众号文章 | 支持：`mp.weixin.qq.com/s/…` 短链接（长链接 `?__biz=…` 常被微信要求验证） |
| 小宇宙 / Apple 播客 | 支持：单集链接（不是节目主页），带时间的逐字稿 |
| Instagram | 支持：reel 和图片帖子（多图帖读第一张） |
| 普通网页 / 文章 | 支持：正文、标题、作者、日期 |
| **Facebook** | **不支持**：未登录的请求拿不到帖子内容 |

不能下载无水印视频，也不提供视频文件：这个服务只返回文本。

## 速度

实测，不是估算：

- 读过的链接（任何人读过都算）：约 **1 秒**，免费
- 小红书图文笔记：**1–2 分钟**（每张图都要描述和 OCR）
- 带字幕的 YouTube 视频：约 **2.5 分钟**
- 4 分钟的 B站 视频：**69 秒**（2026-11-04 实测）

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
