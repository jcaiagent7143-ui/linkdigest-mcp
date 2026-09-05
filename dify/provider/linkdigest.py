from typing import Any

import requests
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from linkdigest_client import LinkDigestClient, LinkDigestError


class LinkDigestProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        api_key = str(credentials.get("api_key") or "").strip()
        if not api_key:
            raise ToolProviderCredentialValidationError("LinkDigest API key is required")
        try:
            # Costs nothing: authenticates against the poll endpoint without
            # starting a digest.
            LinkDigestClient(api_key).check_key()
        except LinkDigestError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc
        except requests.RequestException as exc:
            raise ToolProviderCredentialValidationError("Could not reach linkdigest.dev") from exc
