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

## 做法三：每天自动搜一个话题，只读新出的帖子

很多人用 n8n 是为了「每天盯一个话题」：比如每天早上搜一次「牛肉面 探店」，把新出的抖音视频读成文案，放进飞书表格。两种接法：

**A. 一次调用：搜 + 读 + 对比。** 一个 HTTP Request 节点：

| 字段 | 填什么 |
|---|---|
| Method | `POST` |
| URL | `https://linkdigest.dev/api/v1/search` |
| Authentication | 同做法一（Header Auth：`Authorization` / `Bearer ld_live_…`） |
| Send Body | JSON：`{ "query": "牛肉面 探店", "platform": "douyin", "limit": 3, "digest": true }` |

返回 `202` 和 `batch_id`：搜到的帖子已经排进一个批量任务，读完后还有一页对比（共同主题、各自卖点，引用都逐字核对）。后面接 Wait（3 分钟），再接一个 HTTP Request：`GET https://linkdigest.dev/api/v1/digest/batch/{{ $json.batch_id }}?include=digests`；`status` 还不是 `done` 就再等 1 分钟、再取一次。`digests` 里是每条视频的逐字稿和要点，`synthesis.raw_markdown` 是对比。

2026-11-21 在测试账号上实际跑过：「牛肉面 探店」搜到 3 条抖音视频，搜索 4 积分，3 条各 2 积分，对比 1 积分；约 4 分钟读完。

**B. 只读新帖（推荐每天跑的用法）。** A 每次都会把搜到的帖子全读一遍；每天跑的话，昨天读过的会重复读。换成：

1. Schedule Trigger（每天几点跑）
2. HTTP Request「搜索」：同上，但 Body 去掉 `digest`，`limit` 设 10 —— 只返回 `results`（链接、标题、摘要），搜到才扣搜索的积分，搜不到不扣。
3. Split Out：拆开 `results`。
4. **Remove Duplicates**：Operation 选 *Remove Items Processed in Previous Executions*，Keep Items Where 选 *Value Is New*，Value to Dedupe On 填 `{{ $json.url }}`。n8n 会记住以前跑过的链接，只放新的过去（默认记 10,000 条；节点源码里检查和记录是同一步（checkProcessedAndRecord），条目经过时就记下，所以放在读取之前、且读取失败的那条以后不会再重试）。
5. Aggregate：把剩下的 `url` 合成一个列表；列表为空就到此结束，不用再调用。
6. HTTP Request「批量读取」：`POST https://linkdigest.dev/api/v1/digest/batch`，Body `{ "urls": {{ JSON.stringify($json.url) }}, "depth": "script" }`（只要口播文案；要画面文字和要点就去掉 `depth`；要对比加 `"synthesis": true`）。
7. Wait + `GET /api/v1/digest/batch/<batch_id>?include=digests`，同 A。
8. 写进飞书多维表格 / Google Sheets / 邮件。

这样每天只为新帖子付读取的积分。

## 做法二：AI Agent + MCP Client Tool

| 字段 | 填什么 |
|---|---|
| Endpoint | `https://linkdigest.dev/mcp` |
| Server Transport | HTTP Streamable（如果你的 n8n 只有 SSE 选项，先升级） |
| Authentication | Bearer Auth，Token 填 `ld_live_…` |

能用的工具有 5 个：`digest_url`（读一条）、`search_links`（按话题找帖子）、`compare_links`（读一批并对比）、`list_batches`、`check_balance`。

价格和中文说明：https://linkdigest.dev/zh/n8n-xiaohongshu-douyin
