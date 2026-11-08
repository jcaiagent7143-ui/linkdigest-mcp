"""批量提取抖音文案：一个文件里的链接（每行一条链接或一段分享文案）→ 一批读完 → 每条的口播文案。

    export LINKDIGEST_API_KEY=ld_live_...
    python douyin_batch.py links.txt            # 只要口播文案（depth=script，最便宜）
    python douyin_batch.py links.txt --full     # 连画面文字、要点一起

One POST /api/v1/digest/batch, polled until status is "done", then
?include=digests for every digest at once. Links anyone has read before cost
nothing. A batch holds 10 links on the free plan, 50 on Dev, 200 on Studio;
longer lists are sent as several batches. Run live on 2026-11-08.
"""

from __future__ import annotations

import os
import sys
import time

import requests

API = "https://linkdigest.dev/api/v1/digest/batch"
PER_BATCH = int(os.environ.get("LINKDIGEST_BATCH_SIZE", "10"))


def run(urls: list[str], depth: str | None, headers: dict) -> dict:
    body = {"urls": urls, **({"depth": depth} if depth else {})}
    r = requests.post(API, headers=headers, json=body, timeout=120)
    if r.status_code == 402:
        sys.exit(f"积分不够：{r.json().get('error')}")
    r.raise_for_status()
    batch = r.json()
    while batch["status"] != "done":
        time.sleep(15)
        batch = requests.get(f"{API}/{batch['batch_id']}", headers=headers, timeout=60).json()
    full = requests.get(f"{API}/{batch['batch_id']}?include=digests", headers=headers, timeout=120).json()
    print(f"# batch {batch['batch_id']}: {batch['done']} 条读完, {batch['failed']} 条失败, {batch['credits_total']} 积分", file=sys.stderr)
    for item in batch["items"]:
        if item["status"] == "error":
            print(f"# {item['url']}: {item.get('error_code')} {item.get('error')}", file=sys.stderr)
    return full.get("digests") or {}


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    key = os.environ.get("LINKDIGEST_API_KEY") or sys.exit("先 export LINKDIGEST_API_KEY=ld_live_...")
    headers = {"Authorization": f"Bearer {key}"}
    depth = None if "--full" in sys.argv else "script"
    lines = [ln.strip() for ln in open(sys.argv[1], encoding="utf-8") if ln.strip()]
    for i in range(0, len(lines), PER_BATCH):
        for url, d in run(lines[i : i + PER_BATCH], depth, headers).items():
            text = "".join(seg["text"] for seg in d.get("transcript", []))
            print(f"## {url}\n{text}\n")


if __name__ == "__main__":
    main()
