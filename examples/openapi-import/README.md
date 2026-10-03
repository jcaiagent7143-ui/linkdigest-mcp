# OpenAPI 导入：扣子（Coze）这类平台

LinkDigest 的 REST API 有一份机器可读的规格：**<https://linkdigest.dev/openapi.json>**。
能从 OpenAPI 文件生成插件 / 工具的平台，导入这个地址就能用。

规格是 OpenAPI 3.0.3，刻意写得朴素：不用 `oneOf`，每个字段都有描述，规格里的响应都是 JSON。导入后会出现 4 个工具：

| 工具（operationId） | 接口 | 做什么 |
|---|---|---|
| `digest_url` | `POST /api/v1/digest` | 读一条链接。参数 `url`（链接或整段分享文案）、`format`、`breakdown`、`translate_to`、`max_credits`、`partial_ok` |
| `get_digest` | `GET /api/v1/digest/{jobId}` | 取回还在处理的任务。`wait=20` 时最多等 20 秒再返回 |
| `digest_batch` | `POST /api/v1/digest/batch` | 一次最多 50 条链接，可带 `breakdown`、`translate_to`、签名的 `webhook_url` |
| `get_batch` | `GET /api/v1/digest/batch/{batchId}` | 批量任务的进度和结果，`include=digests` 带上每条结果 |

## 扣子（Coze）

1. 扣子 → 资源库 → 创建插件 → 导入，选「URL」，填 `https://linkdigest.dev/openapi.json`。
2. 授权方式选 Service（服务），位置 Header，参数名 `Authorization`，值 `Bearer ld_live_…`（你自己的 Key，在
   <https://linkdigest.dev/app/keys> 创建）。
3. 工作流里先调 `digest_url`，`format` 用 `json`。
4. 如果返回里 `pending` 为 `true`（HTTP 202），用循环调用 `get_digest`：`jobId` 填上一步返回的 `jobId`，`wait` 填 `20`，
   直到拿到结果（最多循环 10 次）。
5. 正文用 `raw_markdown`，拆解用 `breakdown`，逐字稿用 `transcript`（`[{t, text}]`），图上文字用 `ocr_text`。

说明：上面的步骤按扣子的导入方式写成，我们还没有在扣子里实际导入跑通过。
导入或授权遇到问题，请开 [issue](https://github.com/jcaiagent7143-ui/linkdigest-mcp/issues) 或写信到 support@linkdigest.dev。

其他支持 OpenAPI 3.0 导入的平台可以试同一个地址，我们没有逐一测试。

## 先用 curl 确认流程

```bash
export LINKDIGEST_API_KEY=ld_live_...

# 1. 读一条链接；读过的链接和简短的内容直接返回 200
curl -sS -X POST https://linkdigest.dev/api/v1/digest \
  -H "Authorization: Bearer $LINKDIGEST_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://v.douyin.com/xxxx/", "format": "json", "breakdown": true}'

# 2. 长视频返回 202 {"pending": true, "jobId": "…"}，用 jobId 取结果；还是 202 就再取一次
curl -sS "https://linkdigest.dev/api/v1/digest/<jobId>?format=json&wait=20" \
  -H "Authorization: Bearer $LINKDIGEST_API_KEY"
```

## 状态码

| 状态码 | 含义 |
|---|---|
| 200 | 结果；`credits` 是这次扣的积分，读过的链接 `cached: true`、0 积分 |
| 202 | 还在处理，用 `jobId` 调 `get_digest` |
| 400 | 请求不对，比如 `url` 不是链接、`translate_to` 不是语言代码 |
| 401 | 没有 Key 或 Key 已撤销 |
| 402 | 积分不够或这条链接超出 `max_credits` / 时长上限，**没有扣费**；返回体里的 `buy_url` / `subscribe_url` 不用登录就能付款 |
| 422 | 链接读不了：删帖、私密或需要登录 |
| 429 | 请求太多，按 `Retry-After` 等一下 |
