"""Webhook signatures (Flow-Signature) and webhook replies."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from conftest import SECRET, event_received, evt

from flow_messaging import (
    Flow,
    WebhookSignatureError,
    construct_event,
    sign_payload,
    verify_signature,
    webhook_reply,
)
from flow_messaging.content import buttons
from flow_messaging.types import MessageReceivedEvent, TextContent
from flow_messaging.webhooks import SIGNATURE_HEADER, Webhooks, parse_signature_header

BODY = json.dumps(event_received(evt(1), "Hello webhook"))
NOW = 1_790_000_000


def test_signs_the_way_the_api_does() -> None:
    header = sign_payload(BODY, SECRET, timestamp=NOW)
    want = hmac.new(SECRET.encode(), f"t.{NOW}.{BODY}".encode(), hashlib.sha256).hexdigest()
    assert header == f"t={NOW},v1={want}"
    assert SIGNATURE_HEADER == "Flow-Signature"


@pytest.mark.parametrize("body", [BODY, BODY.encode(), bytearray(BODY.encode())])
def test_round_trip_str_and_bytes(body: str | bytes) -> None:
    header = sign_payload(body, SECRET, timestamp=NOW)
    verify_signature(body, header, SECRET, now=NOW)
    # A str signature verifies the same bytes.
    verify_signature(BODY.encode(), header, SECRET, now=NOW)


def test_wrong_secret() -> None:
    header = sign_payload(BODY, SECRET, timestamp=NOW)
    with pytest.raises(WebhookSignatureError, match="does not match") as e:
        verify_signature(BODY, header, "whsec_other", now=NOW)
    assert e.value.type == "signature_verification"


def test_tampered_body() -> None:
    header = sign_payload(BODY, SECRET, timestamp=NOW)
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY.replace("Hello", "Hullo"), header, SECRET, now=NOW)


def test_tampered_timestamp() -> None:
    header = sign_payload(BODY, SECRET, timestamp=NOW).replace(f"t={NOW}", f"t={NOW + 1}")
    with pytest.raises(WebhookSignatureError, match="does not match"):
        verify_signature(BODY, header, SECRET, now=NOW)


@pytest.mark.parametrize("header", [None, ""])
def test_missing_header(header: str | None) -> None:
    with pytest.raises(WebhookSignatureError, match="No Flow-Signature"):
        verify_signature(BODY, header, SECRET, now=NOW)


@pytest.mark.parametrize("header", ["junk", f"t={NOW}", "v1=abc", "t=soon,v1=abc", f"t={NOW},v1=", f"t={NOW},v0=abc"])
def test_malformed_header(header: str) -> None:
    assert parse_signature_header(header) is None
    with pytest.raises(WebhookSignatureError, match="malformed"):
        verify_signature(BODY, header, SECRET, now=NOW)


def test_timestamp_tolerance() -> None:
    header = sign_payload(BODY, SECRET, timestamp=NOW)
    verify_signature(BODY, header, SECRET, now=NOW + 300)
    verify_signature(BODY, header, SECRET, now=NOW - 300)
    with pytest.raises(WebhookSignatureError, match="300s"):
        verify_signature(BODY, header, SECRET, now=NOW + 301)
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY, header, SECRET, now=NOW - 301)
    verify_signature(BODY, header, SECRET, now=NOW + 1000, tolerance=1000)
    with pytest.raises(WebhookSignatureError, match="10s"):
        verify_signature(BODY, header, SECRET, now=NOW + 11, tolerance=10)


def test_default_now_is_the_clock() -> None:
    verify_signature(BODY, sign_payload(BODY, SECRET), SECRET)
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY, sign_payload(BODY, SECRET, timestamp=int(time.time()) - 3600), SECRET)


def test_several_v1_values_and_rotation() -> None:
    old = sign_payload(BODY, "whsec_old", timestamp=NOW)
    new_sig = sign_payload(BODY, SECRET, timestamp=NOW).split("v1=")[1]
    header = f"{old}, v1={new_sig.upper()}"
    verify_signature(BODY, header, SECRET, now=NOW)
    verify_signature(BODY, header, "whsec_old", now=NOW)
    # A list of secrets (rotating on the receiving side).
    only_new = sign_payload(BODY, SECRET, timestamp=NOW)
    verify_signature(BODY, only_new, ["whsec_old", SECRET], now=NOW)
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY, only_new, ["whsec_a", "whsec_b"], now=NOW)
    # Signing with several secrets gives one v1 each.
    both = sign_payload(BODY, ["whsec_old", SECRET], timestamp=NOW)
    parsed = parse_signature_header(both)
    assert parsed is not None and parsed[0] == NOW and len(parsed[1]) == 2
    verify_signature(BODY, both, "whsec_old", now=NOW)
    verify_signature(BODY, both, SECRET, now=NOW)


def test_secret_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    header = sign_payload(BODY, SECRET, timestamp=NOW)
    with pytest.raises(WebhookSignatureError, match="FLOW_MESSAGING_WEBHOOK_SECRET"):
        verify_signature(BODY, header, now=NOW)
    with pytest.raises(WebhookSignatureError, match="FLOW_MESSAGING_WEBHOOK_SECRET"):
        sign_payload(BODY, None, timestamp=NOW)  # type: ignore[arg-type]
    monkeypatch.setenv("FLOW_MESSAGING_WEBHOOK_SECRET", SECRET)
    verify_signature(BODY, header, now=NOW)
    assert isinstance(construct_event(BODY, header, now=NOW), MessageReceivedEvent)


def test_construct_event_returns_typed_model() -> None:
    header = sign_payload(BODY.encode(), SECRET, timestamp=NOW)
    event = construct_event(BODY.encode(), header, SECRET, now=NOW)
    assert isinstance(event, MessageReceivedEvent)
    assert event.id == evt(1)
    assert isinstance(event.data.message.content, TextContent)
    assert event.data.message.content.text == "Hello webhook"
    assert event.conversation is not None and event.conversation.channel == "telegram"


def test_construct_event_refuses_bad_signature() -> None:
    with pytest.raises(WebhookSignatureError):
        construct_event(BODY, sign_payload(BODY, "whsec_other", timestamp=NOW), SECRET, now=NOW)


def test_flow_webhooks_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    hooks = Flow("fk_test_x").webhooks
    assert isinstance(hooks, Webhooks)
    header = sign_payload(BODY, SECRET)
    assert hooks.verify(BODY, header, SECRET) is True
    assert hooks.verify(BODY, header, "whsec_other") is False
    assert hooks.verify(BODY, None, SECRET) is False
    assert hooks.verify(BODY, header) is False  # no secret anywhere
    monkeypatch.setenv("FLOW_MESSAGING_WEBHOOK_SECRET", SECRET)
    assert hooks.verify(BODY, header) is True
    assert isinstance(hooks.construct_event(BODY, header), MessageReceivedEvent)
    assert hooks.reply("hi") == {"reply": "hi"}
    assert Webhooks.header({"flow-SIGNATURE": header, "Other": "x"}) == header
    assert Webhooks.header({"Other": "x"}) is None


def test_webhook_reply() -> None:
    assert webhook_reply() == {}
    assert webhook_reply(None) == {}
    assert webhook_reply([]) == {}
    assert webhook_reply(()) == {}
    assert webhook_reply("hi") == {"reply": "hi"}
    b = buttons("Size?", ["S", "M"])
    assert webhook_reply(b) == {"reply": b}
    assert webhook_reply(["one", {"type": "text", "text": "two"}]) == {
        "reply": ["one", {"type": "text", "text": "two"}]
    }
    assert webhook_reply(TextContent(type="text", text="model")) == {"reply": {"type": "text", "text": "model"}}
    assert webhook_reply(b, fallback="auto") == {"reply": b, "fallback": "auto"}
    assert webhook_reply("hi", fallback=TextContent(type="text", text="plain")) == {
        "reply": "hi",
        "fallback": {"type": "text", "text": "plain"},
    }
