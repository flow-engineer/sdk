"""Versions, the default base URL and the environment variable names."""

#: The API version this SDK's models were generated from; sent as ``Flow-Version``.
API_VERSION = "2026-11-01"
#: This package's version.
SDK_VERSION = "0.2.3"
DEFAULT_BASE_URL = "https://api.flow.engineer"

#: The API key, ``fk_test_...`` or ``fk_live_...``.
ENV_API_KEY = "FLOW_MESSAGING_KEY"
#: Another base URL, for a local copy of the service.
ENV_BASE_URL = "FLOW_MESSAGING_BASE_URL"
#: A webhook endpoint's signing secret, ``whsec_...``.
ENV_WEBHOOK_SECRET = "FLOW_MESSAGING_WEBHOOK_SECRET"
#: The claim token of a sandbox app, ``fct_...``, for ``device.sign_in``.
ENV_CLAIM_TOKEN = "FLOW_CLAIM_TOKEN"

DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2
#: Longest wait the client accepts before a retry; a longer ``retry_after`` is raised to the caller.
MAX_RETRY_WAIT = 60.0

NO_KEY_HELP = (
    "No key yet? Get a test key in one call, no account needed: "
    "`Flow().sandbox.create_key()`, or `curl -X POST https://api.flow.engineer/v0/sandbox/keys`."
)
