"""flow.conversation(...): handles from IDs, models, refs, events and dicts."""

from __future__ import annotations

import json
from typing import Any

import pytest
import respx
from conftest import (
    CONV,
    MSG,
    conversation,
    conversation_action,
    conversation_ref,
    event_received,
    evt,
    message,
    page,
    url,
)

from flow_messaging import ConversationHandle, Flow
from flow_messaging.types import Conversation, ConversationRef, parse_event


@pytest.mark.parametrize(
    ("ref", "channel"),
    [
        (CONV, None),
        (Conversation.model_validate(conversation(channel="whatsapp")), "whatsapp"),
        (ConversationRef.model_validate(conversation_ref(channel="imessage")), "imessage"),
        (parse_event(event_received(evt(1))), "telegram"),
        ({"id": CONV, "channel": "sms"}, "sms"),
        ({"id": CONV}, None),
    ],
)
def test_conversation_accepts(ref: Any, channel: str | None, flow: Flow) -> None:
    h = flow.conversation(ref)
    assert isinstance(h, ConversationHandle)
    assert h.id == CONV
    assert h.channel == channel
    assert CONV in repr(h)


@pytest.mark.parametrize("ref", [123, None, {"channel": "sms"}, object()])
def test_conversation_refuses(ref: Any, flow: Flow) -> None:
    with pytest.raises(ValueError, match="conversation ID"):
        flow.conversation(ref)


def test_event_without_conversation_refused(flow: Flow) -> None:
    deleted = parse_event(
        {
            "id": evt(2),
            "type": "contact.deleted",
            "created_at": "2026-10-01T12:00:00Z",
            "app": "app_x",
            "livemode": False,
            "timing": {"received_at": "2026-10-01T12:00:00Z", "stored_at": "2026-10-01T12:00:00Z"},
            "data": {"contact": "ct_x"},
        }
    )
    with pytest.raises(ValueError):
        flow.conversation(deleted)


def test_handle_actions(flow: Flow, mock: respx.MockRouter) -> None:
    send = mock.post(url(f"/v1/conversations/{CONV}/messages")).respond(json=message())
    typing = mock.post(url(f"/v1/conversations/{CONV}/typing")).respond(json=conversation_action())
    read = mock.post(url(f"/v1/conversations/{CONV}/read")).respond(json=conversation_action("read"))
    msgs = mock.get(url(f"/v1/conversations/{CONV}/messages")).respond(json=page([message()]))
    h = flow.conversation(CONV)

    h.send("hi", reply_to=MSG, metadata={"k": "v"}, idempotency_key="idem-1")
    assert json.loads(send.calls.last.request.read()) == {
        "content": {"type": "text", "text": "hi"},
        "reply_to": MSG,
        "metadata": {"k": "v"},
    }
    assert send.calls.last.request.headers["idempotency-key"] == "idem-1"

    h.react(MSG, "👍")
    assert json.loads(send.calls.last.request.read()) == {
        "content": {"type": "reaction", "message_id": MSG, "emoji": "👍"},
        "fallback": "auto",
    }
    h.react(MSG, None)
    assert json.loads(send.calls.last.request.read()) == {
        "content": {"type": "reaction", "message_id": MSG, "emoji": None},
        "fallback": "auto",
    }

    h.typing("off")
    assert json.loads(typing.calls.last.request.read()) == {"state": "off"}
    h.mark_read()
    assert json.loads(read.calls.last.request.read()) == {}
    h.mark_read(MSG)
    assert json.loads(read.calls.last.request.read()) == {"up_to": MSG}
    assert [m.id for m in h.messages(limit=5)] == [MSG]
    assert msgs.calls.last.request.url.params["limit"] == "5"
