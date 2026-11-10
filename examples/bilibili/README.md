# bili2notes：B站视频 → Markdown 笔记

一个单文件的命令行小工具（只用 Python 标准库，3.9+）：给它一条 B站 链接，得到一份 Markdown 笔记——
**带时间的章节大纲、要点（附核对过的原话和时间）、带 `[mm:ss]` 的逐字稿**。分P 视频可以一次读多个分 P，每 P 一个文件。

它自己不下载、不转写：调用的是托管的 [LinkDigest](https://linkdigest.dev/docs?ref=github-bili2notes) 接口（本仓库作者做的服务），由服务端读视频并返回文字。

## 30 秒用起来

```bash
curl -O https://raw.githubusercontent.com/jcaiagent7143-ui/linkdigest-mcp/main/examples/bilibili/bili2notes.py

# 没有 Key：免费看一条摘要（标题、要点、读出了多少段）
python3 bili2notes.py "https://www.bilibili.com/video/BV1pu411o7BE"

# 有 Key：完整笔记（大纲 + 要点 + 逐字稿）
export LINKDIGEST_API_KEY=ld_live_...        # 在 https://linkdigest.dev/app/keys 创建
python3 bili2notes.py "https://www.bilibili.com/video/BV1pu411o7BE" -o note.md

# 整段分享文字、b23.tv 短链、BV 号都可以直接贴
python3 bili2notes.py "【标题】 https://b23.tv/xxxxxxx" --depth script

# 分P 视频：读第 1–10 P，每 P 一个文件；开始前会列出每 P 的时长和要花的积分，确认后才开始
python3 bili2notes.py "https://www.bilibili.com/video/BV1JE411g7XF?p=2" --parts 1-10 --depth script --out-dir notes/
```

输出长什么样：[`sample-note.md`](sample-note.md)——跟李沐学AI 的《Transformer论文逐段精读》（87 分钟）在 2026-11-10 的一次真实读取：17 节大纲、15 条要点、527 行逐字稿（示例里逐字稿只保留开头 12 行）。

## 选项

| 选项 | 作用 |
|---|---|
| `--depth script` | 只要口播逐字稿，最省积分 |
| `--depth transcript`（默认） | 口播 + 少量截帧读画面上的字 |
| `--depth full` | 逐帧读画面文字（PPT、板书多的视频） |
| `--parts 1-10` / `3,5,8` / `all` | 分P 视频：再读这些分 P（已经读过的那一 P 不会重读） |
| `--yes` | `--parts` 时跳过确认。不是交互终端又没加 `--yes`，不会开始、不扣积分 |
| `--on-screen` | 笔记里加上「画面上的字」 |
| `--batch-size N` | 一批几条（免费账户 10，Dev 50，Studio 200） |
| `--from-json FILE` | 不联网：把一份已保存的接口返回渲染成笔记 |

- **大纲**：逐字稿满 8 分钟的视频才有；2026-11-10 之前就被读过并缓存的视频，缓存里的结果不带大纲。
- **要点下面的引文**：只显示服务端在视频里逐字找到的原话；没核对上的不显示。
- **花多少积分**：读之前用公开的计费规则估算并打印出来，别人读过的视频不扣，以实际扣费为准。价格见 [linkdigest.dev/pricing](https://linkdigest.dev/pricing)。
- 退出码：0 成功 · 2 参数不对 · 3 Key 无效或免费摘要用完 · 4 积分不够 · 5 链接读不了 · 6 没确认或被限流 · 7 超时。

## 它不做什么

- **不下载视频**，也不给视频文件。
- **不是离线工具**：读取发生在 LinkDigest 的服务器上，你的链接会发给 `linkdigest.dev`。
- **大会员专享、付费、私密、已删除的视频读不了**：服务端会说明原因，不扣积分。
- **不抓 UP 主主页或合集**：`--parts` 只读同一个视频自己的分 P。
- 服务端打开 B站 播放器页面时会经过住宅网络出口，做法写在 [数据来源与合规](https://linkdigest.dev/zh/shuju-laiyuan)。

想完全在本机跑、不依赖任何服务：用 `yt-dlp` 取音频再用 Whisper / faster-whisper 转写，或者看开源项目 Bili2Text。代价是要自己装环境、等转写；好处是不花钱、不出本机。

## 测试

```bash
python -m pytest examples/bilibili/test_bili2notes.py -q    # 23 个离线测试，不联网
```

---

# bili2notes: a Bilibili video → Markdown notes

A single-file CLI (Python 3.9+, standard library only). Give it a Bilibili link and get a Markdown note: **a timed
outline, key points (each with a quote that was checked against the video, and its time), and the transcript with
`[mm:ss]`**. For a multi-part video (分P) it reads several parts in one go, one file per part.

It does not download or transcribe anything itself: it calls the hosted
[LinkDigest](https://linkdigest.dev/docs?ref=github-bili2notes) API (a service by this repository's author).

```bash
curl -O https://raw.githubusercontent.com/jcaiagent7143-ui/linkdigest-mcp/main/examples/bilibili/bili2notes.py
python3 bili2notes.py "https://www.bilibili.com/video/BV1pu411o7BE"            # no key: one free summary
export LINKDIGEST_API_KEY=ld_live_...                                          # https://linkdigest.dev/app/keys
python3 bili2notes.py "https://www.bilibili.com/video/BV1pu411o7BE" -o note.md  # the full note
python3 bili2notes.py "https://www.bilibili.com/video/BV1JE411g7XF?p=2" --parts 1-10 --depth script --out-dir notes/
```

A real result: [`sample-note.md`](sample-note.md) (an 87-minute lecture read on 2026-11-10: 17 outline sections, 15 key
points, 527 transcript lines, of which the sample keeps the first 12).

- `--depth script` is speech only and the cheapest; `transcript` (default) adds a few frames; `full` reads on-screen
  text frame by frame.
- `--parts` lists each part's length and the credits it will cost, and starts only after you confirm (or pass `--yes`).
  The estimate follows the published rule; a part someone already read is free, and what is charged is the service's
  own count. Prices: [linkdigest.dev/pricing](https://linkdigest.dev/pricing).
- The outline exists for transcripts of 8 minutes or more; results cached before 2026-11-10 do not carry one.

What it does not do: it does not download video; it is not offline (the link is sent to `linkdigest.dev`, which reads
it — Bilibili's player page is opened through a residential exit, see
[data sourcing](https://linkdigest.dev/data-sourcing)); member-only, paid, private or deleted videos are refused
without charge; it never crawls an uploader's profile or a collection. For a fully local route, use `yt-dlp` with
Whisper / faster-whisper, or the open-source Bili2Text.
