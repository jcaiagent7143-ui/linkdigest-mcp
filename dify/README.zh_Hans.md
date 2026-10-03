# LinkDigest for Dify

把小红书、抖音、TikTok、YouTube 或 X 的链接转成工作流能用的文本：带时间戳的转写、
屏幕文字、逐图描述与 OCR、正文与元数据。输出 Markdown 或 JSON。

源码：https://github.com/jcaiagent7143-ui/linkdigest-mcp · 服务：https://linkdigest.dev

[English](./README.md)

## 为什么需要它

工作流节点直接抓一个小红书链接，拿到的是一个引导下载 App 的壳，不是笔记本身。
内容是图片和视频，HTML 里没有字可读。抖音和 TikTok 是视频，页面上也没有转写。

LinkDigest 在自己的服务器上完成这一步——还原短链、取回媒体、转写语音、识别屏幕
文字、逐图描述——然后返回文本。

## 安装

1. 在 https://linkdigest.dev/app/keys 创建 API key（Google 一键登录，再点一个按钮）。注册送 10 个免费额度（一次性，不按月补），不需要绑卡。
2. 安装插件，把 key 填进凭据。插件会向 API 校验这个 key，且不消耗次数。

## 工具

**`digest_url(url, format)`**

| 参数 | | |
|---|---|---|
| `url` | 必填 | 分享链接原样粘贴，含 token。短链会自动还原。 |
| `format` | 可选 | `markdown`（默认）或 `json` |

长视频超过单次请求时长，插件会轮询任务直到完成（最多约 3.5 分钟）。
命中缓存的链接约 1 秒返回，且不计费。

## 返回内容

- `transcript`：带时间戳的转写；`transcript_source` 为 `native_captions`
  （平台原生字幕，精确）或 `asr`（语音识别）
- `ocr_text`：所有屏幕文字片段
- `images`：每张图片的描述
- `caption`、`key_points`，以及元数据（作者、发布时间、各项计数）
- `degraded`：当帖子有部分读不出来时非空。**转写为空但 `degraded` 非空，
  说明这是一份比原帖更薄的摘要，而不是一个本来就没内容的帖子。**

## 平台支持

| | |
|---|---|
| 小红书 | 图文笔记和视频笔记，无需登录 |
| 抖音 | 视频，以及图文笔记 |
| TikTok | 短链可还原；高负载时会被限流 |
| YouTube | 有原生字幕就用字幕，没有就实际观看后转写 |
| X | 带视频或图片的帖子 |
| 网页 | 正文与元数据 |
| **哔哩哔哩** | **不支持** —— 对本服务的出口地址返回 HTTP 412 |
| **Instagram** | **代码已接，但未做端到端验证** |

Facebook 不在范围内：它对未登录请求不返回任何帖子内容。

## 实测数字

一条 17 图的小红书笔记：17 段图片描述、381 个屏幕文字片段，约 119 秒。
一条带原生字幕的 TikTok：67 段转写，约 9 秒。

## 价格

注册送 10 个免费额度（一次性，不按月补），无需信用卡。再往上：$5 一次买 250 credits（不订阅、不过期），
或 $9/月含 500 credits——普通帖子 1 credit，视频每开始 1 分钟 1 credit。命中缓存
永远免费且不计数。详见 https://linkdigest.dev/pricing

## 网络

插件只通过 HTTPS 访问 `linkdigest.dev`，本地不运行任何东西。
