"""Shared fixtures: clean environment, mocked HTTP, fake sleeps, and response bodies
shaped like the spec's schemas (they pass the models' validation)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import respx

from flow_messaging import AsyncFlow, Flow

BASE = "https://api.test"
KEY = "fk_test_x"
LIVE_KEY = "fk_live_x"
SECRET = "whsec_x"

#: The repository root (python/tests/unit -> python/tests -> python -> root).
REPO = Path(__file__).resolve().parents[3]
SPEC = REPO / "openapi" / "openapi.yaml"
FACTS = REPO / "agents" / "facts.json"

T0 = "2026-10-01T12:00:00Z"


def ulid(prefix: str, n: int = 0) -> str:
    """An ID shaped like the spec's: prefix + 26-char ULID."""
    return f"{prefix}_01JB8ZD4M6P8R0T2V4X6Z8{n:04d}"


MSG = ulid("msg", 1)
CONV = ulid("conv", 1)
SENDER = ulid("snd", 1)
CONTACT = ulid("ct", 1)
APP = ulid("app", 1)
ACCOUNT = ulid("acct", 1)
FILE = ulid("file", 1)
TPL = ulid("tpl", 1)
WH = ulid("we", 1)
KEY_ID = ulid("key", 1)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("FLOW_MESSAGING_KEY", "FLOW_MESSAGING_BASE_URL", "FLOW_MESSAGING_WEBHOOK_SECRET", "FLOW_CLAIM_TOKEN"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def mock() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        yield router


@pytest.fixture
def sleeps() -> list[float]:
    """The seconds each fake sleep was asked for."""
    return []


@pytest.fixture
def flow(sleeps: list[float]) -> Iterator[Flow]:
    client = Flow(KEY, base_url=BASE)
    client._http._sleep = sleeps.append
    yield client
    client.close()


@pytest.fixture
async def aflow(sleeps: list[float]) -> Any:
    client = AsyncFlow(KEY, base_url=BASE)

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client._http._sleep = fake_sleep
    yield client
    await client.aclose()


# Response bodies -------------------------------------------------------------


def url(path: str) -> str:
    return BASE + path


def text_content(text: str = "Hi there") -> dict[str, Any]:
    return {"kind": "basic", "text": text}


def message(
    id: str = MSG,
    *,
    content: dict[str, Any] | None = None,
    direction: str = "out",
    status: str = "queued",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": id,
        "conversation": CONV,
        "direction": direction,
        "status": status,
        "content": content or text_content(),
        "livemode": False,
        "created_at": T0,
        **extra,
    }


def conversation_ref(id: str = CONV, channel: str = "telegram") -> dict[str, Any]:
    return {"id": id, "channel": channel, "sender": SENDER, "contact": CONTACT}


def conversation(id: str = CONV, channel: str = "telegram", **extra: Any) -> dict[str, Any]:
    return {
        "id": id,
        "app": APP,
        "channel": channel,
        "sender": SENDER,
        "contact": CONTACT,
        "livemode": False,
        "opted_in": True,
        "created_at": T0,
        **extra,
    }


def sender(id: str = SENDER, **extra: Any) -> dict[str, Any]:
    return {
        "id": id,
        "channel": "telegram",
        "kind": "shared",
        "livemode": False,
        "status": "active",
        "address": {"username": "FlowSandboxBot"},
        "limits": {"new_contacts_per_day": 100, "new_contacts_per_hour": 20},
        "created_at": T0,
        **extra,
    }


def template(id: str = TPL) -> dict[str, Any]:
    return {
        "id": id,
        "sender": SENDER,
        "name": "order_update",
        "language": "en",
        "category": "utility",
        "status": "pending",
        "components": [{"type": "body", "text": "Your order {{1}} shipped."}],
        "created_at": T0,
    }


def webhook_endpoint(id: str = WH, **extra: Any) -> dict[str, Any]:
    return {
        "id": id,
        "url": "https://example.test/hooks",
        "events": ["message.received"],
        "enabled": True,
        "livemode": False,
        "created_at": T0,
        **extra,
    }


def contact(id: str = CONTACT) -> dict[str, Any]:
    return {"id": id, "channel": "telegram", "livemode": False, "address": {}, "created_at": T0}


def account() -> dict[str, Any]:
    return {"id": ACCOUNT, "name": "Test account", "plan": "free", "created_at": T0}


def app() -> dict[str, Any]:
    return {
        "id": APP,
        "account": ACCOUNT,
        "name": "Test app",
        "api_version": "2026-11-01",
        "settings": {"transcription": False, "auto_read": False},
        "created_at": T0,
    }


def api_key(mode: str = "test") -> dict[str, Any]:
    return {"id": KEY_ID, "mode": mode, "last4": "abcd", "created_at": T0}


def app_context() -> dict[str, Any]:
    return {"account": account(), "app": app(), "api_key": api_key(), "livemode": False}


def sandbox_key() -> dict[str, Any]:
    return {
        "key": KEY,
        "api_key": api_key(),
        "account": account(),
        "app": app(),
        "allowance": {
            "tier": "anonymous",
            "scope": "app",
            "channels": ["telegram", "whatsapp"],
            "contacts": {"limit": 1, "used": 0},
            "messages_per_contact": 50,
            "messages": {"limit": 50, "used": 0, "remaining": 50},
            "upgrade": "Sign in to lift the allowance.",
        },
        "claim_token": "fct_x",
        "claim_url": "https://api.test/admin/claim",
        "senders": [sender()],
    }


def device_authorization(interval: int = 5, expires_at: str = "2099-01-01T00:00:00Z") -> dict[str, Any]:
    return {
        "device_code": "dc_x",
        "user_code": "ABCD-EFGH",
        "verification_uri": "https://api.test/admin/device",
        "verification_uri_complete": "https://api.test/admin/device?user_code=ABCD-EFGH",
        "expires_in": 900,
        "expires_at": expires_at,
        "interval": interval,
    }


def device_token(status: str = "pending", interval: int = 5, **extra: Any) -> dict[str, Any]:
    return {"status": status, "interval": interval, **extra}


def file_obj(id: str = FILE) -> dict[str, Any]:
    return {
        "id": id,
        "mime_type": "image/png",
        "size_bytes": 4,
        "url": f"{BASE}/v0/files/{id}",
        "livemode": False,
        "created_at": T0,
        "expires_at": "2026-10-31T12:00:00Z",
    }


def conversation_action(action: str = "typing") -> dict[str, Any]:
    return {"conversation": CONV, "action": action}


def deleted(id: str) -> dict[str, Any]:
    return {"id": id, "deleted": True}


def simulated_inbound() -> dict[str, Any]:
    return {"message": MSG, "conversation": CONV, "channel_message_id": "sim_1", "status": "queued"}


def event_received(id: str, text: str = "Hello", **extra: Any) -> dict[str, Any]:
    """A message.received event."""
    return {
        "id": id,
        "type": "message.received",
        "created_at": T0,
        "app": APP,
        "livemode": False,
        "conversation": conversation_ref(),
        "timing": {"received_at": T0, "stored_at": T0},
        "data": {"message": message(content=text_content(text), direction="in", status="received")},
        **extra,
    }


def evt(n: int) -> str:
    return ulid("evt", n)


def page(data: list[dict[str, Any]], has_more: bool = False) -> dict[str, Any]:
    return {"object": "list", "data": data, "has_more": has_more}


def error(type: str, status_message: str = "Something went wrong.", **extra: Any) -> dict[str, Any]:
    return {
        "error": {
            "type": type,
            "message": status_message,
            "hint": f"Fix the {type}.",
            "doc_url": f"https://api.flow.engineer/docs/errors/{type}",
            **extra,
        }
    }
