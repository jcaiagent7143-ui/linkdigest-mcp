"""LangChain's own standard tests for tools (langchain-tests), offline.

Skipped unless langchain-tests is installed. The "integration" half runs here
against a fake HTTP layer too: it checks what the tool hands back, not the service.
"""

from __future__ import annotations

import pytest

pytest.importorskip("langchain_tests")

from langchain_tests.integration_tests import ToolsIntegrationTests  # noqa: E402
from langchain_tests.unit_tests import ToolsUnitTests  # noqa: E402

from conftest import DIGEST, jresp  # noqa: E402
from linkdigest import LinkDigest  # noqa: E402
from linkdigest.integrations.langchain import LinkDigestTool  # noqa: E402


def _client() -> LinkDigest:
    return LinkDigest("ld_live_test_key", transport=lambda req: jresp(200, DIGEST))


class TestLinkDigestToolUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[LinkDigestTool]:
        return LinkDigestTool

    @property
    def tool_constructor_params(self) -> dict:
        return {"client": _client()}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"url": "https://v.douyin.com/abc/", "depth": "script"}

    @property
    def init_from_env_params(self) -> tuple[dict, dict, dict]:
        return {"LINKDIGEST_API_KEY": "ld_live_test_key"}, {}, {}


class TestLinkDigestToolIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> type[LinkDigestTool]:
        return LinkDigestTool

    @property
    def tool_constructor_params(self) -> dict:
        return {"client": _client()}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"url": "https://v.douyin.com/abc/", "depth": "script"}
