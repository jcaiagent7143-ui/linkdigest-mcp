---
name: video-to-notes
description: "视频转笔记 / 学习笔记 (Video to study notes). 用户发来知识类视频链接（抖音、B站、小红书视频、YouTube、TikTok），想把它整理成能存、能搜的学习笔记时使用：一句话主题、要点（每条附口播原话和时间）、视频里出现的数字和专业名词清单（方便核对）、能照着做的步骤。也适合把一位博主或老师的很多条视频逐条做成笔记再汇总成目录。读的是视频里说的话和画面上的字，不是凭标题写。没有 Key 可免费看一条摘要；完整笔记需要 LinkDigest API Key（注册送 10 积分）。不登录平台、不要 Cookie、不下载视频；读不了不扣费。"
version: 1.0.0
homepage: https://linkdigest.dev/zh/bozhu-xilie-shipin-zhuanwenzi?ref=skill-video-to-notes
metadata: {"openclaw":{"requires":{"anyBins":["python3"]},"primaryEnv":"LINKDIGEST_API_KEY","envVars":[{"name":"LINKDIGEST_API_KEY","required":false,"description":"可选。LinkDigest API Key（ld_live_ 开头），在 https://linkdigest.dev/signin?ref=skill-video-to-notes&next=/app/keys 创建，注册送 10 积分；不设也能免费看一条摘要"}],"homepage":"https://linkdigest.dev/zh/bozhu-xilie-shipin-zhuanwenzi?ref=skill-video-to-notes"}}
required_environment_variables:
  - name: LINKDIGEST_API_KEY
    prompt: "LinkDigest API key (starts with ld_live_); optional"
    help: "https://linkdigest.dev/signin?ref=skill-video-to-notes&next=/app/keys"
    required_for: "notes with quotes and times; without it the script shows a free summary, up to 2 a day per address"
---
# 视频转笔记 · 学习笔记 (video → study notes)

知识类短视频（财税、法律、编程、理财、自媒体课……）信息都在口播里，看一遍记不住，收藏了也搜不到。这个 skill 把视频链接读成一份可以存进笔记软件、以后能搜到的 Markdown 笔记，每条要点都带原话和时间。

支持：抖音、B站、小红书视频笔记、YouTube、TikTok 的视频链接，或 App 里「复制链接」得到的整段分享文字。

## 怎么跑

```bash
export LINKDIGEST_API_KEY=ld_live_...   # https://linkdigest.dev/signin?ref=skill-video-to-notes&next=/app/keys （可选，见下）
python3 {baseDir}/scripts/linkdigest.py --format json "<视频链接>"
```

- 10 分钟以上的课或讲座加 `--depth transcript`：全程逐字稿加少量截帧，更省，也读得更长。
- 抖音短链原样复制，`v.douyin.com/` 后面的字母区分大小写。
- 不设 Key 也能跑：每个地址每天免费 2 条，只有摘要（标题、作者、要点），没有逐字稿，所以笔记里引不了原话。这时如实告诉用户这是摘要版。

## 笔记怎么写（给 agent）

读 JSON 里的 `title`、`author`、`key_points`、`transcript`（`[{t, text}]`，`t` 是秒）和 `ocr_text`（画面上的字），按下面的样子写，不要加视频里没有的内容：

```markdown
# <标题>
来源：<链接> · 作者：<author> · 发布：<posted_at>

## 一句话
<这条视频在讲什么，一句>

## 要点
- <要点 1>
  > [mm:ss] <口播里对应的原话>
- <要点 2>
  > [mm:ss] <原话>

## 数字、名词、条款（请核对）
- <视频里出现的金额、比例、日期、法规名、产品名，逐条列出，注明是口播还是画面上的字>

## 能照着做的事
- <视频里明确说了要怎么做的步骤；没有就写「视频没有给出操作步骤」>
```

规则：

1. 每条要点下面必须有一句原话和它的时间：结果里有 `key_point_support` 就用它（按 `point_index` 对应，`quote` 是原话，`t` 是秒，`kind` 为 `image` / `on_screen` 时注明「画面」）；没有就自己在 `transcript` 里找。找不到原话的要点删掉，或标「口播里没找到」。
2. 「数字、名词、条款」一节是给用户核对用的：语音识别会把人名、数字、专业词写错，财税和法律内容尤其要对着原视频看一眼。把这句话写在笔记里。
3. 不替作者下结论，不补充「背景知识」。视频只说了一半的地方，写「视频没有展开」。
4. 用户没要逐字稿就不贴全文，问一句「要附上全文逐字稿吗？」。

## 一个博主的很多条视频

这是最常见的用法：把一位老师的几十条视频都做成笔记。平台不允许不登录列出一个账号的全部作品，所以链接要用户自己给（在 App 里逐条「复制链接」，或一次贴一批）。

- 先报数：有多少条，按下面的价格估一个总积分，用户同意再跑。
- 一条一条读，每条一个笔记文件，文件名用发布日期加标题。
- 最后写一份 `index.md`：按主题分组列出所有笔记和各自的一句话。
- 几十条以上一次提交更快：`douyin-batch-to-text`。

## 价格

每条 1 积分，加每开始的 1 分钟 1 积分：1 分钟 2，3 分钟 4，5 分钟 6，10 分钟 11。`--depth transcript` 是 1 积分加每开始的 2 分钟 1 积分。已经有人读过的链接 0 积分。注册送 10 积分（一次）。加量包一次性、不过期：50 积分 ¥9.9（支付宝）/ $1.50，250 积分 ¥36 / $5。每次运行的花费在 stderr 最后一行。

## 读不了的时候

删除、私密、直播、要登录才能看的视频返回 `422`，写明原因；平台临时拒绝返回 `503`，过一会再试；积分不够或视频超长返回 `402`，里面有补充积分的链接。这三种都不扣费。读不了就告诉用户读不了，不要根据标题编一份笔记。

## 隐私

只有链接会发到 linkdigest.dev；不用任何平台的账号或 Cookie，不在本机下载视频，读完后服务端删除媒体文件。https://linkdigest.dev/privacy · MCP：`https://linkdigest.dev/mcp` · support@linkdigest.dev
