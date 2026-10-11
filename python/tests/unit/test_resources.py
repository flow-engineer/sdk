"""Every resource method: HTTP method, path, query and JSON body, and the typed answer."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from conftest import (
    CONTACT,
    CONV,
    FILE,
    KEY,
    MSG,
    SENDER,
    TPL,
    WH,
    app_context,
    capabilities,
    contact,
    conversation,
    conversation_action,
    deleted,
    event_received,
    evt,
    file_obj,
    message,
    page,
    sender,
    simulated_inbound,
    template,
    url,
    webhook_endpoint,
)

from flow_messaging import APIError, Flow
from flow_messaging.types import (
    AppContext,
    Capabilities,
    Contact,
    Conversation,
    ConversationAction,
    Deleted,
    File,
    Message,
    MessageReceivedEvent,
    Sender,
    SimulatedInbound,
    Template,
    TextContent,
    TranscriptEntry,
    WebhookEndpoint,
)


def sent(route: respx.Route) -> Any:
    return json.loads(route.calls.last.request.read())


# messages ---------------------------------------------------------------------


def test_send_string_becomes_text(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v1/conversations/{CONV}/messages")).respond(json=message())
    msg = flow.messages.send(CONV, "Hello")
    assert isinstance(msg, Message)
    assert msg.id == MSG
    assert sent(route) == {"content": {"type": "text", "text": "Hello"}}


def test_send_dict_with_options(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v1/conversations/{CONV}/messages")).respond(json=message(reply_to="msg_prev"))
    content = {"type": "buttons", "text": "Size?", "buttons": [{"id": "s", "label": "S"}]}
    msg = flow.messages.send(
        CONV,
        content,
        reply_to="msg_prev",
        fallback="auto",
        metadata={"order": "42"},
        channel_options={"telegram": {"disable_notification": True}},
    )
    assert msg.reply_to == "msg_prev"
    assert sent(route) == {
        "content": content,
        "reply_to": "msg_prev",
        "fallback": "auto",
        "metadata": {"order": "42"},
        "channel_options": {"telegram": {"disable_notification": True}},
    }


def test_send_model_omits_unset_fields(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v1/conversations/{CONV}/messages")).respond(json=message())
    flow.messages.send(CONV, TextContent(type="text", text="Hi"), fallback={"type": "text", "text": "Hi (plain)"})
    assert sent(route) == {
        "content": {"type": "text", "text": "Hi"},
        "fallback": {"type": "text", "text": "Hi (plain)"},
    }


def test_send_model_keeps_set_fields(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v1/conversations/{CONV}/messages")).respond(json=message())
    flow.messages.send(CONV, TextContent(type="text", text="*Hi*", format="markdown"))
    assert sent(route)["content"] == {"type": "text", "text": "*Hi*", "format": "markdown"}


@pytest.mark.parametrize(
    ("to", "expected"),
    [
        ("ct_01JB8ZD4M6P8R0T2V4X6Z80001", {"contact": "ct_01JB8ZD4M6P8R0T2V4X6Z80001"}),
        ("+15555550100", {"phone": "+15555550100"}),
        ({"telegram_user_id": "123"}, {"telegram_user_id": "123"}),
    ],
)
def test_start_recipients(to: Any, expected: dict[str, str], flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v1/messages")).respond(201, json=message())
    flow.messages.start(sender=SENDER, to=to, content="Hi", consent={"method": "web_form"})
    assert sent(route) == {
        "sender": SENDER,
        "to": expected,
        "content": {"type": "text", "text": "Hi"},
        "consent": {"method": "web_form"},
    }
    assert "idempotency-key" in route.calls.last.request.headers


def test_start_bad_string_raises_value_error(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v1/messages")).respond(201, json=message())
    with pytest.raises(ValueError, match="contact ID"):
        flow.messages.start(sender=SENDER, to="someone@example.com", content="Hi")
    assert not route.called


def test_retrieve_edit_unsend(flow: Flow, mock: respx.MockRouter) -> None:
    get = mock.get(url(f"/v1/messages/{MSG}")).respond(json=message())
    patch = mock.patch(url(f"/v1/messages/{MSG}")).respond(json=message(content={"type": "text", "text": "new"}))
    delete = mock.delete(url(f"/v1/messages/{MSG}")).respond(json=message(status="unsent"))
    assert flow.messages.retrieve(MSG).id == MSG
    edited = flow.messages.edit(MSG, "new")
    assert sent(patch) == {"content": {"type": "text", "text": "new"}}
    assert edited.content.text == "new"  # type: ignore[union-attr]
    flow.messages.edit(MSG, {"type": "text", "text": "dict", "format": "markdown"})
    assert sent(patch) == {"content": {"type": "text", "text": "dict", "format": "markdown"}}
    assert flow.messages.unsend(MSG).status == "unsent"
    assert get.called and delete.called


def test_path_ids_are_escaped(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.route(host="api.test").respond(json=message())
    flow.messages.retrieve("msg/../x?y#z")
    assert route.calls.last.request.url.raw_path == b"/v1/messages/msg%2F..%2Fx%3Fy%23z"
    flow.messages.send("conv x/1", "hi")
    assert route.calls.last.request.url.raw_path == b"/v1/conversations/conv%20x%2F1/messages"


# conversations ---------------------------------------------------------------


def test_conversations(flow: Flow, mock: respx.MockRouter) -> None:
    lst = mock.get(url("/v1/conversations")).respond(json=page([conversation()]))
    get = mock.get(url(f"/v1/conversations/{CONV}")).respond(json=conversation(window={"open": True}))
    msgs = mock.get(url(f"/v1/conversations/{CONV}/messages")).respond(json=page([message()]))
    p = flow.conversations.list(contact=CONTACT)
    assert isinstance(p.data[0], Conversation)
    assert lst.calls.last.request.url.params["contact"] == CONTACT
    c = flow.conversations.retrieve(CONV)
    assert c.id == CONV and get.called
    m = flow.conversations.messages(CONV, before="msg_z")
    assert isinstance(m.data[0], Message)
    assert msgs.calls.last.request.url.params["before"] == "msg_z"


def test_typing_and_mark_read(flow: Flow, mock: respx.MockRouter) -> None:
    typing = mock.post(url(f"/v1/conversations/{CONV}/typing")).respond(json=conversation_action("typing_on"))
    read = mock.post(url(f"/v1/conversations/{CONV}/read")).respond(json=conversation_action("read"))
    a = flow.conversations.typing(CONV)
    assert isinstance(a, ConversationAction) and a.action == "typing_on"
    assert sent(typing) == {"state": "on"}
    flow.conversations.typing(CONV, "off")
    assert sent(typing) == {"state": "off"}
    assert flow.conversations.mark_read(CONV).action == "read"
    assert sent(read) == {}
    flow.conversations.mark_read(CONV, MSG)
    assert sent(read) == {"up_to": MSG}


def test_capabilities(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/capabilities")).respond(json=capabilities())
    caps = flow.capabilities.retrieve(CONV)
    assert isinstance(caps, Capabilities)
    assert caps.window.open is True
    assert route.calls.last.request.url.params["conversation"] == CONV


# files -------------------------------------------------------------------------


def multipart(route: respx.Route) -> bytes:
    req = route.calls.last.request
    assert req.headers["content-type"].startswith("multipart/form-data; boundary=")
    return req.read()


def test_upload_bytes(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v1/files")).respond(201, json=file_obj())
    f = flow.files.upload(b"\x89PNG", filename="cat.png", channel="telegram")
    assert isinstance(f, File) and f.id == FILE
    raw = multipart(route)
    assert b'name="file"; filename="cat.png"' in raw
    assert b"\x89PNG" in raw
    assert b'name="filename"\r\n\r\ncat.png' in raw
    assert b'name="channel"\r\n\r\ntelegram' in raw
    assert "idempotency-key" in route.calls.last.request.headers


def test_upload_bytes_without_options(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v1/files")).respond(201, json=file_obj())
    flow.files.upload(b"data")
    raw = multipart(route)
    assert b'name="file"; filename="file"' in raw
    assert b'name="filename"\r\n' not in raw
    assert b'name="channel"' not in raw


def test_upload_path(flow: Flow, mock: respx.MockRouter, tmp_path: Path) -> None:
    p = tmp_path / "report.pdf"
    p.write_bytes(b"%PDF-1.7 body")
    route = mock.post(url("/v1/files")).respond(201, json=file_obj())
    flow.files.upload(p)
    raw = multipart(route)
    assert b'filename="report.pdf"' in raw
    assert b"%PDF-1.7 body" in raw
    flow.files.upload(str(p), filename="renamed.pdf")
    assert b'filename="renamed.pdf"' in multipart(route)


def test_upload_file_object(flow: Flow, mock: respx.MockRouter, tmp_path: Path) -> None:
    p = tmp_path / "voice.ogg"
    p.write_bytes(b"OggS")
    route = mock.post(url("/v1/files")).respond(201, json=file_obj())
    with p.open("rb") as fh:
        flow.files.upload(fh)
    raw = multipart(route)
    assert b'filename="voice.ogg"' in raw and b"OggS" in raw
    flow.files.upload(io.BytesIO(b"mem"))
    raw = multipart(route)
    assert b'filename="file"' in raw and b"mem" in raw


def test_upload_rejects_other_types(flow: Flow) -> None:
    with pytest.raises(TypeError):
        flow.files.upload(12345)


def test_download_200_returns_bytes(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v1/files/{FILE}")).respond(200, content=b"bytes!")
    assert flow.files.download(FILE) == b"bytes!"


def test_download_redirect_drops_authorization(flow: Flow, mock: respx.MockRouter) -> None:
    api = mock.get(url(f"/v1/files/{FILE}")).respond(
        302, headers={"Location": "https://files.test/signed/cat.png?sig=x"}
    )
    signed = mock.get("https://files.test/signed/cat.png").respond(200, content=b"signed bytes")
    assert flow.files.download(f"https://api.test/v1/files/{FILE}") == b"signed bytes"
    assert api.calls.last.request.headers["authorization"] == f"Bearer {KEY}"
    req = signed.calls.last.request
    assert "authorization" not in req.headers
    assert req.url.params["sig"] == "x"


def test_download_relative_redirect(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v1/files/{FILE}")).respond(307, headers={"Location": "/f/token/cat.png"})
    signed = mock.get(url("/f/token/cat.png")).respond(200, content=b"x")
    assert flow.files.download(FILE + "/") == b"x"
    assert "authorization" not in signed.calls.last.request.headers


def test_download_redirect_failure(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v1/files/{FILE}")).respond(302, headers={"Location": "https://files.test/gone"})
    mock.get("https://files.test/gone").respond(403)
    with pytest.raises(APIError) as e:
        flow.files.download(FILE)
    assert e.value.status == 403


def test_download_redirect_without_location(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v1/files/{FILE}")).respond(302)
    with pytest.raises(APIError, match="Location"):
        flow.files.download(FILE)


# senders, templates, webhook endpoints, contacts, app ------------------------------


def test_senders(flow: Flow, mock: respx.MockRouter) -> None:
    lst = mock.get(url("/v1/senders")).respond(json=page([sender()]))
    get = mock.get(url(f"/v1/senders/{SENDER}")).respond(json=sender())
    post = mock.post(url("/v1/senders")).respond(201, json=sender(kind="dedicated", status="pending"))
    delete = mock.delete(url(f"/v1/senders/{SENDER}")).respond(json=sender(status="banned"))
    p = flow.senders.list(channel="telegram", kind="shared")
    assert isinstance(p.data[0], Sender)
    assert lst.calls.last.request.url.params["kind"] == "shared"
    assert flow.senders.retrieve(SENDER).id == SENDER and get.called
    s = flow.senders.request(channel="telegram", telegram_bot_token="123:abc", display_name="Bot")
    assert s.kind == "dedicated"
    assert sent(post) == {"channel": "telegram", "telegram_bot_token": "123:abc", "display_name": "Bot"}
    assert flow.senders.disconnect(SENDER).status == "banned" and delete.called


def test_templates(flow: Flow, mock: respx.MockRouter) -> None:
    lst = mock.get(url("/v1/templates")).respond(json=page([template()]))
    post = mock.post(url("/v1/templates")).respond(201, json=template())
    get = mock.get(url(f"/v1/templates/{TPL}")).respond(json=template())
    delete = mock.delete(url(f"/v1/templates/{TPL}")).respond(json=deleted(TPL))
    p = flow.templates.list(sender=SENDER, status="approved")
    assert isinstance(p.data[0], Template)
    assert lst.calls.last.request.url.params["status"] == "approved"
    params = {
        "sender": SENDER,
        "name": "order_update",
        "language": "en",
        "category": "utility",
        "components": [{"type": "body", "text": "Your order {{1}} shipped."}],
    }
    assert flow.templates.create(params).id == TPL
    assert sent(post) == params
    assert "idempotency-key" in post.calls.last.request.headers
    assert flow.templates.retrieve(TPL).name == "order_update" and get.called
    d = flow.templates.delete(TPL)
    assert isinstance(d, Deleted) and d.deleted and delete.called


def test_webhook_endpoints(flow: Flow, mock: respx.MockRouter) -> None:
    post = mock.post(url("/v1/webhook_endpoints")).respond(201, json=webhook_endpoint(secret="whsec_x"))
    lst = mock.get(url("/v1/webhook_endpoints")).respond(json=page([webhook_endpoint()]))
    get = mock.get(url(f"/v1/webhook_endpoints/{WH}")).respond(json=webhook_endpoint())
    patch = mock.patch(url(f"/v1/webhook_endpoints/{WH}")).respond(json=webhook_endpoint(enabled=False))
    delete = mock.delete(url(f"/v1/webhook_endpoints/{WH}")).respond(json=deleted(WH))
    rotate = mock.post(url(f"/v1/webhook_endpoints/{WH}/rotate_secret")).respond(
        json=webhook_endpoint(secret="whsec_y")
    )

    created = flow.webhook_endpoints.create(url="https://example.test/hooks", events=("message.received",))
    assert isinstance(created, WebhookEndpoint) and created.secret == "whsec_x"
    assert sent(post) == {"url": "https://example.test/hooks", "events": ["message.received"]}
    flow.webhook_endpoints.create(url="https://example.test/hooks", events=["message.sent"], description="d")
    assert sent(post)["description"] == "d"
    assert isinstance(flow.webhook_endpoints.list(limit=5).data[0], WebhookEndpoint)
    assert lst.calls.last.request.url.params["limit"] == "5"
    assert flow.webhook_endpoints.retrieve(WH).id == WH and get.called
    updated = flow.webhook_endpoints.update(WH, enabled=False, events=["message.failed"])
    assert updated.enabled is False
    assert sent(patch) == {"enabled": False, "events": ["message.failed"]}
    assert "idempotency-key" not in patch.calls.last.request.headers
    flow.webhook_endpoints.update(WH, url="https://example.test/new")
    assert sent(patch) == {"url": "https://example.test/new"}
    assert flow.webhook_endpoints.delete(WH).deleted and delete.called
    assert flow.webhook_endpoints.rotate_secret(WH, overlap_seconds=0).secret == "whsec_y"
    assert sent(rotate) == {"overlap_seconds": 0}
    flow.webhook_endpoints.rotate_secret(WH)
    assert sent(rotate) == {}


def test_contacts(flow: Flow, mock: respx.MockRouter) -> None:
    lst = mock.get(url("/v1/contacts")).respond(json=page([contact()]))
    get = mock.get(url(f"/v1/contacts/{CONTACT}")).respond(json=contact())
    delete = mock.delete(url(f"/v1/contacts/{CONTACT}")).respond(204)
    p = flow.contacts.list(channel="whatsapp")
    assert isinstance(p.data[0], Contact)
    assert lst.calls.last.request.url.params["channel"] == "whatsapp"
    assert flow.contacts.retrieve(CONTACT).id == CONTACT and get.called
    assert flow.contacts.delete(CONTACT) is None
    assert delete.called


def test_app_retrieve(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url("/v1/app")).respond(json=app_context())
    ctx = flow.app.retrieve()
    assert isinstance(ctx, AppContext)
    assert ctx.api_key.mode == "test"


def test_events_retrieve(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v1/events/{evt(1)}")).respond(json=event_received(evt(1), "yo"))
    e = flow.events.retrieve(evt(1))
    assert isinstance(e, MessageReceivedEvent)
    assert e.data.message.content.text == "yo"  # type: ignore[union-attr]


# testing ---------------------------------------------------------------------------


def test_simulated_conversation(flow: Flow, mock: respx.MockRouter) -> None:
    create = mock.post(url("/v1/test/conversations")).respond(201, json=conversation(simulated=True))
    inbound = mock.post(url(f"/v1/test/conversations/{CONV}/inbound")).respond(201, json=simulated_inbound())
    transcript = mock.get(url(f"/v1/test/conversations/{CONV}/transcript"))
    m2 = message("msg_01JB8ZD4M6P8R0T2V4X6Z80002", shown={"type": "text", "text": "Hi"})
    transcript.side_effect = [
        httpx.Response(200, json=page([message(direction="in", status="received")], True)),
        httpx.Response(200, json=page([m2], False)),
    ]
    c = flow.test.create_conversation("telegram", contact={"username": "ada"}, name="Ada")
    assert isinstance(c, Conversation)
    assert sent(create) == {"channel": "telegram", "contact": {"username": "ada"}, "name": "Ada"}
    flow.test.create_conversation("sms")
    assert sent(create) == {"channel": "sms"}
    r = flow.test.inbound(CONV, "Hello agent", reply_to=MSG)
    assert isinstance(r, SimulatedInbound) and r.message == MSG
    assert sent(inbound) == {"content": {"type": "text", "text": "Hello agent"}, "reply_to": MSG}
    flow.test.inbound(CONV, {"type": "media", "kind": "image", "file_id": FILE})
    assert sent(inbound) == {"content": {"type": "media", "kind": "image", "file_id": FILE}}
    entries = list(flow.test.transcript(CONV, limit=1))
    assert all(isinstance(e, TranscriptEntry) for e in entries)
    assert [e.direction for e in entries] == ["in", "out"]
    assert transcript.calls[1].request.url.params["after"] == MSG
    assert transcript.calls[1].request.url.params["limit"] == "1"
