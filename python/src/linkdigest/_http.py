"""The one place this package touches the network.

Everything else talks to a `Transport`: a callable that takes a `Request` and
returns a `Response`. The default one is the standard library's urllib, so the
package installs with no dependencies; tests pass a fake one instead.

urllib honours HTTPS_PROXY / HTTP_PROXY / NO_PROXY from the environment, so a
proxy works without configuration here.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from ._version import __version__
from .errors import NetworkError

USER_AGENT = f"linkdigest-python/{__version__} (+https://github.com/jcaiagent7143-ui/linkdigest-mcp)"


@dataclass
class Request:
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = None
    timeout: float = 60.0


@dataclass
class Response:
    status: int
    # Header names are lower-cased so lookups do not depend on the server's casing.
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def header(self, name: str, default: str = "") -> str:
        return self.headers.get(name.lower(), default)


Transport = Callable[[Request], Response]

# Where operating systems keep their CA bundle, for a Python that ships without
# one. The python.org installer on macOS is the common case: until "Install
# Certificates.command" is run, every HTTPS request fails with
# CERTIFICATE_VERIFY_FAILED, and urllib has no certifi to fall back on.
_CA_BUNDLES = (
    "/etc/ssl/cert.pem",  # macOS, Alpine, Arch
    "/etc/ssl/certs/ca-certificates.crt",  # Debian, Ubuntu
    "/etc/pki/tls/certs/ca-bundle.crt",  # Fedora, RHEL
    "/etc/ssl/ca-bundle.pem",  # openSUSE
    "/opt/homebrew/etc/ca-certificates/cert.pem",
    "/usr/local/etc/ca-certificates/cert.pem",
)
_ssl_context: Optional[ssl.SSLContext] = None


def ssl_context() -> ssl.SSLContext:
    """The default verifying context, plus a CA bundle if Python found none of its own."""
    global _ssl_context
    if _ssl_context is None:
        ctx = ssl.create_default_context()
        if not ctx.cert_store_stats().get("x509_ca"):
            candidates = []
            try:
                import certifi  # type: ignore[import-not-found]  # optional, used when present

                candidates.append(certifi.where())
            except ImportError:
                pass
            candidates.extend(_CA_BUNDLES)
            for path in candidates:
                if os.path.isfile(path):
                    try:
                        ctx.load_verify_locations(cafile=path)
                        break
                    except (OSError, ssl.SSLError):
                        continue
        _ssl_context = ctx
    return _ssl_context


def urllib_transport(req: Request) -> Response:
    """Send one request with urllib. 4xx/5xx are returned, not raised."""
    headers = {"User-Agent": USER_AGENT, **req.headers}
    r = urllib.request.Request(req.url, data=req.body, headers=headers, method=req.method)
    try:
        context = ssl_context() if req.url.startswith("https:") else None
        with urllib.request.urlopen(r, timeout=req.timeout, context=context) as resp:
            return Response(
                status=resp.status,
                headers={k.lower(): v for k, v in resp.headers.items()},
                body=resp.read(),
            )
    except urllib.error.HTTPError as e:
        # An HTTP error status is an answer from the server, not a failure to
        # reach it: hand it back so the caller can read the JSON error body.
        try:
            body = e.read()
        except OSError:
            body = b""
        return Response(
            status=e.code,
            headers={k.lower(): v for k, v in (e.headers or {}).items()},
            body=body,
        )
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
        reason = getattr(e, "reason", None) or e
        raise NetworkError(f"could not reach {req.url}: {reason}") from e
