# Dify：在工作流里读抖音、小红书链接

LinkDigest 在 Dify 插件市场上有现成插件，ID 是 **`jcaiagent7143-ui/linkdigest`**：
<https://marketplace.dify.ai/plugin/jcaiagent7143-ui/linkdigest>。源码在本仓库的 [`dify/`](../../dify/)。

## 版本

2026-10-03 查询插件市场接口，市场上的最新版是 **0.1.1**，说明里的工具参数只有 `url` 和 `format`。
本仓库 `dify/` 里是 **0.1.3**，工具多了 `translate_to`（翻译）和 `breakdown`（爆款拆解），已提交
[langgenius/dify-plugins#3210](https://github.com/langgenius/dify-plugins/pull/3210)，合并之前市场上仍是 0.1.1。

## 安装和授权

1. 在 <https://linkdigest.dev/app/keys> 创建 API Key（`ld_live_` 开头）。注册送 10 积分（一次性），不用绑卡。
2. Dify → 插件 → 探索 Marketplace，搜索 **LinkDigest**，安装。
3. 在插件的凭据里填入「API 密钥」。插件会调用 `GET /api/v1/digest/credential-check` 校验，不读链接、不扣积分。

插件只连 `linkdigest.dev`。

## 一个最小的工作流：链接 → 文案 → 改写

```
[开始]  变量 link（文本）
   │
[工具] LinkDigest · 读取社交链接（digest_url）
   │     url    = {{link}}          整段分享文案也行，服务端会取出链接
   │     format = markdown           给 LLM 读用 markdown；要拆字段用 json
   │
[LLM]  系统提示：你是短视频编导。
   │     用户提示：下面是一条内容的逐字稿、画面文字和要点：
   │              {{LinkDigest 的 text 输出}}
   │              请总结它的开头钩子和结构，并按同样结构写一版关于 [我的产品] 的脚本。
   │
[结束]
```

- 长视频一次请求读不完时，插件会自己轮询任务直到完成，最多约 3.5 分钟（`dify/linkdigest_client.py` 里的
  `DEADLINE_SECONDS = 210`）。读过的链接约 1 秒返回，不扣积分。
- 选 `json` 时，插件（0.1.3 源码）同时输出 JSON 消息和 JSON 文本：逐字稿在 `transcript`（`[{t, text}]`），图上文字在
  `ocr_text` / `images`，整条 Markdown 在 `raw_markdown`。
- 0.1.3 上架后，把 `breakdown` 设为 `true` 就能直接拿到爆款拆解（+1 积分），不再需要上面 LLM 节点去猜结构；
  拆解里的引用已经和原文逐字核对过。

## 报错时

插件把 API 的原话交给工作流：

- 积分用完（402）：消息里带一个付款链接，打开就能付，不用登录。
- 链接读不了（422）：删帖、私密账号或需要登录，消息写明原因。
- Key 无效（401）：去 <https://linkdigest.dev/app/keys> 重新创建。

不支持 B站（对我们服务器返回 HTTP 412）。完整的平台列表见仓库首页的 [README.zh-CN.md](../../README.zh-CN.md#平台支持)。
