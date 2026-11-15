---
name: hongguo-drama-research
description: "红果短剧 / AI短剧选题研究：读红果短剧官网的榜单（AI剧、真人剧、漫剧），把前 N 部剧的简介、标签、集数、评分和评分人数、点赞、收藏、热度、榜单名次和观众剧评读出来，再出一页对比：什么题材和标签在榜上、观众夸什么骂什么（带原话）。也能读单部剧的详情页链接。编剧、AI短剧团队、短剧解说和投稿前做选题时使用。只读公开的剧详情页，不读剧集视频。需要 LINKDIGEST_API_KEY。"
version: 1.0.0
homepage: https://linkdigest.dev/zh/docs?ref=skill-hongguo-drama-research
metadata: {"openclaw":{"requires":{"env":["LINKDIGEST_API_KEY"],"anyBins":["python3"]},"primaryEnv":"LINKDIGEST_API_KEY","envVars":[{"name":"LINKDIGEST_API_KEY","required":true,"description":"LinkDigest API Key（ld_live_ 开头），在 https://linkdigest.dev/signin?ref=skill-hongguo-drama-research&next=/app/keys 创建"}],"homepage":"https://linkdigest.dev/zh/docs?ref=skill-hongguo-drama-research"}}
required_environment_variables:
  - name: LINKDIGEST_API_KEY
    prompt: "LinkDigest API key (starts with ld_live_)"
    help: "https://linkdigest.dev/signin?ref=skill-hongguo-drama-research&next=/app/keys"
    required_for: "reading the drama pages"
---

# 红果短剧选题研究（榜单 + 剧评，带原话）

> 脚本路径 `scripts/` 相对于本技能目录。只用 Python 3.8+ 标准库。

AI 短剧做一部的成本降下来了，难的变成**拍什么**。红果短剧官网的每部剧都有公开的详情页：简介、标签、集数、评分和评分人数、点赞、收藏、热度、榜单名次，还有观众写的剧评。这个技能把榜单上的前 N 部剧一次读完，告诉你：

- 榜上是什么题材和标签（数得出来，不是感觉）；
- 每部剧的集数、评分、热度、榜单名次；
- 观众在剧评里夸什么、骂什么，带原话，可以核对。

## 什么时候用

- 「红果现在什么题材火」「AI剧榜上都是什么剧」「我想写乡村 / 年代 / 穿越题材，榜上同类剧评分怎么样、观众吐槽什么」。
- 投稿红果之前，看同类剧的评分和差评点；写短剧解说前，找观众最在意的点。

## 什么时候不用

- 要剧集里说了什么（台词、前三集钩子）：剧集只在你自己的浏览器里读——在 hongguoduanju.com 播放这一集，用 LinkDigest 浏览器插件的「读这个视频」。这个技能和我们的服务器都不下载剧集。
- 要看抖音上的短剧解说、切片：直接把抖音链接给 `douyin-video-to-text` 或 `viral-video-remake`。

## 用法

```bash
export LINKDIGEST_API_KEY=ld_live_...

python3 scripts/rank.py                       # AI剧榜，前 12 部
python3 scripts/rank.py --page real --top 20  # 真人剧
python3 scripts/rank.py --page comic          # 漫剧
python3 scripts/rank.py --page home           # 首页（热播）
python3 scripts/rank.py --no-insight          # 不做剧评洞察，每部少 1 积分

# 单部剧
python3 scripts/linkdigest.py "https://hongguoduanju.com/detail?series_id=<id>" --format json
```

输出：一张表（剧名 / 集数 · 评分 · 热度 · 榜单 / 标签），再加一页对比（题材、标签、观众夸和骂的点，带原话）。`--format json` 拿到每部剧的完整数据。

## 费用

每部剧 1 积分，加剧评洞察再 +1；对比按每 10 部 1 积分。别人读过的剧不收费。前 12 部 AI 剧加洞察大约 25 积分。

## 实测（2026-11-15）

单部「反向拿捏2：和闺蜜穿七零带着婆婆一起离」：评分 9.0（7,177 人），189.4 万赞、158.7 万收藏、109 集、6213 万热度，标签 穿越 / 逆袭 / 年代 / 乡村，9 条剧评；加洞察共 2 积分。

当天首页 + 三个分类榜共 48 部剧：最常见的标签是 都市 18、逆袭 13、现代 13、穿越 11、乡村 10；AI 剧里乡村 7 部、年代 5 部，中位数 135 集。

## 注意

- 只读红果官网公开的剧详情页；榜单页由你自己的电脑打开一次取剧目，间隔正常，不批量爬。
- 数字是读取当时红果页面上的值，会变；对比里的结论来自这一次读到的剧。
