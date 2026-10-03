"""一列链接 → 一张表：标题、作者、逐字稿、图上文字、要点、钩子，和每条花了几个积分。

    pip install linkdigest-mcp          # 或在仓库里: pip install ./python
    export LINKDIGEST_API_KEY=ld_live_...
    python links_to_csv.py links.txt out.csv            # links.txt 每行一条链接或一段分享文案
    python links_to_csv.py links.txt out.csv --breakdown   # 每条 +1 积分，多出钩子 / 模板列

Links are read one after another. A link that fails (removed post, private
account) becomes a row with the error and the run goes on; running out of
credits stops the run and prints the pay link. A long video that is still
running after --max-wait keeps its job id in the row, to collect later with
`linkdigest --job <id>`.

The CSV is written as UTF-8 with a BOM so Excel and WPS open the Chinese text
correctly.
"""

from __future__ import annotations

import argparse
import csv
import sys

from linkdigest import JobPendingError, LinkDigest, LinkDigestError, PaymentRequiredError

COLUMNS = [
    "link",
    "platform",
    "title",
    "author",
    "posted_at",
    "transcript",
    "on_screen_text",
    "image_text",
    "key_points",
    "likes",
    "comments",
    "collects",
    "shares",
    "hook",
    "template",
    "credits",
    "cached",
    "degraded",
    "error",
]


def row_for(link: str, d) -> dict:
    stats = d.get("stats") or {}
    bd = d.breakdown or {}
    hook = bd.get("hook") or {}
    return {
        "link": link,
        "platform": d.platform,
        "title": d.title,
        "author": d.author,
        "posted_at": d.get("posted_at"),
        "transcript": d.transcript_text,
        "on_screen_text": "\n".join(str(x.get("text", "")) for x in d.on_screen),
        "image_text": "\n\n".join(str(img.get("ocr", "")) for img in d.images if img.get("ocr")),
        "key_points": "\n".join(d.key_points),
        "likes": stats.get("likes"),
        "comments": stats.get("comments"),
        "collects": stats.get("collects"),
        "shares": stats.get("shares"),
        "hook": hook.get("spoken") or hook.get("on_screen") or "",
        "template": "\n".join(bd.get("template") or []),
        "credits": d.credits,
        "cached": d.cached,
        "degraded": "; ".join(d.degraded),
        "error": "",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("links", help="text file, one link (or share text) per line")
    ap.add_argument("out", help="CSV file to write")
    ap.add_argument("--breakdown", action="store_true", help="爆款拆解, +1 credit per link")
    ap.add_argument("--max-wait", type=float, default=600, help="seconds to wait for one long video")
    args = ap.parse_args()

    with open(args.links, encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    ld = LinkDigest(max_wait=args.max_wait)
    spent = 0
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for i, link in enumerate(links, 1):
            print(f"[{i}/{len(links)}] {link[:80]}", file=sys.stderr)
            try:
                d = ld.digest(link, breakdown=args.breakdown)
            except PaymentRequiredError as e:
                print(f"out of credits, stopping: {e}", file=sys.stderr)
                break
            except JobPendingError as e:
                w.writerow({"link": link, "error": f"still running: linkdigest --job {e.job_id}"})
                continue
            except LinkDigestError as e:
                w.writerow({"link": link, "error": str(e)})
                continue
            spent += d.credits or 0
            w.writerow(row_for(link, d))
            f.flush()
    print(f"done: {args.out}, {spent} credit(s) spent", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
