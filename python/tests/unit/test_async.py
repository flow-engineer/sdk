"""AsyncFlow: the async code paths (requests, retries, pagination, files, device flow,
handles, options and the async context manager)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from conftest import (
    BASE,
    CONV,
    FILE,
    KEY,
    MSG,
    conversation,
    conversation_action,
    device_authorization,
    device_token,
    error,
    file_obj,
    message,
    page,
    sandbox_key,
    ulid,
    url,
)

from flow_messaging import (
    API_VERSION,
    APIConnectionError,
    APITimeoutError,
    AsyncConversationHandle,
    AsyncFlow,
    AsyncPage,
    AsyncPager,
    AuthenticationError,
    ChannelError,
    DeviceSignInError,
    NewContactLimitError,
    RateLimitError,
)
from flow_messaging.types import Conversation, Message

C = [ulid("conv", n) for n in range(1, 6)]
SEND = url(f"/v0/conversations/{CONV}/basic")


def paged(route: respx.Route) -> None:
    pages = {None: ([C[0], C[1]], True), C[1]: ([C[2], C[3]], True), C[3]: ([C[4]], False)}

    def answer(request: httpx.Request) -> httpx.Response:
        ids, more = pages[request.url.params.get("after")]
        return httpx.Response(200, json=page([conversation(i) for i in ids], more))

    route.side_effect = answer


async def test_env_and_headers(monkeypatch: pytest.MonkeyPatch, mock: respx.MockRouter) -> None:
    monkeypatch.setenv("FLOW_MESSAGING_KEY", "fk_test_env")
    monkeypatch.setenv("FLOW_MESSAGING_BASE_URL", "https://env.test/")
    route = mock.post(f"https://env.test/v0/conversations/{CONV}/basic").respond(json=message())
    async with AsyncFlow() as aflow:
        assert aflow.base_url == "https://env.test"
        assert aflow.test_mode
        msg = await aflow.messages.send(CONV, "hi")
    assert isinstance(msg, Message)
    h = route.calls.last.request.headers
    assert h["authorization"] == "Bearer fk_test_env"
    assert h["flow-version"] == API_VERSION
    assert h["user-agent"].startswith("flow-messaging-python/")
    assert h["idempotency-key"]
    assert json.loads(route.calls.last.request.read()) == {"kind": "basic", "text": "hi"}


async def test_no_flow_version(mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(json=message())
    async with AsyncFlow(KEY, base_url=BASE, flow_version=None) as aflow:
        await aflow.messages.retrieve(MSG)
    assert "flow-version" not in route.calls.last.request.headers
    assert "idempotency-key" not in route.calls.last.request.headers


async def test_without_key_raises_before_request(mock: respx.MockRouter) -> None:
    route = mock.route(host="api.test").respond(json=message())
    async with AsyncFlow(base_url=BASE) as aflow:
        with pytest.raises(AuthenticationError):
            await aflow.messages.send(CONV, "hi")
        with pytest.raises(AuthenticationError):
            await aflow.conversations.list()
    assert not route.called


async def test_keyless_calls(mock: respx.MockRouter) -> None:
    keys = mock.post(url("/v0/sandbox/keys")).respond(201, json=sandbox_key())
    auth = mock.post(url("/v0/device/authorizations")).respond(json=device_authorization())
    async with AsyncFlow(base_url=BASE) as aflow:
        assert (await aflow.sandbox.create_key()).key == KEY
        await aflow.device.authorize(claim_token="fct_x")
    for route in (keys, auth):
        assert "authorization" not in route.calls.last.request.headers
        assert "idempotency-key" not in route.calls.last.request.headers


async def test_retries_rate_limited_and_5xx_with_same_key(
    aflow: AsyncFlow, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.post(SEND)
    route.side_effect = [
        httpx.Response(429, json=error("rate_limited", retry_after=2)),
        httpx.Response(503, json=error("api_error")),
        httpx.ConnectError("refused"),
        httpx.Response(200, json=message()),
    ]
    async with AsyncFlow(KEY, base_url=BASE, max_retries=3) as client:
        client._http._sleep = aflow._http._sleep
        await client.messages.send(CONV, "hi", idempotency_key="k")
    assert route.call_count == 4
    assert sleeps[0] == 2.0 and len(sleeps) == 3
    assert {c.request.headers["idempotency-key"] for c in route.calls} == {"k"}


async def test_not_retried(aflow: AsyncFlow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(SEND)
    route.side_effect = [
        httpx.Response(502, json=error("channel_error")),
        httpx.Response(429, json=error("new_contact_limit", retry_after=5)),
        httpx.Response(429, json=error("rate_limited", retry_after=120)),
    ]
    with pytest.raises(ChannelError):
        await aflow.messages.send(CONV, "a")
    with pytest.raises(NewContactLimitError):
        await aflow.messages.send(CONV, "b")
    with pytest.raises(RateLimitError):
        await aflow.messages.send(CONV, "c")
    assert route.call_count == 3
    assert sleeps == []


async def test_connection_and_timeout_errors(aflow: AsyncFlow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    conn = mock.get(url(f"/v0/messages/{MSG}")).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(APIConnectionError) as e:
        await aflow.messages.retrieve(MSG)
    assert not isinstance(e.value, APITimeoutError)
    assert conn.call_count == 3
    slow = mock.get(url("/v0/app")).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(APITimeoutError):
        await aflow.app.retrieve()
    assert slow.call_count == 3
    assert len(sleeps) == 4


async def test_await_list_gives_one_page(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v0/conversations"))
    paged(route)
    pager = aflow.conversations.list(limit=2, channel="telegram")
    assert isinstance(pager, AsyncPager)
    assert route.call_count == 0  # lazy until awaited or iterated
    first = await pager
    assert isinstance(first, AsyncPage)
    assert [c.id for c in first.data] == C[:2]
    assert first.has_more
    assert route.call_count == 1
    second = await first.next_page()
    assert second is not None and [c.id for c in second.data] == C[2:4]
    assert route.calls.last.request.url.params["after"] == C[1]
    assert route.calls.last.request.url.params["channel"] == "telegram"
    third = await second.next_page()
    assert third is not None and await third.next_page() is None
    assert "items" in repr(first)


async def test_async_for_walks_every_page(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v0/conversations"))
    paged(route)
    ids = [c.id async for c in aflow.conversations.list(before="conv_z")]
    assert ids == C
    assert [c.request.url.params.get("after") for c in route.calls] == [None, C[1], C[3]]
    assert all(c.request.url.params["before"] == "conv_z" for c in route.calls)
    page1 = await aflow.conversations.list()
    assert [c.id async for c in page1] == C
    assert [len(p.data) async for p in page1.iter_pages()] == [2, 2, 1]


async def test_to_list(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v0/conversations"))
    paged(route)
    items = await aflow.conversations.list().to_list(3)
    assert all(isinstance(c, Conversation) for c in items)
    assert [c.id for c in items] == C[:3]
    assert route.call_count == 2
    assert [c.id for c in await (await aflow.conversations.list()).to_list()] == C


async def test_events_list_type_repeated(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v0/events")).respond(json=page([]))
    await aflow.events.list(type=["message.received", "message.sent"])
    assert route.calls.last.request.url.params.get_list("type") == ["message.received", "message.sent"]


async def test_resources_round_trip(aflow: AsyncFlow, mock: respx.MockRouter, tmp_path: Path) -> None:
    start = mock.post(url("/v0/messages")).respond(201, json=message())
    edit = mock.patch(url(f"/v0/messages/{MSG}")).respond(json=message())
    unsend = mock.delete(url(f"/v0/messages/{MSG}")).respond(json=message(status="unsent"))
    upload = mock.post(url("/v0/files")).respond(201, json=file_obj())
    contact = mock.delete(url("/v0/contacts/ct_x")).respond(204)
    await aflow.messages.start(sender="snd_x", to="+15555550100", message="hi")
    assert json.loads(start.calls.last.request.read()) == {
        "sender": "snd_x",
        "to": {"phone": "+15555550100"},
        "kind": "basic",
        "text": "hi",
    }
    with pytest.raises(ValueError):
        await aflow.messages.start(sender="snd_x", to="ada", message="hi")
    await aflow.messages.edit(MSG, "new")
    assert json.loads(edit.calls.last.request.read()) == {"text": "new"}
    assert (await aflow.messages.unsend(MSG)).status == "unsent" and unsend.called
    p = tmp_path / "pic.png"
    p.write_bytes(b"\x89PNG")
    assert (await aflow.files.upload(p, channel="whatsapp")).id == FILE
    raw = upload.calls.last.request.read()
    assert b'filename="pic.png"' in raw and b'name="channel"\r\n\r\nwhatsapp' in raw
    assert await aflow.contacts.delete("ct_x") is None and contact.called


async def test_download_redirect_without_authorization(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    api = mock.get(url(f"/v0/files/{FILE}")).respond(302, headers={"Location": "https://files.test/s?sig=1"})
    signed = mock.get("https://files.test/s").respond(200, content=b"async bytes")
    assert await aflow.files.download(f"{BASE}/v0/files/{FILE}") == b"async bytes"
    assert api.calls.last.request.headers["authorization"] == f"Bearer {KEY}"
    assert "authorization" not in signed.calls.last.request.headers
    mock.get(url("/v0/files/file_direct")).respond(200, content=b"direct")
    assert await aflow.files.download("file_direct") == b"direct"


async def test_device_wait_for_key(aflow: AsyncFlow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(url("/v0/device/token"))
    route.side_effect = [
        httpx.Response(200, json=device_token("pending", 5)),
        httpx.Response(429, json=error("rate_limited", retry_after=20)),
        httpx.Response(503, json=error("api_error")),
        httpx.ConnectError("down"),
        httpx.Response(200, json=device_token("pending", 8)),
        httpx.Response(200, json=device_token("approved", 8, key="fk_test_new")),
    ]
    tok = await aflow.device.wait_for_key("dc_x", interval=5)
    assert tok.key == "fk_test_new"
    # 5; pending -> 5; 429 -> interval 10, wait 20; failure -> 10; failure -> 10; pending(8) -> 10.
    assert sleeps == [5, 5, 20, 10, 10, 10]


async def test_device_denied_and_failures(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    route = mock.post(url("/v0/device/token"))
    route.side_effect = [httpx.Response(200, json=device_token("denied"))]
    with pytest.raises(DeviceSignInError) as e:
        await aflow.device.wait_for_key("dc_x")
    assert e.value.reason == "denied"
    route.side_effect = [httpx.ConnectError("down")] * 5
    with pytest.raises(APIConnectionError):
        await aflow.device.wait_for_key("dc_x")


async def test_device_bearer_for_test_key_only(mock: respx.MockRouter) -> None:
    route = mock.post(url("/v0/device/authorizations")).respond(json=device_authorization())
    async with AsyncFlow(KEY, base_url=BASE) as aflow:
        await aflow.device.authorize()
        assert route.calls.last.request.headers["authorization"] == f"Bearer {KEY}"
        await aflow.device.authorize(claim_token="fct_x")
        assert "authorization" not in route.calls.last.request.headers
    async with AsyncFlow("fk_live_x", base_url=BASE) as aflow:
        await aflow.device.authorize()
        assert "authorization" not in route.calls.last.request.headers


async def test_sign_in(mock: respx.MockRouter, sleeps: list[float]) -> None:
    mock.post(url("/v0/device/authorizations")).respond(json=device_authorization(interval=3))
    mock.post(url("/v0/device/token")).respond(json=device_token("approved", 3, key="fk_test_new"))
    prompts: list[str] = []
    async with AsyncFlow(base_url=BASE) as aflow:

        async def fake(seconds: float) -> None:
            sleeps.append(seconds)

        aflow._http._sleep = fake
        tok = await aflow.device.sign_in(lambda a: prompts.append(a.user_code))
    assert tok.key == "fk_test_new"
    assert prompts == ["ABCD-EFGH"]
    assert sleeps == [3]


async def test_conversation_handle(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    send = mock.post(SEND).respond(json=message())
    react = mock.post(url(f"/v0/conversations/{CONV}/reaction")).respond(json=message())
    typing = mock.post(url(f"/v0/conversations/{CONV}/typing")).respond(json=conversation_action())
    read = mock.post(url(f"/v0/conversations/{CONV}/read")).respond(json=conversation_action("read"))
    mock.get(url(f"/v0/conversations/{CONV}/messages")).respond(json=page([message()]))
    h = aflow.conversation({"id": CONV, "channel": "telegram"})
    assert isinstance(h, AsyncConversationHandle)
    assert h.channel == "telegram"
    await h.react(MSG, None)
    assert json.loads(react.calls.last.request.read()) == {"message_id": MSG, "emoji": None}
    await h.send("hello")
    assert json.loads(send.calls.last.request.read()) == {"kind": "basic", "text": "hello"}
    assert (await h.typing()).action == "typing"
    assert json.loads(typing.calls.last.request.read()) == {}
    assert (await h.read(MSG)).action == "read"
    assert json.loads(read.calls.last.request.read()) == {"up_to": MSG}
    assert [m.id async for m in h.messages()] == [MSG]


async def test_async_send_routing(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    buttons = mock.post(url(f"/v0/conversations/{CONV}/buttons")).respond(json=message())
    card = mock.post(url(f"/v0/conversations/{CONV}/contact-card")).respond(json=message())
    unsend = mock.delete(url(f"/v0/messages/{MSG}")).respond(json=message(status="unsent"))
    await aflow.messages.send(CONV, {"kind": "buttons", "text": "Size?", "buttons": [{"id": "s", "label": "S"}]})
    assert buttons.called
    await aflow.messages.send(CONV, {"kind": "contact_card", "name": "Ada"})
    assert json.loads(card.calls.last.request.read()) == {"kind": "contact_card", "name": "Ada"}
    assert (await aflow.messages.send(CONV, {"kind": "unsend", "message_id": MSG})).status == "unsent"
    assert unsend.called
    with pytest.raises(ValueError):
        await aflow.messages.send(CONV, {"text": "no kind"})


async def test_with_options_and_context_manager(mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(503, json=error("api_error"))
    async with AsyncFlow(KEY, base_url=BASE) as aflow:
        copy = aflow.with_options(max_retries=0, timeout=3)
        assert isinstance(copy, AsyncFlow)
        assert copy._http.client is aflow._http.client
        assert (copy._http.options.max_retries, copy._http.options.timeout) == (0, 3)
        assert aflow._http.options.max_retries == 2
        with pytest.raises(Exception):  # noqa: B017 - APIError; only the count matters here
            await copy.messages.retrieve(MSG)
        assert route.call_count == 1
        await copy.aclose()
        assert not aflow._http.client.is_closed
        inner = aflow._http.client
    assert inner.is_closed


async def test_callers_async_client_left_open() -> None:
    client = httpx.AsyncClient()
    async with AsyncFlow(KEY, base_url=BASE, http_client=client):
        pass
    assert not client.is_closed
    await client.aclose()
