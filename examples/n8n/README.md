# n8n：读小红书、抖音链接（不登录、不用 Cookie）

LinkDigest 只读、不发布：它不登录你的小红书或抖音账号，也不替你发笔记。下面两种做法任选一种。

## 做法一：HTTP Request 节点

| 字段 | 填什么 |
|---|---|
| Method | `POST` |
| URL | `https://linkdigest.dev/api/v1/digest` |
| Authentication | Generic Credential Type → Header Auth：Name `Authorization`，Value `Bearer ld_live_…` |
| Send Body | JSON：`{ "url": "{{ $json.url }}", "depth": "script" }`（只要口播文案；要画面文字和要点就去掉 `depth`） |

返回里 `transcript` 是带秒数的口播分段，`raw_markdown` 是整篇可读文本，小红书还有 `comments`（分享页上的热评）。

视频读得久（通常 30–90 秒）时，接口约 25 秒内先返回 `pending: true`。做法：接一个 IF 节点判断 `{{ $json.pending }}`，为真时接 Wait（15 秒），再连回同一个 HTTP Request 节点。同样的请求再发一次就会拿到结果，只扣一次积分。这个循环 2026-11-08 在测试账号上实际跑过：第一次返回 202，15 秒后第二次返回 200 和 20 段文案，记账一次，1 积分。

一次几十条：用 `POST /api/v1/digest/batch`，见 [`../python/douyin_batch.py`](../python/douyin_batch.py)。

## 做法二：AI Agent + MCP Client Tool

| 字段 | 填什么 |
|---|---|
| Endpoint | `https://linkdigest.dev/mcp` |
| Server Transport | HTTP Streamable（如果你的 n8n 只有 SSE 选项，先升级） |
| Authentication | Bearer Auth，Token 填 `ld_live_…` |

能用的工具有 5 个：`digest_url`（读一条）、`search_links`（按话题找帖子）、`compare_links`（读一批并对比）、`list_batches`、`check_balance`。

价格和中文说明：https://linkdigest.dev/zh/n8n-xiaohongshu-douyin
