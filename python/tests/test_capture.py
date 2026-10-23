"""`linkdigest capture <file>` end to end, offline: the extraction is replaced
by fixed parts (the real ffmpeg path runs in test_capture_ffmpeg when ffmpeg is
installed) and the network by the fake transport."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from conftest import FakeTransport, jresp
from linkdigest import capture, cli

PARTS = capture.VideoParts(audio=b"\xff\xfb" + b"a" * 1000, frames=[b"\xff\xd8\xff" + b"f1", b"\xff\xd8\xff" + b"f2"], frame_times=[2.0, 6.0], seconds=8.0, truncated=False)


@pytest.fixture()
def no_extraction(monkeypatch, tmp_path):
    clip = tmp_path / "video.mp4"
    clip.write_bytes(b"not really a video")
    monkeypatch.setattr(capture, "read_video_file", lambda path, **kw: PARTS)
    return clip


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("LINKDIGEST_API_KEY", "ld_live_cap")
    transport = FakeTransport()
    monkeypatch.setattr(capture, "urllib_transport", transport)
    monkeypatch.setattr(capture.time, "sleep", lambda s: None)
    return transport


def run(capsys, *argv: str):
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def parse_multipart(body: bytes, ctype: str):
    boundary = ctype.split("boundary=")[1].encode()
    fields = []
    for chunk in body.split(b"--" + boundary)[1:-1]:
        head, _, data = chunk.lstrip(b"\r\n").partition(b"\r\n\r\n")
        name = re.search(rb'name="([^"]+)"', head).group(1).decode()
        filename = re.search(rb'filename="([^"]+)"', head)
        fields.append((name, filename.group(1).decode() if filename else None, data[:-2]))
    return fields


def test_frames_sit_where_the_console_puts_them():
    assert capture.frame_moments(8) == [2.0, 6.0]
    assert len(capture.frame_moments(600)) == 36 and capture.frame_moments(600)[0] > 0
    assert capture.frame_moments(1) == [0.5]


def test_an_overflowing_frame_budget_is_thinned_evenly_not_truncated():
    frames = [bytes([i]) * 100 for i in range(10)]
    kept, times, dropped = capture._thin(frames, [float(i) for i in range(10)], 450)
    assert dropped == len(frames) - len(kept) and sum(len(f) for f in kept) <= 450
    assert kept[0] == frames[0] and kept[-1] == frames[-1], "the read still spans the clip"


def test_a_link_where_a_file_belongs_is_refused_with_the_steps_never_fetched(capsys, fake):
    code, out, err = run(capsys, "capture", "https://v.douyin.com/abc/")
    assert code == 2 and "reads a video FILE, not a link" in err and "保存本地" in err
    assert fake.requests == []


def test_a_missing_file_is_an_input_error(capsys, fake, tmp_path):
    code, out, err = run(capsys, "capture", str(tmp_path / "nope.mp4"), "--dry-run")
    assert code == 2 and "no such file" in err


def test_a_key_is_required_unless_it_is_a_dry_run(capsys, monkeypatch, no_extraction):
    monkeypatch.delenv("LINKDIGEST_API_KEY", raising=False)
    code, out, err = run(capsys, "capture", str(no_extraction))
    assert code == 2 and "LINKDIGEST_API_KEY" in err and "/app/keys" in err
    code, out, err = run(capsys, "capture", str(no_extraction), "--dry-run")
    assert code == 0 and "nothing was sent and nothing was charged" in err


def test_a_dry_run_reports_what_would_go_and_sends_nothing(capsys, no_extraction, fake):
    code, out, err = run(capsys, "capture", str(no_extraction), "--dry-run", "--json")
    assert code == 0 and fake.requests == []
    summary = json.loads(out)
    assert summary["frames"] == 2 and summary["audio_bytes"] == 1002 and summary["total_bytes"] == 1002 + 10
    assert summary["page_url"].endswith("/app/upload")


def test_the_request_is_the_capture_contract_and_the_poll_ends_in_markdown(capsys, no_extraction, fake):
    fake.queue += [
        jresp(202, {"id": "cap_1", "poll": "/api/v1/capture/cap_1", "retryAfter": 1}),
        jresp(200, {"status": "running", "stage": "transcribing"}),
        jresp(200, {"status": "done", "credits": 3, "view_url": "https://linkdigest.dev/app/digests/k", "digest": {"raw_markdown": "# 标题\n\n## Transcript\n[00:00] 大家好", "title": "标题"}}),
    ]
    code, out, err = run(capsys, "capture", str(no_extraction), "--url", "8.52 复制打开抖音 https://www.douyin.com/video/7001 复制此链接")
    assert code == 0 and out.startswith("# 标题") and "3 credits" in err and "transcribing" in err
    post = fake.requests[0]
    assert post.method == "POST" and post.url == "https://linkdigest.dev/api/v1/capture"
    assert post.headers["Authorization"] == "Bearer ld_live_cap"
    fields = parse_multipart(post.body, post.headers["Content-Type"])
    assert [(n, f) for n, f, _ in fields] == [("audio", "audio.mp3"), ("frames", "frame_00.jpg"), ("frames", "frame_01.jpg"), ("meta", None)]
    assert fields[0][2] == PARTS.audio and fields[1][2] == PARTS.frames[0]
    meta = json.loads(fields[3][2])
    assert meta == {"title": "", "description": "", "page_url": "https://www.douyin.com/video/7001", "duration_seconds": 8.0, "frame_times": [2.0, 6.0]}, "the share text's link, never fetched"
    assert fake.requests[1].method == "GET" and fake.requests[1].url == "https://linkdigest.dev/api/v1/capture/cap_1"


def test_json_output_leaves_out_the_markdown_and_out_writes_a_file(capsys, no_extraction, fake, tmp_path):
    fake.queue += [jresp(202, {"id": "cap_2"}), jresp(200, {"status": "done", "digest": {"raw_markdown": "# x", "title": "x", "transcript": []}})]
    target = tmp_path / "post.json"
    code, out, err = run(capsys, "capture", str(no_extraction), "--json", "-o", str(target))
    assert code == 0 and out == "" and f"wrote {target}" in err
    assert json.loads(target.read_text()) == {"title": "x", "transcript": []}


def test_a_refusal_says_what_to_do_and_does_not_retry(capsys, no_extraction, fake):
    fake.queue.append(jresp(503, {"error": "Douyin is blocking automated reads right now", "how_to_read_now": "save it and run linkdigest capture"}))
    code, out, err = run(capsys, "capture", str(no_extraction))
    assert code == 3 and "503" in err and "Douyin is blocking" in err and "linkdigest capture" in err
    assert len(fake.requests) == 1


def test_a_402_is_the_callers_to_fix(capsys, no_extraction, fake):
    fake.queue.append(jresp(402, {"error": "This read costs 3 credits; 1 is available.", "pay_url": "https://linkdigest.dev/app/billing"}))
    code, out, err = run(capsys, "capture", str(no_extraction))
    assert code == 2 and "402" in err and "3 credits" in err


def test_url_mode_is_untouched(capsys, monkeypatch):
    monkeypatch.delenv("LINKDIGEST_API_KEY", raising=False)
    code, out, err = run(capsys)
    assert code == 2 and "give a link" in err


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")
def test_a_real_file_becomes_sound_and_frames(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10", "-f", "lavfi", "-i", "sine=frequency=440",
         "-t", "9", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(clip)],
        check=True,
    )
    parts = capture.read_video_file(str(clip))
    assert 8.5 <= parts.seconds <= 9.5 and not parts.truncated
    assert parts.audio[:2] in (b"\xff\xfb", b"\xff\xf3", b"ID3"[:2]) or len(parts.audio) > 1000
    assert len(parts.frames) == 2 and parts.frame_times == capture.frame_moments(parts.seconds)
    assert all(f[:3] == b"\xff\xd8\xff" for f in parts.frames)
    short = tmp_path / "short.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10", "-t", "1", "-pix_fmt", "yuv420p", str(short)], check=True)
    with pytest.raises(capture.CaptureError, match="shorter than 3 seconds"):
        capture.read_video_file(str(short))
