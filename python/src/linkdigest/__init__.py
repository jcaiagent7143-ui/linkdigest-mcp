"""LinkDigest: social links (抖音, 小红书, TikTok, YouTube, X) as text an LLM can read.

    from linkdigest import LinkDigest

    ld = LinkDigest()  # reads LINKDIGEST_API_KEY; get one at https://linkdigest.dev/app/keys
    d = ld.digest("https://v.douyin.com/xxxx/", breakdown=True)
    print(d.title, d.credits)
    print(d.markdown)

Also installed: the `linkdigest` command line and the `linkdigest-mcp` stdio MCP server.
"""

from ._version import __version__
from .client import Digest, LinkDigest
from .errors import (
    AuthenticationError,
    InvalidRequestError,
    JobPendingError,
    LinkDigestError,
    NetworkError,
    PaymentRequiredError,
    RateLimitError,
    ServerError,
    UnreadableLinkError,
)

__all__ = [
    "__version__",
    "LinkDigest",
    "Digest",
    "LinkDigestError",
    "AuthenticationError",
    "InvalidRequestError",
    "JobPendingError",
    "NetworkError",
    "PaymentRequiredError",
    "RateLimitError",
    "ServerError",
    "UnreadableLinkError",
]
