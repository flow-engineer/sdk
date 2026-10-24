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

from flow_messaging import APIError, Flow, UnsupportedContentError
from flow_messaging.content import buttons, image, list_message, location
from flow_messaging.content import template as template_kind
from flow_messaging.types import (
    AppContext,
    BasicMessage,
    Contact,
    Conversation,
    ConversationAction,
    Deleted,
    EditMessageRequest,
    File,
    Message,
    MessageReceivedEvent,
    ReadMessage,
    Sender,
    SimulatedInbound,
    Template,
    TranscriptEntry,
    WebhookEndpoint,
)


def sent(route: respx.Route) -> Any:
    return json.loads(route.calls.last.request.read())


# messages ---------------------------------------------------------------------

#: Each kind sent with POST /v0/conversations/{id}/<path>: the method, its path, and a body.
KINDS: list[tuple[str, str, dict[str, Any]]] = [
    ("basic", "basic", {"text": "Hello"}),
    ("voice", "voice", {"file_id": FILE}),
    ("buttons", "buttons", {"text": "Size?", "buttons": [{"id": "s", "label": "S"}]}),
    ("list", "list", {"text": "Size?", "button": "Sizes", "sections": [{"rows": [{"id": "s", "title": "S"}]}]}),
    ("carousel", "carousel", {"text": "Picks", "cards": []}),
    ("template", "template", {"template_id": TPL, "language": "en"}),
    ("contact_card", "contact-card", {"name": "Ada", "phones": ["+15555550100"]}),
    ("location", "location", {"lat": 52.52, "lng": 13.405}),
    ("effect", "effect", {"text": "Party!", "effect": "confetti"}),
    ("reaction", "reaction", {"message_id": MSG, "emoji": None}),
]


@pytest.mark.parametrize(("method", "path", "fields"), KINDS)
def test_each_kind_method_posts_to_its_endpoint(
    method: str, path: str, fields: dict[str, Any], flow: Flow, mock: respx.MockRouter
) -> None:
    route = mock.post(url(f"/v0/conversations/{CONV}/{path}")).respond(json=message())
    msg = getattr(flow.messages, method)(CONV, fields, idempotency_key="evt_1:0")
    assert isinstance(msg, Message)
    assert sent(route) == fields
    assert route.calls.last.request.headers["idempotency-key"] == "evt_1:0"
    # Keyword fields are laid over the message, and a matching kind is kept.
    getattr(flow.messages, method)(CONV, {"kind": path.replace("-", "_"), **fields}, metadata={"k": "v"})
    assert sent(route) == {"kind": path.replace("-", "_"), **fields, "metadata": {"k": "v"}}


def test_kind_method_refuses_another_kind(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.route(host="api.test").respond(json=message())
    with pytest.raises(ValueError, match=r"messages\.send"):
        flow.messages.basic(CONV, buttons("Size?", ["S"]))
    assert not route.called


def test_basic_with_keyword_fields_and_builders(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v0/conversations/{CONV}/basic")).respond(json=message())
    flow.messages.basic(CONV, text="See https://example.test", link_preview=False, reply_to=MSG)
    assert sent(route) == {"text": "See https://example.test", "link_preview": False, "reply_to": MSG}
    flow.messages.basic(CONV, image(FILE, "Your receipt"))
    assert sent(route) == {"kind": "basic", "text": "Your receipt", "media": {"type": "image", "file_id": FILE}}
    flow.messages.basic(CONV, BasicMessage(text="model"))
    assert sent(route) == {"kind": "basic", "text": "model"}


@pytest.mark.parametrize(("method", "path", "fields"), KINDS)
def test_send_routes_each_kind_to_its_endpoint(
    method: str, path: str, fields: dict[str, Any], flow: Flow, mock: respx.MockRouter
) -> None:
    route = mock.post(url(f"/v0/conversations/{CONV}/{path}")).respond(json=message())
    kind = {"kind": method, **fields}
    msg = flow.messages.send(CONV, kind, idempotency_key="evt_1:card:2")
    assert isinstance(msg, Message)
    assert sent(route) == kind
    assert route.calls.last.request.headers["idempotency-key"] == "evt_1:card:2"


def test_send_string_is_basic_text(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v0/conversations/{CONV}/basic")).respond(json=message())
    msg = flow.messages.send(CONV, "Hello")
    assert isinstance(msg, Message) and msg.id == MSG
    assert isinstance(msg.content, BasicMessage)
    assert sent(route) == {"kind": "basic", "text": "Hello"}


def test_send_builders_and_models(flow: Flow, mock: respx.MockRouter) -> None:
    b = mock.post(url(f"/v0/conversations/{CONV}/buttons")).respond(json=message())
    flow.messages.send(CONV, buttons("Size?", ["S", "M"]))
    assert sent(b) == {
        "kind": "buttons",
        "text": "Size?",
        "buttons": [{"id": "S", "label": "S"}, {"id": "M", "label": "M"}],
    }
    lst = mock.post(url(f"/v0/conversations/{CONV}/list")).respond(json=message())
    flow.messages.send(CONV, list_message("Size?", "Sizes", [{"id": "s", "title": "S"}]))
    assert sent(lst)["sections"] == [{"rows": [{"id": "s", "title": "S"}]}]
    # A model keeps its kind even when it was left at its default, and only the fields set.
    basic = mock.post(url(f"/v0/conversations/{CONV}/basic")).respond(json=message())
    flow.messages.send(CONV, BasicMessage(text="Hi"))
    assert sent(basic) == {"kind": "basic", "text": "Hi"}


def test_send_typing_and_read_answer_conversation_actions(flow: Flow, mock: respx.MockRouter) -> None:
    typing = mock.post(url(f"/v0/conversations/{CONV}/typing")).respond(json=conversation_action("typing"))
    read = mock.post(url(f"/v0/conversations/{CONV}/read")).respond(json=conversation_action("read"))
    a = flow.messages.send(CONV, {"kind": "typing"})
    assert isinstance(a, ConversationAction) and a.action == "typing"
    assert sent(typing) == {"kind": "typing"}
    r = flow.messages.send(CONV, ReadMessage(up_to=MSG), idempotency_key="evt_1:read")
    assert isinstance(r, ConversationAction) and r.action == "read"
    assert sent(read) == {"kind": "read", "up_to": MSG}
    assert read.calls.last.request.headers["idempotency-key"] == "evt_1:read"


def test_send_edit_and_unsend_patch_and_delete(flow: Flow, mock: respx.MockRouter) -> None:
    patch = mock.patch(url(f"/v0/messages/{MSG}")).respond(json=message())
    delete = mock.delete(url(f"/v0/messages/{MSG}")).respond(json=message(status="unsent"))
    posts = mock.post(host="api.test").respond(json=message())
    flow.messages.send(CONV, {"kind": "edit", "message_id": MSG, "text": "fixed", "telegram": {"parse_mode": "HTML"}})
    assert sent(patch) == {"text": "fixed", "telegram": {"parse_mode": "HTML"}}
    assert flow.messages.send(CONV, {"kind": "unsend", "message_id": MSG}).status == "unsent"
    assert delete.called and not posts.called
    with pytest.raises(ValueError, match="message_id"):
        flow.messages.send(CONV, {"kind": "edit", "text": "no target"})


@pytest.mark.parametrize(
    "bad",
    [
        {"text": "no kind"},
        {"type": "text", "text": "the old shape"},
        {"kind": "hologram"},
        {"kind": "button_reply", "button_id": "s", "label": "S"},
        {"kind": "file_blocked", "reason": "malware"},
        None,
    ],
)
def test_send_refuses_a_missing_or_unknown_kind_before_any_request(
    bad: Any, flow: Flow, mock: respx.MockRouter
) -> None:
    route = mock.route(host="api.test").respond(json=message())
    with pytest.raises(ValueError):
        flow.messages.send(CONV, bad)
    assert not route.called


@pytest.mark.parametrize(
    ("to", "expected"),
    [
        (CONTACT, {"contact": CONTACT}),
        ("+15555550100", {"phone": "+15555550100"}),
        ({"telegram_user_id": "42"}, {"telegram_user_id": "42"}),
    ],
)
def test_start_is_one_flat_body(to: Any, expected: dict[str, str], flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v0/messages")).respond(201, json=message())
    flow.messages.start(sender=SENDER, to=to, message="Hi", consent={"method": "web_form"})
    assert sent(route) == {
        "sender": SENDER,
        "to": expected,
        "consent": {"method": "web_form"},
        "kind": "basic",
        "text": "Hi",
    }


def test_start_template_and_keyword_fields(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v0/messages")).respond(201, json=message())
    flow.messages.start(
        sender=SENDER, to=CONTACT, message=template_kind(TPL, "en", {"body": ["42"]}), idempotency_key="k1"
    )
    assert sent(route) == {
        "sender": SENDER,
        "to": {"contact": CONTACT},
        "kind": "template",
        "template_id": TPL,
        "language": "en",
        "params": {"body": ["42"]},
    }
    assert route.calls.last.request.headers["idempotency-key"] == "k1"
    flow.messages.start(sender=SENDER, to=CONTACT, kind="basic", text="Your table is ready.", link_preview=False)
    assert sent(route) == {
        "sender": SENDER,
        "to": {"contact": CONTACT},
        "kind": "basic",
        "text": "Your table is ready.",
        "link_preview": False,
    }


@pytest.mark.parametrize("message_", [{"text": "no kind"}, buttons("Size?", ["S"]), None])
def test_start_refuses_kinds_other_than_basic_and_template(message_: Any, flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.route(host="api.test").respond(201, json=message())
    with pytest.raises(ValueError, match="basic"):
        flow.messages.start(sender=SENDER, to=CONTACT, message=message_)
    assert not route.called


def test_start_bad_string_raises_value_error(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v0/messages")).respond(201, json=message())
    with pytest.raises(ValueError, match="contact ID"):
        flow.messages.start(sender=SENDER, to="someone@example.com", message="Hi")
    assert not route.called


def test_retrieve_edit_unsend(flow: Flow, mock: respx.MockRouter) -> None:
    get = mock.get(url(f"/v0/messages/{MSG}")).respond(json=message())
    patch = mock.patch(url(f"/v0/messages/{MSG}")).respond(json=message(content={"kind": "basic", "text": "new"}))
    delete = mock.delete(url(f"/v0/messages/{MSG}")).respond(json=message(status="unsent"))
    assert flow.messages.retrieve(MSG).id == MSG and get.called
    flow.messages.edit(MSG, "new")
    assert sent(patch) == {"text": "new"}
    flow.messages.edit(MSG, text="kw", imessage={"styles": []})
    assert sent(patch) == {"text": "kw", "imessage": {"styles": []}}
    flow.messages.edit(MSG, EditMessageRequest(text="model"))
    assert sent(patch) == {"text": "model"}
    assert "idempotency-key" not in patch.calls.last.request.headers
    assert flow.messages.unsend(MSG).status == "unsent"
    assert delete.called


def test_unsupported_content_carries_param_and_hint(flow: Flow, mock: respx.MockRouter) -> None:
    mock.post(url(f"/v0/conversations/{CONV}/carousel")).respond(
        422,
        json={
            "error": {
                "type": "unsupported_content",
                "message": "Telegram has no carousels.",
                "param": "kind",
                "hint": "Send each card as a basic message.",
            }
        },
    )
    with pytest.raises(UnsupportedContentError) as caught:
        flow.messages.carousel(CONV, {"text": "Picks", "cards": []}, idempotency_key="evt_1:card")
    assert caught.value.param == "kind"
    assert caught.value.hint == "Send each card as a basic message."


def test_path_ids_are_escaped(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.route(host="api.test").respond(json=message())
    flow.messages.retrieve("msg/../x?y#z")
    assert route.calls.last.request.url.raw_path == b"/v0/messages/msg%2F..%2Fx%3Fy%23z"
    flow.messages.send("conv x/1", "hi")
    assert route.calls.last.request.url.raw_path == b"/v0/conversations/conv%20x%2F1/basic"


# conversations ---------------------------------------------------------------


def test_conversations(flow: Flow, mock: respx.MockRouter) -> None:
    lst = mock.get(url("/v0/conversations")).respond(json=page([conversation()]))
    get = mock.get(url(f"/v0/conversations/{CONV}")).respond(json=conversation(window={"open": True}))
    msgs = mock.get(url(f"/v0/conversations/{CONV}/messages")).respond(json=page([message()]))
    p = flow.conversations.list(contact=CONTACT)
    assert isinstance(p.data[0], Conversation)
    assert lst.calls.last.request.url.params["contact"] == CONTACT
    c = flow.conversations.retrieve(CONV)
    assert c.id == CONV and get.called
    m = flow.conversations.messages(CONV, before="msg_z")
    assert isinstance(m.data[0], Message)
    assert msgs.calls.last.request.url.params["before"] == "msg_z"


def test_typing_and_read(flow: Flow, mock: respx.MockRouter) -> None:
    typing = mock.post(url(f"/v0/conversations/{CONV}/typing")).respond(json=conversation_action("typing"))
    read = mock.post(url(f"/v0/conversations/{CONV}/read")).respond(json=conversation_action("read"))
    a = flow.conversations.typing(CONV)
    assert isinstance(a, ConversationAction) and a.action == "typing"
    assert sent(typing) == {}
    assert "state" not in sent(typing)
    flow.conversations.typing(CONV, imessage={"duration_seconds": 10}, idempotency_key="evt_1:typing")
    assert sent(typing) == {"imessage": {"duration_seconds": 10}}
    assert typing.calls.last.request.headers["idempotency-key"] == "evt_1:typing"
    assert flow.conversations.read(CONV).action == "read"
    assert sent(read) == {}
    flow.conversations.read(CONV, MSG)
    assert sent(read) == {"up_to": MSG}
    flow.conversations.read(CONV, up_to=MSG)
    assert sent(read) == {"up_to": MSG}
    assert not hasattr(flow.conversations, "mark_read")


def test_no_capabilities_resource(flow: Flow) -> None:
    assert not hasattr(flow, "capabilities")


# files -------------------------------------------------------------------------


def multipart(route: respx.Route) -> bytes:
    req = route.calls.last.request
    assert req.headers["content-type"].startswith("multipart/form-data; boundary=")
    return req.read()


def test_upload_bytes(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v0/files")).respond(201, json=file_obj())
    f = flow.files.upload(b"\x89PNG", filename="cat.png", channel="telegram")
    assert isinstance(f, File) and f.id == FILE
    raw = multipart(route)
    assert b'name="file"; filename="cat.png"' in raw
    assert b"\x89PNG" in raw
    assert b'name="filename"\r\n\r\ncat.png' in raw
    assert b'name="channel"\r\n\r\ntelegram' in raw
    assert "idempotency-key" in route.calls.last.request.headers


def test_upload_bytes_without_options(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v0/files")).respond(201, json=file_obj())
    flow.files.upload(b"data")
    raw = multipart(route)
    assert b'name="file"; filename="file"' in raw
    assert b'name="filename"\r\n' not in raw
    assert b'name="channel"' not in raw


def test_upload_path(flow: Flow, mock: respx.MockRouter, tmp_path: Path) -> None:
    p = tmp_path / "report.pdf"
    p.write_bytes(b"%PDF-1.7 body")
    route = mock.post(url("/v0/files")).respond(201, json=file_obj())
    flow.files.upload(p)
    raw = multipart(route)
    assert b'filename="report.pdf"' in raw
    assert b"%PDF-1.7 body" in raw
    flow.files.upload(str(p), filename="renamed.pdf")
    assert b'filename="renamed.pdf"' in multipart(route)


def test_upload_file_object(flow: Flow, mock: respx.MockRouter, tmp_path: Path) -> None:
    p = tmp_path / "voice.ogg"
    p.write_bytes(b"OggS")
    route = mock.post(url("/v0/files")).respond(201, json=file_obj())
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
    mock.get(url(f"/v0/files/{FILE}")).respond(200, content=b"bytes!")
    assert flow.files.download(FILE) == b"bytes!"


def test_download_redirect_drops_authorization(flow: Flow, mock: respx.MockRouter) -> None:
    api = mock.get(url(f"/v0/files/{FILE}")).respond(
        302, headers={"Location": "https://files.test/signed/cat.png?sig=x"}
    )
    signed = mock.get("https://files.test/signed/cat.png").respond(200, content=b"signed bytes")
    assert flow.files.download(f"https://api.test/v0/files/{FILE}") == b"signed bytes"
    assert api.calls.last.request.headers["authorization"] == f"Bearer {KEY}"
    req = signed.calls.last.request
    assert "authorization" not in req.headers
    assert req.url.params["sig"] == "x"


def test_download_relative_redirect(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v0/files/{FILE}")).respond(307, headers={"Location": "/f/token/cat.png"})
    signed = mock.get(url("/f/token/cat.png")).respond(200, content=b"x")
    assert flow.files.download(FILE + "/") == b"x"
    assert "authorization" not in signed.calls.last.request.headers


def test_download_redirect_failure(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v0/files/{FILE}")).respond(302, headers={"Location": "https://files.test/gone"})
    mock.get("https://files.test/gone").respond(403)
    with pytest.raises(APIError) as e:
        flow.files.download(FILE)
    assert e.value.status == 403


def test_download_redirect_without_location(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v0/files/{FILE}")).respond(302)
    with pytest.raises(APIError, match="Location"):
        flow.files.download(FILE)


# senders, templates, webhook endpoints, contacts, app ------------------------------


def test_senders(flow: Flow, mock: respx.MockRouter) -> None:
    lst = mock.get(url("/v0/senders")).respond(json=page([sender()]))
    get = mock.get(url(f"/v0/senders/{SENDER}")).respond(json=sender())
    post = mock.post(url("/v0/senders")).respond(201, json=sender(kind="dedicated", status="pending"))
    delete = mock.delete(url(f"/v0/senders/{SENDER}")).respond(json=sender(status="banned"))
    p = flow.senders.list(channel="telegram", kind="shared")
    assert isinstance(p.data[0], Sender)
    assert lst.calls.last.request.url.params["kind"] == "shared"
    assert flow.senders.retrieve(SENDER).id == SENDER and get.called
    s = flow.senders.request(channel="telegram", telegram_bot_token="123:abc", display_name="Bot")
    assert s.kind == "dedicated"
    assert sent(post) == {"channel": "telegram", "telegram_bot_token": "123:abc", "display_name": "Bot"}
    assert flow.senders.disconnect(SENDER).status == "banned" and delete.called


def test_templates(flow: Flow, mock: respx.MockRouter) -> None:
    lst = mock.get(url("/v0/templates")).respond(json=page([template()]))
    post = mock.post(url("/v0/templates")).respond(201, json=template())
    get = mock.get(url(f"/v0/templates/{TPL}")).respond(json=template())
    delete = mock.delete(url(f"/v0/templates/{TPL}")).respond(json=deleted(TPL))
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
    post = mock.post(url("/v0/webhook_endpoints")).respond(201, json=webhook_endpoint(secret="whsec_x"))
    lst = mock.get(url("/v0/webhook_endpoints")).respond(json=page([webhook_endpoint()]))
    get = mock.get(url(f"/v0/webhook_endpoints/{WH}")).respond(json=webhook_endpoint())
    patch = mock.patch(url(f"/v0/webhook_endpoints/{WH}")).respond(json=webhook_endpoint(enabled=False))
    delete = mock.delete(url(f"/v0/webhook_endpoints/{WH}")).respond(json=deleted(WH))
    rotate = mock.post(url(f"/v0/webhook_endpoints/{WH}/rotate_secret")).respond(
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
    lst = mock.get(url("/v0/contacts")).respond(json=page([contact()]))
    get = mock.get(url(f"/v0/contacts/{CONTACT}")).respond(json=contact())
    delete = mock.delete(url(f"/v0/contacts/{CONTACT}")).respond(204)
    p = flow.contacts.list(channel="whatsapp")
    assert isinstance(p.data[0], Contact)
    assert lst.calls.last.request.url.params["channel"] == "whatsapp"
    assert flow.contacts.retrieve(CONTACT).id == CONTACT and get.called
    assert flow.contacts.delete(CONTACT) is None
    assert delete.called


def test_app_retrieve(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url("/v0/app")).respond(json=app_context())
    ctx = flow.app.retrieve()
    assert isinstance(ctx, AppContext)
    assert ctx.api_key.mode == "test"


def test_events_retrieve(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v0/events/{evt(1)}")).respond(json=event_received(evt(1), "yo"))
    e = flow.events.retrieve(evt(1))
    assert isinstance(e, MessageReceivedEvent)
    assert e.data.message.content.text == "yo"  # type: ignore[union-attr]


# testing ---------------------------------------------------------------------------


def test_simulated_conversation(flow: Flow, mock: respx.MockRouter) -> None:
    create = mock.post(url("/v0/test/conversations")).respond(201, json=conversation(simulated=True))
    inbound = mock.post(url(f"/v0/test/conversations/{CONV}/inbound")).respond(201, json=simulated_inbound())
    transcript = mock.get(url(f"/v0/test/conversations/{CONV}/transcript"))
    m2 = message("msg_01JB8ZD4M6P8R0T2V4X6Z80002")
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
    assert sent(inbound) == {"content": {"kind": "basic", "text": "Hello agent"}, "reply_to": MSG}
    flow.test.inbound(CONV, image(FILE))
    assert sent(inbound) == {"content": {"kind": "basic", "media": {"type": "image", "file_id": FILE}}}
    flow.test.inbound(CONV, {"kind": "button_reply", "message_id": MSG, "button_id": "s"})
    assert sent(inbound) == {"content": {"kind": "button_reply", "message_id": MSG, "button_id": "s"}}
    flow.test.inbound(CONV, location(52.52, 13.405))
    assert sent(inbound) == {"content": {"kind": "location", "lat": 52.52, "lng": 13.405}}
    entries = list(flow.test.transcript(CONV, limit=1))
    assert all(isinstance(e, TranscriptEntry) for e in entries)
    assert [e.direction for e in entries] == ["in", "out"]
    assert transcript.calls[1].request.url.params["after"] == MSG
    assert transcript.calls[1].request.url.params["limit"] == "1"
