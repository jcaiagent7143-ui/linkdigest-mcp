"""linkdigest.links: the same cases the site's link parser (web/src/lib/urls.ts,
web/src/lib/linkResolve.ts) and the engine's resolver pin, run here offline.
Redirects come from a fake transport, except one local HTTP server that shows
redirect_transport neither follows a redirect nor sends a cookie."""

from __future__ import annotations

import http.server
import json
import threading
from urllib.parse import quote

import pytest

from linkdigest import links
from linkdigest._http import Request, Response
from linkdigest.errors import NetworkError
from linkdigest.links import LinkError, Post, extract_url, identify, mid_to_bid, resolve

from conftest import FakeTransport

XHS = "【A16Z访谈 - 创新案例库 | 小红书 - 你的生活指南】 😆 ITbRNSf9JcVgxV5 😆 http://xhslink.com/o/3D7all8PZvv 复制本条信息，打开【小红书】App查看精彩内容！"
DY = "7.32 复制打开抖音，看看【杨大哥的作品】千问 3.8 预览版发布 https://v.douyin.com/G8Oggg_IXMA/ E@u.Ib 03/09 复制此链接，打开Dou音搜索，直接观看视频！"
TT = "Check this out! https://vt.tiktok.com/ZSVuVKYDW/ via TikTok"
BARE = "xhslink.com/o/3D7all8PZvv"


def redirect(location: str, status: int = 302) -> Response:
    return Response(status=status, headers={"location": location})


# -- extract_url ---------------------------------------------------------------


@pytest.mark.parametrize("text,expected", [
    (XHS, "http://xhslink.com/o/3D7all8PZvv"),
    (DY, "https://v.douyin.com/G8Oggg_IXMA/"),
    (TT, "https://vt.tiktok.com/ZSVuVKYDW/"),
    (BARE, "https://" + BARE),
    ("https://x.com/ProfTomYeh/status/2091167283057930455?s=20", "https://x.com/ProfTomYeh/status/2091167283057930455?s=20"),
    ("看看这个 https://www.douyin.com/video/7664299952662777098。", "https://www.douyin.com/video/7664299952662777098"),
    ("https://www.youtube.com/watch?v=CEvIs9y1uog&t=95s", "https://www.youtube.com/watch?v=CEvIs9y1uog&t=95s"),
    ("【某个标题】https://b23.tv/Ab12Cd3】", "https://b23.tv/Ab12Cd3"),
    # A short link's code is ASCII: Chinese glued onto it is share text (the site keeps it).
    ("复制xhslink.com/o/3D7all8PZvv打开", "https://xhslink.com/o/3D7all8PZvv"),
    ("看看 https://v.douyin.com/G8Oggg_IXMA/复制此链接，打开Dou音", "https://v.douyin.com/G8Oggg_IXMA/"),
    ("https://zh.wikipedia.org/wiki/抖音", "https://zh.wikipedia.org/wiki/抖音"),
    ("快手 https://v.kuaishou.com/AbCd12 复制此消息", "https://v.kuaishou.com/AbCd12"),
    ("https://mp.weixin.qq.com/s/AbCdEfGhIjKlMn12，", "https://mp.weixin.qq.com/s/AbCdEfGhIjKlMn12"),
])
def test_the_link_inside_share_text(text, expected):
    assert extract_url(text) == expected


# The site's NOT_LINKS: a sentence with a dot is not a hostname (2026-09-20).
@pytest.mark.parametrize("text", [
    "自进化.一篇就够了", "帮我总结这个笔记.谢谢", "月薪RM6k 如何分配", "someone@example.com",
    "screenshot 2026-09-19.png", "192.168.1.1", "not a link at all", "", "   ", "javascript:alert(1)", None, 42,
])
def test_text_that_is_not_a_link(text):
    assert extract_url(text) is None


@pytest.mark.parametrize("text,expected", [
    ("xiaohongshu.com", "https://xiaohongshu.com"),
    ("xiaohongshu.com/explore/123?xsec_token=abc", "https://xiaohongshu.com/explore/123?xsec_token=abc"),
    ("www.xiaohongshu.com/explore/123", "https://www.xiaohongshu.com/explore/123"),
    ("http://自进化.example.com/a", "http://自进化.example.com/a"),
])
def test_still_links(text, expected):
    assert extract_url(text) == expected


# -- identify: the site's describeLink cases ------------------------------------


def test_douyin_share_addresses_become_the_post():
    assert identify("https://www.iesdouyin.com/share/video/7675706162171448622/?region=CN&mid=1&u_code=x") == Post(
        "douyin", "7675706162171448622", "video", "https://www.douyin.com/video/7675706162171448622")
    note = identify("https://www.iesdouyin.com/share/note/7680883233300000000/?from=web")
    assert note.kind == "note" and note.canonical_url == "https://www.douyin.com/note/7680883233300000000"
    assert identify("https://www.douyin.com/jingxuan?modal_id=7685253896516363626").post_id == "7685253896516363626"
    # The engine's forms: slides share a note's id space; vid / aweme_id query ids.
    assert identify("https://www.iesdouyin.com/share/slides/7680883233300000000/").kind == "note"
    assert identify("https://www.douyin.com/user/self?vid=7685253896516363626").post_id == "7685253896516363626"
    assert identify("https://www.douyin.com/user/MS4wLjABAAAA") == Post("douyin", None, "unknown", None)


def test_xiaohongshu_keeps_xsec_token_and_drops_tracking():
    p = identify("https://www.xiaohongshu.com/discovery/item/6a6bf662000000002402de7e?xsec_token=AB12&xsec_source=pc_share&share_id=zz")
    assert p.canonical_url == "https://www.xiaohongshu.com/explore/6a6bf662000000002402de7e?xsec_token=AB12"
    inner = "https://www.xiaohongshu.com/discovery/item/6a6bf662000000002402de7e?xsec_token=T9"
    login = identify("https://www.xiaohongshu.com/login?redirectPath=" + quote(inner, safe=""))
    assert login.post_id == "6a6bf662000000002402de7e" and login.canonical_url.endswith("xsec_token=T9")


def test_xsec_token_is_literal_never_reencoded():
    # Xiaohongshu compares the token byte for byte: dFo%3D is a login wall, dFo= is the note.
    p = identify("https://www.xiaohongshu.com/explore/6a6bf662000000002402de7e?xsec_token=ABdFo%3D&xsec_source=pc_feed")
    assert p.canonical_url.endswith("?xsec_token=ABdFo=")
    plus = identify("https://www.xiaohongshu.com/explore/6a6bf662000000002402de7e?xsec_token=AB+cd=")
    assert plus.canonical_url.endswith("?xsec_token=AB+cd="), "+ stays +, not a space"
    # The /404/sec_ wall nests redirectPath after a second "?" (engine: unwrap_login_redirect).
    wall = identify("https://www.xiaohongshu.com/404/sec_abc?source=/explore?redirectPath="
                    + quote("https://www.xiaohongshu.com/explore/6a6bf662000000002402de7e?xsec_token=XY%3D", safe=""))
    assert wall.post_id == "6a6bf662000000002402de7e" and wall.canonical_url.endswith("xsec_token=XY=")
    # rednote.com and a profile's note address are the same note.
    assert identify("https://www.rednote.com/explore/6a6bf662000000002402de7e").post_id == "6a6bf662000000002402de7e"
    assert identify("https://www.xiaohongshu.com/user/profile/5a6bf662000000002402de7e/6a6bf662000000002402de7e").post_id == "6a6bf662000000002402de7e"


def test_bilibili_keeps_the_part_number():
    assert identify("https://www.bilibili.com/video/BV1stVH66E6G/?spm_id_from=333.1387&p=2").canonical_url == "https://www.bilibili.com/video/BV1stVH66E6G/?p=2"
    assert identify("https://m.bilibili.com/video/BV1stVH66E6G?p=1&share_source=copy").canonical_url == "https://www.bilibili.com/video/BV1stVH66E6G/"
    assert identify("https://www.bilibili.com/video/av170001/").post_id == "av170001"


def test_weibo_mid_becomes_its_bid():
    # The engine's 33-pair check (adapters/weibo.py, 2026-11-01), three of them here.
    assert mid_to_bid("5351369302084798") == "RlylI8KlM"
    assert mid_to_bid("5351093540225587") == "RlraW0WGv"
    assert mid_to_bid("5358241811792089") == "Ror8p7wcF"
    assert identify("https://m.weibo.cn/detail/5351369302084798").canonical_url == "https://m.weibo.cn/detail/RlylI8KlM"
    assert identify("https://weibo.com/1234567890/RlylI8KlM").post_id == "RlylI8KlM"
    assert identify("https://weibo.com/u/1234567890").post_id is None


@pytest.mark.parametrize("url,platform,post_id,canonical", [
    ("https://youtu.be/CEvIs9y1uog?t=95", "youtube", "CEvIs9y1uog", "https://www.youtube.com/watch?v=CEvIs9y1uog"),
    ("https://www.youtube.com/shorts/CEvIs9y1uog", "youtube", "CEvIs9y1uog", "https://www.youtube.com/watch?v=CEvIs9y1uog"),
    ("https://music.youtube.com/watch?v=CEvIs9y1uog&list=x", "youtube", "CEvIs9y1uog", "https://www.youtube.com/watch?v=CEvIs9y1uog"),
    ("https://www.tiktok.com/@syiok_lah/video/7675345600187092246?_r=1&_t=ZS", "tiktok", "7675345600187092246",
     "https://www.tiktok.com/@syiok_lah/video/7675345600187092246"),
    ("https://x.com/ProfTomYeh/status/2091167283057930455?s=20", "x", "2091167283057930455", "https://x.com/ProfTomYeh/status/2091167283057930455"),
    ("https://twitter.com/i/web/status/2091167283057930455", "x", "2091167283057930455", "https://x.com/i/status/2091167283057930455"),
    ("https://www.instagram.com/reel/DAbCdEf123/?igsh=xyz", "instagram", "DAbCdEf123", "https://www.instagram.com/reel/DAbCdEf123/"),
    ("https://www.instagram.com/someone/p/DAbCdEf123/", "instagram", "DAbCdEf123", "https://www.instagram.com/p/DAbCdEf123/"),
    ("https://www.kuaishou.com/short-video/3xabc123def?authorId=1", "kuaishou", "3xabc123def", "https://www.kuaishou.com/short-video/3xabc123def"),
    ("https://mp.weixin.qq.com/s/AbCdEfGhIjKlMn12", "wechat", "AbCdEfGhIjKlMn12", "https://mp.weixin.qq.com/s/AbCdEfGhIjKlMn12"),
    ("https://www.xiaoyuzhoufm.com/episode/6a6bf662000000002402de7e?s=abc", "podcast", "6a6bf662000000002402de7e",
     "https://www.xiaoyuzhoufm.com/episode/6a6bf662000000002402de7e"),
    ("https://podcasts.apple.com/cn/podcast/some-show/id1234567?i=1000654321", "podcast", "1000654321",
     "https://podcasts.apple.com/podcast/id1234567?i=1000654321"),
])
def test_other_platforms(url, platform, post_id, canonical):
    p = identify(url)
    assert (p.platform, p.post_id, p.canonical_url) == (platform, post_id, canonical)


def test_short_links_and_unknown_hosts():
    assert identify(DY) == Post("douyin", None, "unknown", None, short=True)
    assert identify("https://b23.tv/Ab12Cd3").short and identify("https://t.co/abc").platform == "x"
    assert identify("https://example.com/x") is None and identify("没有链接") is None


# -- resolve ------------------------------------------------------------------


def test_a_share_text_is_followed_one_hop_to_the_post():
    fake = FakeTransport(redirect("https://www.iesdouyin.com/share/video/7675706162171448622/?region=CN"))
    r = resolve("7.32 复制打开抖音，看看【某某的作品】 https://v.douyin.com/VeXgdE_QwTE/ 复制此链接", transport=fake)
    assert (r.post_id, r.hops, r.url, r.platform) == ("7675706162171448622", 1, "https://v.douyin.com/VeXgdE_QwTE/", "douyin")
    assert r.canonical_url == "https://www.douyin.com/video/7675706162171448622"
    assert r.final_url == "https://www.iesdouyin.com/share/video/7675706162171448622/?region=CN"
    req = fake.requests[0]
    assert req.method == "HEAD" and req.headers["User-Agent"].startswith("linkdigest-links/") and "Cookie" not in req.headers


def test_b23_lands_on_bilibili():
    r = resolve("https://b23.tv/Ab12Cd3", transport=FakeTransport(redirect("https://www.bilibili.com/video/BV1stVH66E6G/?share_source=copy")))
    assert r.canonical_url == "https://www.bilibili.com/video/BV1stVH66E6G/"


def test_head_refused_then_get():
    # xhslink.com answers HEAD with 404 and GET with the redirect (checked 2026-11-09).
    fake = FakeTransport(Response(status=404), redirect("https://www.xiaohongshu.com/discovery/item/6a8039b70000000033013dad?xsec_token=CBer%3D&type=video"))
    r = resolve(XHS, transport=fake)
    assert [q.method for q in fake.requests] == ["HEAD", "GET"]
    assert r.canonical_url == "https://www.xiaohongshu.com/explore/6a8039b70000000033013dad?xsec_token=CBer="


def test_a_chain_is_read_hop_by_hop():
    # A relative Location is joined to the hop it came from.
    fake = FakeTransport(redirect("/second"), redirect("https://www.bilibili.com/video/BV1stVH66E6G?p=3", 301))
    r = resolve("https://b23.tv/first", transport=fake)
    assert r.hops == 2 and [q.url for q in fake.requests] == ["https://b23.tv/first", "https://b23.tv/second"]
    assert r.canonical_url == "https://www.bilibili.com/video/BV1stVH66E6G/?p=3"


def test_a_hop_off_the_platforms_is_reported_never_requested():
    fake = FakeTransport(redirect("https://example.com/phish"))
    r = resolve("https://xhslink.com/o/evil", transport=fake)
    assert r.final_url == "https://example.com/phish" and r.platform is None and r.post_id is None
    assert len(fake.requests) == 1 and all("example.com" not in q.url for q in fake.requests)


def test_a_post_address_needs_no_request_and_an_unknown_host_is_not_asked():
    fake = FakeTransport()
    assert resolve("https://www.douyin.com/video/7685253896516363626", transport=fake).hops == 0
    other = resolve("https://example.com/x", transport=fake)
    assert other.platform is None and fake.requests == []


def test_errors():
    with pytest.raises(LinkError):
        resolve("没有链接", transport=FakeTransport())
    with pytest.raises(LinkError, match="expired"):
        resolve("https://v.douyin.com/gone/", transport=FakeTransport(Response(status=200), Response(status=200)))
    with pytest.raises(LinkError, match="redirects"):
        resolve("https://b23.tv/a", max_hops=2, transport=FakeTransport(redirect("https://b23.tv/b"), redirect("https://b23.tv/c")))
    with pytest.raises(NetworkError):
        resolve("https://b23.tv/a", transport=FakeTransport(NetworkError("offline")))
    # A later hop that fails keeps what the earlier ones found.
    kept = resolve("https://t.co/a", transport=FakeTransport(redirect("https://b23.tv/b"), NetworkError("offline")))
    assert kept.final_url == "https://b23.tv/b" and kept.hops == 1


def test_max_hops_mirrors_the_site():
    assert links.MAX_HOPS == 5
    assert {"v.douyin.com", "xhslink.com", "xhslink.cn", "b23.tv"} <= links.SHORT_HOSTS


# -- redirect_transport against a local server -----------------------------------


class _Server(http.server.BaseHTTPRequestHandler):
    seen: list = []

    def _answer(self):
        type(self).seen.append((self.command, self.path, self.headers.get("Cookie"), self.headers.get("User-Agent")))
        if self.path == "/short":
            self.send_response(302)
            self.send_header("Location", "/post")
            self.send_header("Set-Cookie", "session=abc; Path=/")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if self.command == "GET":
                self.wfile.write(b"x" * 1000)

    do_GET = do_HEAD = _answer

    def log_message(self, *args):  # silence
        pass


def test_redirect_transport_neither_follows_nor_keeps_cookies():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Server)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        _Server.seen.clear()
        first = links.redirect_transport(Request("GET", base + "/short", headers={"User-Agent": links.USER_AGENT}, timeout=5))
        second = links.redirect_transport(Request("HEAD", base + "/short", timeout=5))
        assert first.status == 302 and first.header("location") == "/post" and first.body == b""
        assert second.status == 302
        assert [s[1] for s in _Server.seen] == ["/short", "/short"], "the redirect was not followed"
        assert all(s[2] is None for s in _Server.seen), "the Set-Cookie was not sent back"
        assert all(s[3] == links.USER_AGENT for s in _Server.seen)
    finally:
        server.shutdown()


# -- CLI -----------------------------------------------------------------------


def test_cli_offline(capsys):
    assert links.main(["--offline", "看看 https://www.douyin.com/video/7685253896516363626 。"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["platform"] == "douyin" and out["post_id"] == "7685253896516363626"
    assert links.main(["--offline", "没有链接"]) == 2
