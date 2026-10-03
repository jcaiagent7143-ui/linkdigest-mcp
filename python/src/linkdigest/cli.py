"""linkdigest — read a social link from the terminal.

    export LINKDIGEST_API_KEY=ld_live_...
    linkdigest "https://v.douyin.com/xxxx/"                 # Markdown to stdout
    linkdigest "https://xhslink.com/o/xxxx" --breakdown     # + 爆款拆解 (+1 credit)
    linkdigest "<link>" --translate en --json > post.json   # structured JSON
    pbpaste | linkdigest -                                  # the whole share text works too
    linkdigest --job <job_id>                               # collect a job that was still running

Status (credits spent, cache hits, a job still running) goes to stderr, so
stdout stays clean for pipes.

Exit codes: 0 ok · 1 error · 2 usage or no key · 3 out of credits (prints the
pay link) · 4 still running after --max-wait (prints the job id).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, TextIO

from ._version import __version__
from .client import API_KEY_ENV, DEFAULT_MAX_WAIT, LinkDigest
from .errors import (
    KEYS_URL,
    AuthenticationError,
    JobPendingError,
    LinkDigestError,
    PaymentRequiredError,
)

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_PAYMENT, EXIT_PENDING = 0, 1, 2, 3, 4


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="linkdigest",
        description=(
            "Turn a Xiaohongshu, Douyin, TikTok, YouTube or X link into text: transcript, "
            "on-screen text, image descriptions and OCR, key points; optionally a viral "
            "breakdown (爆款拆解) and a translation. Uses the hosted API at linkdigest.dev "
            f"with the key in ${API_KEY_ENV}."
        ),
        epilog=f"Get a key: {KEYS_URL}",
    )
    p.add_argument("url", nargs="?", help="the link, or the whole share text containing it; '-' reads stdin")
    p.add_argument("--breakdown", action="store_true", help="also take the post apart: hook, timed beats, template (+1 credit)")
    p.add_argument("--translate", metavar="LANG", help="also translate, e.g. en, ja, zh-CN (+1 credit)")
    p.add_argument("--json", action="store_true", help="print the full JSON instead of Markdown")
    p.add_argument("--partial-ok", action="store_true", help="read the opening minutes of a video that is too long, instead of refusing it")
    p.add_argument("--max-credits", type=int, metavar="N", help="refuse (free of charge) if this link would cost more than N credits")
    p.add_argument("--job", metavar="JOB_ID", help="collect a digest that was still running, instead of reading a url")
    p.add_argument("--max-wait", type=float, default=DEFAULT_MAX_WAIT, metavar="SECONDS", help=f"how long to wait for a long job (default {DEFAULT_MAX_WAIT:.0f})")
    p.add_argument("--check-key", action="store_true", help="validate the API key without spending a credit, then exit")
    p.add_argument("--api-key", help=f"API key (default: ${API_KEY_ENV}; prefer the env var, arguments show up in shell history)")
    p.add_argument("--base-url", help="API base URL (default https://linkdigest.dev)")
    p.add_argument("-q", "--quiet", action="store_true", help="no status lines on stderr")
    p.add_argument("--version", action="version", version=f"linkdigest {__version__}")
    return p


def _utf8(stream: TextIO) -> None:
    """Chinese text must survive a Windows pipe (cp936 / cp1252)."""
    enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
    if enc != "utf8" and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def main(argv: Optional[List[str]] = None, stdin: Optional[TextIO] = None) -> int:
    args = _parser().parse_args(argv)
    out, err = sys.stdout, sys.stderr
    _utf8(out)

    def status(line: str) -> None:
        if not args.quiet:
            print(line, file=err, flush=True)

    url = args.url
    if url == "-":
        url = (stdin or sys.stdin).read()
    if not args.check_key and not args.job and not (url and url.strip()):
        _parser().print_usage(err)
        print("linkdigest: give a link (or '-' to read one from stdin), or --job JOB_ID", file=err)
        return EXIT_USAGE

    try:
        client = LinkDigest(args.api_key, base_url=args.base_url, max_wait=args.max_wait)
    except AuthenticationError as e:
        print(f"linkdigest: {e}", file=err)
        return EXIT_USAGE

    def on_pending(job_id: str, stage: Optional[str]) -> None:
        status(f"… still reading (job {job_id}{', ' + stage if stage else ''})")

    fmt = "json"  # always ask for JSON: it carries credits and cached, and raw_markdown
    try:
        if args.check_key:
            info = client.check_key()
            key = info.get("key") or {}
            print(f"key ok: {key.get('label') or ''} {key.get('hint') or ''}".rstrip(), file=out)
            return EXIT_OK
        if args.job:
            digest = client.collect(args.job, fmt, on_pending=on_pending)
        else:
            digest = client.digest(
                url,
                fmt,
                breakdown=args.breakdown,
                translate_to=args.translate,
                partial_ok=args.partial_ok,
                max_credits=args.max_credits,
                on_pending=on_pending,
            )
    except PaymentRequiredError as e:
        print(f"linkdigest: {e}", file=err)
        return EXIT_PAYMENT
    except JobPendingError as e:
        print(f"linkdigest: {e}", file=err)
        print(f"collect it with: linkdigest --job {e.job_id}", file=err)
        return EXIT_PENDING
    except LinkDigestError as e:
        print(f"linkdigest: {e}", file=err)
        return EXIT_ERROR

    if args.json:
        print(json.dumps(digest.data, ensure_ascii=False, indent=2), file=out)
    else:
        print(digest.markdown.rstrip("\n"), file=out)
    cost = "cached, 0 credits" if digest.cached else f"{digest.credits} credit(s)"
    status("[linkdigest] " + " · ".join(p for p in (digest.platform, cost) if p))
    for note in digest.degraded:
        status(f"[linkdigest] degraded: {note}")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
