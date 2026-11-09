"""Link parsing: the real link inside pasted share text, the post it names, and
where a short link goes. Offline first, standard library only, no API key.

    from linkdigest.links import extract_url, identify, resolve

    text = "7.32 复制打开抖音，看看【某某的作品】 https://v.douyin.com/VeXgdE_QwTE/ 复制此链接"
    extract_url(text)          # 'https://v.douyin.com/VeXgdE_QwTE/'
    identify("https://www.iesdouyin.com/share/video/7675706162171448622/?mid=1")
    # Post(platform='douyin', post_id='7675706162171448622', kind='video',
    #      canonical_url='https://www.douyin.com/video/7675706162171448622', short=False)
    resolve(text)              # follows the short link: ResolvedLink(..., post_id='7675…', hops=1)

The same rules as the free link parser at https://linkdigest.dev/zh/lianjie-jiexi
and LinkDigest's own engine, so a link parsed here names the post LinkDigest
would read. `extract_url` and `identify` never touch the network. `resolve`
reads redirects and nothing else: one request per hop (HEAD, then GET when a
server does not answer HEAD with a redirect), the body never read, no cookies,
at most MAX_HOPS hops, an honest User-Agent, and only short-link hosts are ever
asked. A hop that points off the known platforms is reported, not requested.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

from ._http import Request, Response, ssl_context
from ._version import __version__
from .errors import NetworkError

__all__ = [
    "MAX_HOPS",
    "SHORT_HOSTS",
    "USER_AGENT",
    "LinkError",
    "Post",
    "ResolvedLink",
    "extract_url",
    "identify",
    "resolve",
]

USER_AGENT = f"linkdigest-links/{__version__} (+https://github.com/jcaiagent7143-ui/linkdigest-mcp)"
#: As in the site's resolver (web/src/lib/linkResolve.ts MAX_HOPS).
MAX_HOPS = 5

#: Share short links: the address is a per-share code that redirects to the post.
#: youtu.be is not here: its path already is the video id, so identify() reads it offline.
SHORT_HOSTS = frozenset({
    "v.douyin.com",
    "xhslink.com", "xhslink.cn",
    "b23.tv",
    "vt.tiktok.com", "vm.tiktok.com",
    "t.co",
    "t.cn",
    "v.kuaishou.com",
})


class LinkError(ValueError):
    """No link in the text, a short link that goes nowhere, or too many redirects."""


@dataclass(frozen=True)
class Post:
    """What a link names, read from the address alone.

    `post_id` and `canonical_url` are None for a short link (`short` is True:
    call resolve()) and for a platform page that is not a post (a profile, a
    search). `canonical_url` is the post's own address: tracking dropped,
    Xiaohongshu's xsec_token kept (a shared note is not served without it),
    Bilibili's part number kept.
    """

    platform: str
    post_id: Optional[str]
    kind: str
    canonical_url: Optional[str]
    short: bool = False


@dataclass(frozen=True)
class ResolvedLink:
    input: str
    #: The link found in `input`.
    url: str
    #: Where the redirects ended: the last Location read (never requested if off-platform).
    final_url: str
    platform: Optional[str]
    post_id: Optional[str]
    kind: str
    canonical_url: Optional[str]
    hops: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# extract_url: the same rules as the site's lib/urls.ts extractUrl.

# The apps do not put a URL on the clipboard, they put a paragraph with a URL in
# it — 「【标题 - 作者 | 小红书 - 你的生活指南】 😆 xxx 😆 http://xhslink.com/o/… 复制本条信息…」,
# 「7.32 复制打开抖音，看看【…】 https://v.douyin.com/…/ E@u.Ib 03/09 …」. Take the first
# link; strip the punctuation Chinese share text glues onto its end.
_URL_IN_TEXT = re.compile(r"(?:https?://|www\.)[^\s<>\"'“”‘’（）()【】\[\]「」『』，。！？、]+", re.I)
# A short-link host written without a scheme. JavaScript's \b is ASCII, so a
# host glued to Chinese text (复制xhslink.com/…) still starts a match; Python's
# Unicode \b would not, hence the explicit look-behind.
_BARE_HOST = re.compile(
    r"(?<![A-Za-z0-9_])(?:xhslink\.(?:com|cn)|v\.douyin\.com|vt\.tiktok\.com|vm\.tiktok\.com|youtu\.be|b23\.tv|t\.co|t\.cn|v\.kuaishou\.com)"
    r"/[^\s<>\"'“”（）()【】，。！？、]+",
    re.I,
)
_TRAILING = re.compile(r"[.,;:!?)\]}】」』。，！？、]+$")
# When nothing in the text looked like a link, the whole text must look like a
# host — not merely contain a dot: 「自进化.一篇就够了」 is a sentence, not a domain.
_BARE_URLISH = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}(?::\d{1,5})?(?:[/?#]\S*)?$",
    re.I,
)


def extract_url(text: Any) -> Optional[str]:
    """The first link in pasted text (share text, a bare short link, a URL), or None.

    A link without a scheme gets https://. Text that only contains a dot
    (「帮我总结这个笔记.谢谢」, an email address, an IP) is not a link.
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None
    m = _URL_IN_TEXT.search(text) or _BARE_HOST.search(text)
    url = _TRAILING.sub("", m.group(0) if m else text)
    if not m and not _BARE_URLISH.match(url):
        return None
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    if len(url) > 2048:
        return None
    try:
        parts = urlparse(url)
        host = parts.hostname or ""
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or "." not in host:
        return None
    if host.lower() in SHORT_HOSTS:
        # A short link's code is ASCII, so Chinese glued onto it (…/G8Oggg_IXMA/复制此链接)
        # is the share text, not the link. Other URLs keep theirs (zh.wikipedia.org/wiki/抖音).
        tail = url[url.lower().index(host.lower()) + len(host):]
        url = url[: len(url) - len(tail)] + re.split(r"[^\x21-\x7e]", tail, maxsplit=1)[0]
    return url


# ---------------------------------------------------------------------------
# identify: platform, post id and the post's own address, from the URL alone.

_DOUYIN_HOSTS = ("douyin.com", "iesdouyin.com")
_DOUYIN_POST = re.compile(r"/(?:share/)?(video|note|slides)/(\d{8,20})(?:/|$)")
_DOUYIN_ID = re.compile(r"\d{8,20}")
_XHS_NOTE = re.compile(r"/(?:discovery/item|explore|search_result|user/profile/[0-9a-f]{24})/([0-9a-f]{24})(?:/|$)")
_XSEC = re.compile(r"[?&]xsec_token=([^&#]+)")
_BILI_BV = re.compile(r"/video/(BV[0-9A-Za-z]{10})(?:/|$)")
_BILI_AV = re.compile(r"/video/av(\d+)(?:/|$)", re.I)
_YOUTUBE_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_TIKTOK_POST = re.compile(r"^/@([^/]+)/(video|photo)/(\d{8,25})(?:/|$)")
_TIKTOK_V = re.compile(r"^/v/(\d{8,25})(?:\.html)?(?:/|$)")
_X_STATUS = re.compile(r"^/([A-Za-z0-9_]{1,15})/status(?:es)?/(\d{5,25})(?:/|$)")
_X_I_STATUS = re.compile(r"^/i/(?:web/)?status/(\d{5,25})(?:/|$)")
_INSTAGRAM = re.compile(r"^(?:/[A-Za-z0-9._]+)?/(p|reels?|tv)/([A-Za-z0-9_-]{5,})(?:/|$)")
_KUAISHOU = re.compile(r"^/(?:short-video|fw/photo)/([A-Za-z0-9_-]{6,})(?:/|$)")
_XYZ_EPISODE = re.compile(r"^/episode/([0-9a-f]{24})(?:/|$)")
_APPLE_SHOW = re.compile(r"/id(\d+)/?$")
_WECHAT_S = re.compile(r"^/s/([A-Za-z0-9_-]{10,})(?:/|$)")
# Weibo (the engine's adapters/weibo.py): a bid or a numeric mid.
_WEIBO_REF = re.compile(r"[A-Za-z0-9]{7,19}")
_WEIBO_PAGE_WORDS = {"detail", "status", "u", "tv", "show", "p", "profile", "n", "api"}
_BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _host_is(host: str, *domains: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def _literal_xsec_token(url: str) -> Optional[str]:
    """xsec_token exactly as Xiaohongshu compares it: decoded once, never re-encoded.

    `…dFo%3D` is a login wall where `…dFo=` is the note, and `+` must stay `+`
    (form decoding would make it a space)."""
    m = _XSEC.search(url)
    return unquote(m.group(1)) if m else None


def _unwrap_xhs(url: str) -> str:
    """The note address a Xiaohongshu login or /404/sec_ interstitial carries in redirectPath."""
    parts = urlparse(url)
    if not parts.path.startswith(("/login", "/404")):
        return url
    inner = (parse_qs(parts.query).get("redirectPath") or [""])[0]
    if not inner:
        # The /404/sec_… wall nests redirectPath after a second "?" in its `source` value.
        m = re.search(r"[?&]redirectPath=([^&]+)", url)
        inner = unquote(m.group(1)) if m else ""
    inner = urljoin(url, inner) if inner else ""
    host = (urlparse(inner).hostname or "").lower()
    return inner if inner and _host_is(host, "xiaohongshu.com", "rednote.com") else url


def mid_to_bid(mid: str) -> str:
    """A numeric Weibo mid as its bid (Weibo's base62.js: 7-digit groups from the
    right, every group but the leftmost padded to four characters)."""
    groups = [mid[max(0, i - 7):i] for i in range(len(mid), 0, -7)]
    out = ""
    for index, group in enumerate(reversed(groups)):
        n, code = int(group), ""
        while n:
            code = _BASE62[n % 62] + code
            n //= 62
        code = code or "0"
        out += code.rjust(4, "0") if index else code
    return out


def _weibo_ref(path: str) -> Optional[str]:
    segs = [s for s in path.split("/") if s]
    if len(segs) >= 2 and segs[-2] in ("detail", "status"):
        return segs[-1] if _WEIBO_REF.fullmatch(segs[-1]) else None
    if len(segs) == 2 and segs[0].isdigit() and _WEIBO_REF.fullmatch(segs[1]) and segs[1] not in _WEIBO_PAGE_WORDS:
        return segs[1]
    return None


def _post(platform: str, post_id: Optional[str], kind: str, canonical: Optional[str]) -> Post:
    if post_id is None:
        return Post(platform, None, "unknown", None)
    return Post(platform, post_id, kind, canonical)


def identify(url_or_text: str) -> Optional[Post]:
    """The platform and post a link names, without any network request.

    Accepts a URL or pasted share text (the link is extracted first). None when
    there is no link or its host is not a platform this module knows. A short
    link (v.douyin.com, xhslink.com, b23.tv …) returns `short=True` and no id:
    the id is only behind its redirect, which is what resolve() reads.
    """
    url = extract_url(url_or_text)
    if not url:
        return None
    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    path, query = parts.path, parts.query
    qs = parse_qs(query)
    first = lambda name: (qs.get(name) or [""])[0]  # noqa: E731

    if host in SHORT_HOSTS:
        platform = {
            "v.douyin.com": "douyin", "xhslink.com": "xiaohongshu", "xhslink.cn": "xiaohongshu",
            "b23.tv": "bilibili", "vt.tiktok.com": "tiktok", "vm.tiktok.com": "tiktok",
            "t.co": "x", "t.cn": "weibo", "v.kuaishou.com": "kuaishou",
        }[host]
        return Post(platform, None, "unknown", None, short=True)

    if _host_is(host, *_DOUYIN_HOSTS):
        m = _DOUYIN_POST.search(path)
        if m:
            kind = "video" if m.group(1) == "video" else "note"
            return _post("douyin", m.group(2), kind, f"https://www.douyin.com/{kind}/{m.group(2)}")
        for name in ("modal_id", "vid", "aweme_id"):
            if _DOUYIN_ID.fullmatch(first(name)):
                return _post("douyin", first(name), "video", f"https://www.douyin.com/video/{first(name)}")
        return _post("douyin", None, "", None)

    if _host_is(host, "xiaohongshu.com", "rednote.com"):
        inner = _unwrap_xhs(url)
        m = _XHS_NOTE.match(urlparse(inner).path)
        if not m:
            return _post("xiaohongshu", None, "", None)
        token = _literal_xsec_token(inner)
        canonical = f"https://www.xiaohongshu.com/explore/{m.group(1)}"
        if token:
            canonical += "?xsec_token=" + quote(token, safe="=+/-_.~!*'()")
        return _post("xiaohongshu", m.group(1), "note", canonical)

    if _host_is(host, "bilibili.com"):
        m = _BILI_BV.search(path)
        vid = m.group(1) if m else (f"av{_BILI_AV.search(path).group(1)}" if _BILI_AV.search(path) else None)
        if not vid:
            return _post("bilibili", None, "", None)
        part = first("p")
        canonical = f"https://www.bilibili.com/video/{vid}/" + (f"?p={part}" if part.isdigit() and part != "1" else "")
        return _post("bilibili", vid, "video", canonical)

    if _host_is(host, "weibo.com", "weibo.cn"):
        ref = _weibo_ref(path)
        if not ref:
            return _post("weibo", None, "", None)
        bid = mid_to_bid(ref) if ref.isdigit() and len(ref) >= 15 else ref
        return _post("weibo", bid, "post", f"https://m.weibo.cn/detail/{bid}")

    if _host_is(host, "youtube.com", "youtu.be"):
        if host == "youtu.be":
            video = path.strip("/").split("/")[0]
        elif path.startswith(("/shorts/", "/live/", "/embed/")):
            video = path.split("/")[2]
        elif path == "/watch":
            video = first("v")
        else:
            video = ""
        if not _YOUTUBE_ID.fullmatch(video):
            return _post("youtube", None, "", None)
        return _post("youtube", video, "video", f"https://www.youtube.com/watch?v={video}")

    if _host_is(host, "tiktok.com"):
        m = _TIKTOK_POST.match(path)
        if m:
            kind = "video" if m.group(2) == "video" else "note"
            return _post("tiktok", m.group(3), kind, f"https://www.tiktok.com/@{m.group(1)}/{m.group(2)}/{m.group(3)}")
        m = _TIKTOK_V.match(path)
        if m:
            return _post("tiktok", m.group(1), "video", f"https://m.tiktok.com/v/{m.group(1)}.html")
        return _post("tiktok", None, "", None)

    if _host_is(host, "x.com", "twitter.com"):
        m = _X_STATUS.match(path)
        if m and m.group(1) != "i":
            return _post("x", m.group(2), "post", f"https://x.com/{m.group(1)}/status/{m.group(2)}")
        m = _X_I_STATUS.match(path)
        if m:
            return _post("x", m.group(1), "post", f"https://x.com/i/status/{m.group(1)}")
        return _post("x", None, "", None)

    if _host_is(host, "instagram.com"):
        m = _INSTAGRAM.match(path)
        if not m:
            return _post("instagram", None, "", None)
        section = "p" if m.group(1) == "p" else "reel"
        return _post("instagram", m.group(2), "post" if section == "p" else "video",
                     f"https://www.instagram.com/{section}/{m.group(2)}/")

    if _host_is(host, "kuaishou.com"):
        m = _KUAISHOU.match(path)
        if not m:
            return _post("kuaishou", None, "", None)
        return _post("kuaishou", m.group(1), "video", f"https://www.kuaishou.com/short-video/{m.group(1)}")

    if host == "mp.weixin.qq.com":
        m = _WECHAT_S.match(path)
        if m:
            return _post("wechat", m.group(1), "article", f"https://mp.weixin.qq.com/s/{m.group(1)}")
        if path.rstrip("/") == "/s" and all(first(k) for k in ("__biz", "mid", "idx", "sn")):
            keep = "&".join(f"{k}={quote(first(k), safe='=')}" for k in ("__biz", "mid", "idx", "sn"))
            return _post("wechat", first("sn"), "article", f"https://mp.weixin.qq.com/s?{keep}")
        return _post("wechat", None, "", None)

    if _host_is(host, "xiaoyuzhoufm.com"):
        m = _XYZ_EPISODE.match(path)
        if not m:
            return _post("podcast", None, "", None)
        return _post("podcast", m.group(1), "episode", f"https://www.xiaoyuzhoufm.com/episode/{m.group(1)}")

    if host == "podcasts.apple.com":
        show, episode = _APPLE_SHOW.search(path), first("i")
        if not (show and episode.isdigit()):
            return _post("podcast", None, "", None)
        return _post("podcast", episode, "episode", f"https://podcasts.apple.com/podcast/id{show.group(1)}?i={episode}")

    return None


# ---------------------------------------------------------------------------
# resolve: read the redirects of a short link, nothing else.


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None  # urllib then raises HTTPError carrying the 3xx and its Location


def redirect_transport(req: Request) -> Response:
    """One request whose redirect is returned, not followed; the body is never read.

    No cookie processor is installed, so no cookie is ever sent or kept.
    """
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ssl_context()))
    r = urllib.request.Request(req.url, headers={"User-Agent": USER_AGENT, **req.headers}, method=req.method)
    try:
        with opener.open(r, timeout=req.timeout) as resp:
            return Response(status=resp.status, headers={k.lower(): v for k, v in resp.headers.items()})
    except urllib.error.HTTPError as e:
        headers = {k.lower(): v for k, v in (e.headers or {}).items()}
        e.close()
        return Response(status=e.code, headers=headers)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        reason = getattr(e, "reason", None) or e
        raise NetworkError(f"could not reach {req.url}: {reason}") from e


def _known_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in SHORT_HOSTS or identify(url) is not None


def resolve(
    text_or_url: str,
    *,
    max_hops: int = MAX_HOPS,
    timeout: float = 8.0,
    transport: Optional[Callable[[Request], Response]] = None,
) -> ResolvedLink:
    """The post behind pasted text or a link, following short-link redirects.

    Only short-link hosts (SHORT_HOSTS) are requested; a link that is already a
    post address is identified with no request at all. Each hop is HEAD, then
    GET when the server does not answer HEAD with a redirect; only the status
    and Location are read. A hop to a host this module does not know is
    returned as `final_url` without being requested (platform None).

    Raises LinkError when there is no link, a short link redirects nowhere (it
    has usually expired) or there are more than `max_hops` redirects, and
    NetworkError when the first hop cannot be reached (a later hop that fails
    keeps what the earlier ones found).
    """
    send = transport or redirect_transport
    url = extract_url(text_or_url)
    if not url:
        raise LinkError("no link found in the text: paste the link, or the whole text the app's Share → Copy link gave you")
    current, hops = url, 0
    while (urlparse(current).hostname or "").lower() in SHORT_HOSTS:
        if hops >= max_hops:
            raise LinkError(f"more than {max_hops} redirects; stopped at {current}")
        try:
            resp = send(Request("HEAD", current, headers={"User-Agent": USER_AGENT}, timeout=timeout))
            if not (300 <= resp.status < 400 and resp.header("location")):
                resp = send(Request("GET", current, headers={"User-Agent": USER_AGENT}, timeout=timeout))
        except NetworkError:
            if hops == 0:
                raise
            break
        location = resp.header("location") if 300 <= resp.status < 400 else ""
        if not location:
            if hops == 0:
                raise LinkError(f"{current} did not redirect anywhere (HTTP {resp.status}); it has probably expired — copy a fresh link")
            break
        hops += 1
        current = urljoin(current, location)
        if not _known_host(current):
            break  # reported, never requested
    post = identify(current)
    return ResolvedLink(
        input=text_or_url,
        url=url,
        final_url=current,
        platform=post.platform if post else None,
        post_id=post.post_id if post else None,
        kind=post.kind if post else "unknown",
        canonical_url=post.canonical_url if post else None,
        hops=hops,
    )


# ---------------------------------------------------------------------------
# The linkdigest-links command.


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="linkdigest-links",
        description="Find the link in pasted share text and the post it names (抖音, 小红书, B站, 微博, YouTube, "
        "TikTok, X, Instagram, 快手, 公众号, 小宇宙). Short links are followed redirect by redirect; "
        "nothing else is fetched and no key is needed.",
    )
    parser.add_argument("text", help='a link or the whole share text; "-" reads standard input')
    parser.add_argument("--offline", action="store_true", help="do not follow short links (no network at all)")
    parser.add_argument("--version", action="version", version=f"linkdigest-links {__version__}")
    args = parser.parse_args(argv)
    text = sys.stdin.read() if args.text == "-" else args.text
    try:
        if args.offline:
            url = extract_url(text)
            if not url:
                raise LinkError("no link found in the text")
            post = identify(url)
            out: Dict[str, Any] = {"input": text, "url": url, **(asdict(post) if post else {"platform": None})}
        else:
            out = resolve(text).to_dict()
    except LinkError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except NetworkError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 3
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
