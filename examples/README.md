# 示例

| 目录 | 内容 |
|---|---|
| [`python/links_to_csv.py`](python/links_to_csv.py) | 一列链接 → CSV：标题、作者、逐字稿、画面文字、图上文字、要点、互动数据、钩子、模板、积分。用本仓库的 Python SDK |
| [`python/douyin_batch.py`](python/douyin_batch.py) | 批量提取抖音文案：一个文件的链接 → 一批读完 → 每条的口播文案（`POST /api/v1/digest/batch`，只用 requests） |
| [`n8n/`](n8n/) | n8n：HTTP Request 节点读一条链接（含视频的等待循环），或 AI Agent 挂 MCP Client Tool |
| [`dify/`](dify/) | Dify 插件市场里的 LinkDigest 插件（`jcaiagent7143-ui/linkdigest`），以及一个「链接 → 文案 → 改写」的最小工作流 |
| [`openapi-import/`](openapi-import/) | 用 `https://linkdigest.dev/openapi.json` 在扣子这类平台生成插件；长视频的循环取结果；状态码 |
| [`feishu-bitable/`](feishu-bitable/) | 飞书多维表格：字段捷径（已提交审核，未上架）和现在可用的「发送 HTTP 请求」做法 |

MCP 客户端（Cherry Studio、通义灵码、Trae、Cursor、Claude Code、魔搭）的配置在仓库首页：[README.zh-CN.md](../README.zh-CN.md#mcp-配置)。
