# 飞书多维表格：一列链接，旁边自动填好

## 字段捷径：已提交审核，还没有上架

LinkDigest 的飞书多维表格**字段捷径**已经开发完成，**2026-10-03 提交了飞书的上架审核**，目前还不能在捷径中心搜到。
上架之后会在这里和 [linkdigest.dev/zh/docs#feishu](https://linkdigest.dev/zh/docs#feishu) 给出链接。

提交审核的版本是这样用的：

1. 多维表格 → 新建字段 → 字段捷径 → 搜索「LinkDigest」。
2. 选链接所在的列、要什么（文案 / 图文里的文字 / 要点 / 爆款拆解）、是否翻译。
3. 在授权弹窗里填 API Key。Key 由飞书保管，表格的协作者看不到。

旁边会拆出结果、标题、作者、钩子、结构节拍、可复用模板、点赞、评论、收藏、分享和本次积分等列。
飞书单元格不显示错误信息，所以积分用完时，单元格里直接写付款链接；链接读不了时，单元格写明原因。

审核结果以飞书为准，上架前这一节描述的是提交的版本，不是线上可用的功能。

## 现在就能用的办法：自动化里的「发送 HTTP 请求」

在字段捷径上架之前，可以用多维表格自动化的「发送 HTTP 请求」调同一个 REST API：

| 项 | 填写 |
|---|---|
| 请求方法 | `POST` |
| URL | `https://linkdigest.dev/api/v1/digest` |
| 请求头 | `Authorization: Bearer ld_live_…`，`Content-Type: application/json` |
| 请求体 | `{"url": "<链接字段>", "format": "json"}`；要爆款拆解加 `"breakdown": true`（+1 积分） |

返回的 JSON 里，`title`、`author`、`raw_markdown`（整条内容）、`key_points`、`credits` 可以写回表格的列。

注意：

- 读过的链接和简短的内容一次就返回结果（200）。需要转写的视频、图片多的图文笔记（每张图都要描述和 OCR）
  20 秒内读不完，会先返回 202 和 `jobId`，要再发一次
  `GET https://linkdigest.dev/api/v1/digest/<jobId>?format=json&wait=20` 取结果。自动化里怎么接这第二步、
  怎么解析 JSON 写回字段，取决于飞书自动化当前的能力，我们没有完整测试过这条自动化流程。
- 链接多的话，用 Python 跑一遍再导入表格更省事：[`examples/python/links_to_csv.py`](../python/links_to_csv.py)
  会自动等长视频，输出 Excel / WPS 能直接打开的 UTF-8 CSV，再导入多维表格。
