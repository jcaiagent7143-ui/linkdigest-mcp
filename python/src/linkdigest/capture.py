"""`linkdigest capture <video-file>`: read a video you already have.

Douyin's embed player serves most links again (2026-10-21), but a post it will
not serve answers 503 `platform_refused`. A video saved from the app (分享 →
保存本地) can be read anywhere: this command extracts its sound and a few
frames on THIS machine and sends only those to `POST /api/v1/capture`. The
video itself is never uploaded.

    linkdigest capture ~/Downloads/video.mp4 --url "https://www.douyin.com/video/…"
    linkdigest capture ./video.mp4 --title "My video" -o post.md
    linkdigest capture ./video.mp4 --dry-run --verbose     # no key, no network, no charge

Needs ffmpeg and ffprobe on PATH. Exit codes: 0 ok · 2 the file or the account
(unreadable, no key, out of credits, rate-limited) · 3 the server or the network.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from ._http import Request, Response, urllib_transport
from .client import API_KEY_ENV, DEFAULT_BASE_URL
from .errors import NetworkError

# The site's own limits (web/src/lib/capture.ts CAPTURE_LIMITS): the whole
# request stays under Amplify's ~6 MB ceiling.
MAX_AUDIO_BYTES = 3_000_000
MAX_FRAME_BYTES = 400_000
MAX_TOTAL_BYTES = 4_500_000

MIN_SECONDS = 3.0
MAX_SECONDS = 600
MAX_FRAMES = 36
FRAME_EVERY_SECONDS = 4
FRAME_WIDTH = 720
JPEG_QUALITY = 6  # ffmpeg -q:v; about the extension's 0.7 JPEG
AUDIO_KBPS = 24

EXIT_OK, EXIT_INPUT, EXIT_SERVER = 0, 2, 3

_URL_LIKE = re.compile(r"https?://|www\.|(?:douyin|xiaohongshu|rednote|bilibili)\.com", re.I)
_SEEK_TIMEOUT = 20.0


class CaptureError(ValueError):
    """The file cannot be read as a capture; nothing was sent or spent."""


@dataclass
class VideoParts:
    """What `/api/v1/capture` takes, held in memory."""

    audio: bytes
    frames: List[bytes]
    frame_times: List[float]
    seconds: float
    truncated: bool
    # Frames left out to stay under MAX_TOTAL_BYTES (thinned evenly).
    dropped: int = 0


# --- extraction (ffmpeg on this machine) -----------------------------------


def frame_moments(seconds: float, *, max_frames: int = MAX_FRAMES, every: float = FRAME_EVERY_SECONDS) -> List[float]:
    """Where to take frames: every few seconds, at most `max_frames`, never at
    0 (a frame there is often black). The same rule as the console's upload
    page, so a file read here and there shows the same moments."""
    seconds = max(0.0, float(seconds))
    count = max(1, min(max_frames, int(seconds // every)))
    step = seconds / count
    return [round(i * step + step / 2, 1) for i in range(count)]


def _thin(frames: List[bytes], times: List[float], budget: int) -> Tuple[List[bytes], List[float], int]:
    """Drop frames evenly until their total fits `budget`, keeping the first
    and the last so the read still spans the clip."""
    total = sum(len(f) for f in frames)
    if total <= budget or len(frames) <= 1:
        return frames, times, 0
    keep = max(1, min(len(frames), int(len(frames) * budget / total)))
    while True:
        if keep == 1:
            picks = [len(frames) // 2]
        else:
            picks = sorted({round(i * (len(frames) - 1) / (keep - 1)) for i in range(keep)})
        got = [frames[i] for i in picks]
        if sum(len(f) for f in got) <= budget or keep == 1:
            return got, [times[i] for i in picks], len(frames) - len(got)
        keep -= 1


def probe_duration(path: Path) -> Optional[float]:
    """How long the file plays for, in seconds; None when ffprobe cannot tell."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None
    try:
        value = float(proc.stdout.decode(errors="replace").strip())
    except ValueError:
        return None
    return value if value > 0 else None


def extract_audio(path: Path, seconds: float, *, kbps: int = AUDIO_KBPS) -> bytes:
    """The opening `seconds` of the sound track as 16 kHz mono MP3 (about 180 KB a minute at 24 kbps)."""
    tmp = Path(tempfile.mkdtemp(prefix="linkdigest_audio_"))
    out = tmp / "audio.mp3"
    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "error",
        "-t", f"{seconds:.2f}", "-i", str(path),
        "-vn", "-ac", "1", "-ar", "16000", "-f", "mp3", "-codec:a", "libmp3lame", "-b:a", f"{kbps}k",
        str(out),
    ]
    try:
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=60 + seconds)
        except subprocess.TimeoutExpired as exc:
            raise CaptureError("ffmpeg timed out extracting the sound") from exc
        if not out.exists() or out.stat().st_size == 0:
            detail = proc.stderr.decode(errors="replace")
            if "does not contain any stream" in detail:
                raise CaptureError(
                    f"{path.name} has no sound track. The transcript needs it; a video saved without audio cannot be read."
                )
            raise CaptureError(f"ffmpeg produced no audio: {detail[:200]}")
        return out.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # never persist media


def sample_frames_at(path: Path, times: List[float], *, max_width: int = FRAME_WIDTH, quality: int = JPEG_QUALITY) -> List[Tuple[float, bytes]]:
    """One JPEG at each of `times`, by input-side seeking. A frame identical to
    the one before it is dropped; frames that fail are left out."""
    tmp = Path(tempfile.mkdtemp(prefix="linkdigest_seek_"))
    got: List[Tuple[float, bytes]] = []
    try:
        for index, t in enumerate(times):
            out = tmp / f"frame_{index:04d}.jpg"
            cmd = [
                "ffmpeg", "-nostdin", "-loglevel", "error",
                "-ss", f"{max(0.0, float(t)):.2f}", "-i", str(path),
                "-frames:v", "1", "-vf", f"scale='min({max_width},iw)':-2", "-q:v", str(quality),
                str(out),
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=_SEEK_TIMEOUT)
            except subprocess.TimeoutExpired:
                continue
            if not out.exists() or out.stat().st_size == 0:
                continue
            blob = out.read_bytes()
            if got and got[-1][1] == blob:
                continue
            got.append((round(float(t), 2), blob))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return got


def read_video_file(path: str, *, max_seconds: int = MAX_SECONDS, max_frames: int = MAX_FRAMES) -> VideoParts:
    """Length, sound and frames of a local video, or CaptureError.

    A clip longer than `max_seconds` is read from its start only (`truncated`),
    as the console does; a clip shorter than three seconds is refused, because
    the site refuses it too and the extract would have been wasted.
    """
    if not shutil.which("ffmpeg"):
        raise CaptureError("ffmpeg is not on PATH. Install it (brew install ffmpeg) and run again.")
    if not shutil.which("ffprobe"):
        raise CaptureError("ffprobe is not on PATH. It ships with ffmpeg (brew install ffmpeg).")

    source = Path(path).expanduser()
    if not source.is_file():
        raise CaptureError(f"no such file: {source}")
    if not source.stat().st_size:
        raise CaptureError(f"{source.name} is empty")

    full = probe_duration(source)
    if not full:
        raise CaptureError(f"could not tell how long {source.name} is; is it a video file?")
    if full < MIN_SECONDS:
        raise CaptureError(f"{source.name} is shorter than {MIN_SECONDS:.0f} seconds")

    seconds = min(full, float(max_seconds))
    truncated = full > max_seconds + 1

    audio = extract_audio(source, seconds)
    if len(audio) > MAX_AUDIO_BYTES:
        raise CaptureError(
            f"the sound track came to {len(audio) // 1_000_000} MB, over the site's "
            f"{MAX_AUDIO_BYTES // 1_000_000} MB limit; read {max_seconds // 60} minutes or less"
        )

    frames: List[bytes] = []
    times: List[float] = []
    for t, blob in sample_frames_at(source, frame_moments(seconds, max_frames=max_frames)):
        if len(blob) > MAX_FRAME_BYTES:
            continue
        frames.append(blob)
        times.append(t)
    # No frames is not a failure: the words alone still make a digest, as on
    # the console's upload page.

    frames, times, dropped = _thin(frames, times, MAX_TOTAL_BYTES - len(audio))
    return VideoParts(audio=audio, frames=frames, frame_times=times, seconds=round(seconds, 1), truncated=truncated, dropped=dropped)


# --- the request ------------------------------------------------------------


def multipart(parts: VideoParts, meta: dict) -> Tuple[bytes, str]:
    """The capture request body: audio, frames and a JSON `meta` field. Returns (body, content-type)."""
    boundary = "----linkdigest-" + uuid.uuid4().hex
    chunks: List[bytes] = []

    def file_part(name: str, filename: str, ctype: str, blob: bytes) -> None:
        chunks.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
             f"Content-Type: {ctype}\r\n\r\n").encode() + blob + b"\r\n"
        )

    file_part("audio", "audio.mp3", "audio/mpeg", parts.audio)
    for i, blob in enumerate(parts.frames):
        file_part("frames", f"frame_{i:02d}.jpg", "image/jpeg", blob)
    chunks.append(
        (f"--{boundary}\r\nContent-Disposition: form-data; name=\"meta\"\r\nContent-Type: application/json\r\n\r\n").encode()
        + json.dumps(meta, ensure_ascii=False).encode("utf-8") + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _refusal(resp: Response) -> str:
    """The site's own sentence, plus the route it offers when there is one."""
    try:
        body = resp.json()
    except ValueError:
        return resp.text.strip()[:300] or f"HTTP {resp.status}"
    if not isinstance(body, dict):
        return str(body)[:300]
    text = str(body.get("error") or body.get("message") or f"HTTP {resp.status}")
    route = body.get("how_to_read_now")
    return f"{text}\n\n{route}" if route else text


def _looks_like_link(arg: str) -> bool:
    """A share link or share text, not a file. A real file wins even when its
    name happens to contain a hostname."""
    if Path(arg).expanduser().exists():
        return False
    return bool(_URL_LIKE.search(arg))


def _extract_url(text: str) -> str:
    m = re.search(r"https?://[^\s\"'<>，。、）)]+", text)
    return m.group(0).rstrip(".,;:!?") if m else text.strip()


LINK_NOT_A_FILE = """\
linkdigest capture reads a video FILE, not a link. For a link, run: linkdigest "<link>"

When Douyin's player will not serve a post, save the video first:

  1. In the Douyin app: Share (分享) → Save locally (保存本地), then move the
     file to your computer.
  2. linkdigest capture /path/to/video.mp4 --url "<the link>"

Without a file: open {site}/app/upload in a browser, or install the extension
({site}/extension) and press its button on the video's page.
"""


def _print_summary(summary: dict, err) -> None:
    print(
        f"{summary['file']}: {summary['seconds']:.1f} s" + (" (opening 10 minutes read)" if summary["truncated"] else ""),
        file=err,
    )
    print(
        f"sound {summary['audio_bytes'] / 1000:.0f} KB · {summary['frames']} frames"
        + (f" ({summary['dropped_frames']} left out to fit)" if summary["dropped_frames"] else "")
        + f" · {summary['total_bytes'] / 1_000_000:.2f} MB in all",
        file=err,
    )


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="linkdigest capture",
        description=(
            "Read a video file you already have. Its sound and a few frames are "
            "extracted on this machine; only those are sent. The video is not uploaded."
        ),
    )
    p.add_argument("file", nargs="?", help="the video file (MP4, MOV, WebM, …)")
    p.add_argument("--url", help="the page the video came from; carried as context only, never fetched")
    p.add_argument("--title", help="a title, when the page is not known")
    p.add_argument("--json", action="store_true", help="output JSON instead of Markdown")
    p.add_argument("-o", "--out", help="write the result here instead of stdout")
    p.add_argument("--timeout", type=float, default=360.0, help="seconds to wait for the digest")
    p.add_argument("--dry-run", action="store_true", help="extract and report what would be sent; no key, no network, no charge")
    p.add_argument("--api-key", "--key", dest="api_key", help=f"API key (default: ${API_KEY_ENV}; prefer the env var)")
    p.add_argument("--base-url", "--site", dest="base_url", default=DEFAULT_BASE_URL, help=f"the site (default {DEFAULT_BASE_URL})")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    err = sys.stderr
    if not args.file:
        _parser().error("a video file is required: linkdigest capture <file> --url <link>")

    site = args.base_url.rstrip("/")
    if _looks_like_link(args.file):
        print(LINK_NOT_A_FILE.format(site=site), file=err)
        return EXIT_INPUT

    key = (args.api_key or os.environ.get(API_KEY_ENV, "")).strip()
    if not key and not args.dry_run:
        print(f"an API key is required. Set {API_KEY_ENV} (or pass --api-key); create one at {site}/app/keys", file=err)
        return EXIT_INPUT

    page_url = f"{site}/app/upload"
    if args.url:
        candidate = _extract_url(args.url)
        if not candidate.startswith(("http://", "https://")):
            print("--url must be a link; it is only carried as the page the video came from", file=err)
            return EXIT_INPUT
        page_url = candidate

    try:
        parts = read_video_file(args.file)
    except CaptureError as exc:
        print(str(exc), file=err)
        return EXIT_INPUT

    meta = {
        "title": (args.title or "")[:300],
        "description": "",
        "page_url": page_url,
        "duration_seconds": parts.seconds,
        "frame_times": parts.frame_times,
    }
    total = len(parts.audio) + sum(len(f) for f in parts.frames)
    summary = {
        "file": args.file, "seconds": parts.seconds, "truncated": parts.truncated,
        "audio_bytes": len(parts.audio), "frames": len(parts.frames), "frame_times": parts.frame_times,
        "dropped_frames": parts.dropped, "total_bytes": total, "page_url": page_url,
    }

    if args.dry_run:
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            _print_summary(summary, err)
            print("Dry run: nothing was sent and nothing was charged.", file=err)
        return EXIT_OK

    if args.verbose:
        _print_summary(summary, err)
    print(f"sending {total / 1_000_000:.2f} MB to {site}…", file=err)
    return _send(site, key, parts, meta, args)


def _send(site: str, key: str, parts: VideoParts, meta: dict, args) -> int:
    err = sys.stderr
    body, ctype = multipart(parts, meta)
    headers = {"Authorization": f"Bearer {key}"}
    try:
        resp = urllib_transport(Request("POST", f"{site}/api/v1/capture", {**headers, "Content-Type": ctype}, body, timeout=max(60.0, args.timeout)))
    except NetworkError as exc:
        print(f"the upload failed: {exc}", file=err)
        return EXIT_SERVER
    if resp.status != 202:
        print(f"the site refused it ({resp.status}): {_refusal(resp)}", file=err)
        return EXIT_INPUT if resp.status in {400, 401, 402, 413, 429} else EXIT_SERVER
    try:
        started = resp.json()
    except ValueError:
        print("the site answered with something that is not JSON", file=err)
        return EXIT_SERVER
    capture_id = started.get("id")
    if not capture_id:
        print("the site did not say which job this is", file=err)
        return EXIT_SERVER

    poll = started.get("poll") or f"/api/v1/capture/{capture_id}"
    poll_url = poll if poll.startswith("http") else f"{site}{poll}"
    delay = float(started.get("retryAfter") or 3)
    deadline = time.monotonic() + args.timeout
    state: dict = {}
    while True:
        if time.monotonic() > deadline:
            print(f"still reading after {args.timeout:.0f} s. It carries on at {site}/app/digests — open it there.", file=err)
            return EXIT_SERVER
        time.sleep(max(1.0, delay))
        try:
            got = urllib_transport(Request("GET", poll_url, headers, None, timeout=60.0))
        except NetworkError:
            # Not retried for the POST (a second one would be billed twice);
            # a poll that fails is simply asked again.
            continue
        if got.status == 404:
            print(f"the job is gone ({capture_id}). Open {site}/app/digests.", file=err)
            return EXIT_SERVER
        if got.status >= 500:
            continue  # the engine is restarting or busy; ask again
        if got.status != 200:
            print(f"the site refused it ({got.status}): {_refusal(got)}", file=err)
            return EXIT_INPUT if got.status in {400, 401, 402, 429} else EXIT_SERVER
        try:
            state = got.json()
        except ValueError:
            print("the site answered with something that is not JSON", file=err)
            return EXIT_SERVER
        if state.get("status") == "done":
            break
        delay = float(state.get("retryAfter") or delay)
        print(f"reading… ({state.get('stage') or 'reading'})", file=err)

    digest = state.get("digest") or {}
    text = json.dumps({k: v for k, v in digest.items() if k != "raw_markdown"}, ensure_ascii=False, indent=2) if args.json else (digest.get("raw_markdown") or "")
    if args.out:
        Path(args.out).expanduser().write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=err)
    else:
        print(text)
    tail = []
    if state.get("credits") is not None:
        tail.append(f"{state['credits']} credits")
    if state.get("view_url"):
        tail.append(state["view_url"])
    if tail:
        print(" · ".join(tail), file=err)
    return EXIT_OK
