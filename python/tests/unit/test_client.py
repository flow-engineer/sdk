"""Client setup: key and base URL from the environment, headers, idempotency keys,
keyless calls, with_options and the context managers."""

from __future__ import annotations

import httpx
import pytest
import respx
from conftest import (
    BASE,
    CONV,
    KEY,
    MSG,
    conversation,
    conversation_action,
    device_authorization,
    device_token,
    message,
    page,
    sandbox_key,
    url,
)

import flow_messaging
from flow_messaging import API_VERSION, AuthenticationError, Flow


def test_key_and_base_url_from_environment(monkeypatch: pytest.MonkeyPatch, mock: respx.MockRouter) -> None:
    monkeypatch.setenv("FLOW_MESSAGING_KEY", "fk_test_env")
    monkeypatch.setenv("FLOW_MESSAGING_BASE_URL", "https://env.test/")
    route = mock.get("https://env.test/v0/messages/" + MSG).respond(json=message())
    with Flow() as flow:
        assert flow.api_key == "fk_test_env"
        assert flow.base_url == "https://env.test"
        assert flow.test_mode
        flow.messages.retrieve(MSG)
    assert route.calls.last.request.headers["authorization"] == "Bearer fk_test_env"


def test_explicit_arguments_win_over_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLOW_MESSAGING_KEY", "fk_test_env")
    monkeypatch.setenv("FLOW_MESSAGING_BASE_URL", "https://env.test")
    with Flow("fk_live_x", base_url="https://explicit.test///") as flow:
        assert flow.api_key == "fk_live_x"
        assert flow.base_url == "https://explicit.test"
        assert not flow.test_mode


def test_default_base_url() -> None:
    with Flow(KEY) as flow:
        assert flow.base_url == flow_messaging.DEFAULT_BASE_URL == "https://api.flow.engineer"


def test_headers_on_get(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(json=message())
    flow.messages.retrieve(MSG)
    h = route.calls.last.request.headers
    assert h["authorization"] == f"Bearer {KEY}"
    assert h["flow-version"] == API_VERSION
    assert h["user-agent"].startswith("flow-messaging-python/")
    assert h["accept"] == "application/json"
    assert "idempotency-key" not in h


def test_no_flow_version_when_none(mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(json=message())
    with Flow(KEY, base_url=BASE, flow_version=None) as flow:
        flow.messages.retrieve(MSG)
    assert "flow-version" not in route.calls.last.request.headers


def test_custom_flow_version_and_default_headers(mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(json=message())
    with Flow(KEY, base_url=BASE, flow_version="2026-01-01", default_headers={"X-Extra": "1"}) as flow:
        flow.messages.retrieve(MSG)
    h = route.calls.last.request.headers
    assert h["flow-version"] == "2026-01-01"
    assert h["x-extra"] == "1"


def test_idempotency_key_on_authenticated_post(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v0/conversations/{CONV}/messages")).respond(json=message())
    flow.messages.send(CONV, "hi")
    flow.messages.send(CONV, "hi")
    first, second = (c.request.headers["idempotency-key"] for c in route.calls)
    assert first and second and first != second


def test_callers_idempotency_key_used_verbatim(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v0/conversations/{CONV}/messages")).respond(json=message())
    flow.messages.send(CONV, "hi", idempotency_key="my-key-1")
    assert route.calls.last.request.headers["idempotency-key"] == "my-key-1"
    t = mock.post(url(f"/v0/conversations/{CONV}/typing")).respond(json=conversation_action())
    flow.conversations.typing(CONV, idempotency_key="my-key-2")
    assert t.calls.last.request.headers["idempotency-key"] == "my-key-2"


def test_no_idempotency_key_on_get_patch_delete(flow: Flow, mock: respx.MockRouter) -> None:
    routes = [
        mock.get(url(f"/v0/messages/{MSG}")).respond(json=message()),
        mock.patch(url(f"/v0/messages/{MSG}")).respond(json=message()),
        mock.delete(url(f"/v0/messages/{MSG}")).respond(json=message(status="unsent")),
        mock.get(url("/v0/conversations")).respond(json=page([conversation()])),
    ]
    flow.messages.retrieve(MSG)
    flow.messages.edit(MSG, "new")
    flow.messages.unsend(MSG)
    flow.conversations.list()
    for route in routes:
        assert route.called
        assert "idempotency-key" not in route.calls.last.request.headers


def test_same_idempotency_key_across_retries(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(url(f"/v0/conversations/{CONV}/messages"))
    route.side_effect = [
        httpx.Response(503, json={"error": {"type": "api_error", "message": "busy"}}),
        httpx.ConnectError("refused"),
        httpx.Response(200, json=message()),
    ]
    flow.messages.send(CONV, "hi")
    keys = {c.request.headers["idempotency-key"] for c in route.calls}
    assert route.call_count == 3
    assert len(keys) == 1


def test_without_key_raises_before_any_request(mock: respx.MockRouter) -> None:
    route = mock.route(host="api.test").respond(json=message())
    with Flow(base_url=BASE) as flow:
        assert flow.api_key is None
        assert not flow.test_mode
        with pytest.raises(AuthenticationError) as e:
            flow.messages.send(CONV, "hi")
        assert "FLOW_MESSAGING_KEY" in str(e.value)
        assert "sandbox.create_key" in str(e.value)
        with pytest.raises(AuthenticationError):
            flow.messages.retrieve(MSG)
        with pytest.raises(AuthenticationError):
            flow.conversations.list()
        with pytest.raises(AuthenticationError):
            flow.app.retrieve()
    assert not route.called


def test_keyless_calls_without_key(mock: respx.MockRouter) -> None:
    keys = mock.post(url("/v0/sandbox/keys")).respond(201, json=sandbox_key())
    auth = mock.post(url("/v0/device/authorizations")).respond(json=device_authorization())
    tok = mock.post(url("/v0/device/token")).respond(json=device_token())
    with Flow(base_url=BASE) as flow:
        created = flow.sandbox.create_key(name="My agent")
        flow.device.authorize()
        flow.device.poll("dc_x")
    assert created.key == KEY
    assert created.claim_token == "fct_x"
    for route in (keys, auth, tok):
        h = route.calls.last.request.headers
        assert "authorization" not in h
        assert "idempotency-key" not in h
        assert h["flow-version"] == API_VERSION
    assert keys.calls.last.request.read() == b'{"name":"My agent"}'


def test_keyless_calls_send_no_key_even_when_client_has_one(flow: Flow, mock: respx.MockRouter) -> None:
    keys = mock.post(url("/v0/sandbox/keys")).respond(201, json=sandbox_key())
    tok = mock.post(url("/v0/device/token")).respond(json=device_token())
    flow.sandbox.create_key()
    flow.device.poll("dc_x")
    for route in (keys, tok):
        h = route.calls.last.request.headers
        assert "authorization" not in h
        assert "idempotency-key" not in h


def test_with_options(mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(json=message())
    with Flow(KEY, base_url=BASE, timeout=30, max_retries=2, default_headers={"X-A": "1"}) as flow:
        copy = flow.with_options(timeout=5, max_retries=0, default_headers={"X-B": "2"})
        assert copy is not flow
        assert isinstance(copy, Flow)
        o, c = flow._http.options, copy._http.options
        assert (c.timeout, c.max_retries) == (5, 0)
        assert (o.timeout, o.max_retries) == (30, 2)
        assert copy.api_key == KEY
        assert copy.base_url == BASE
        assert c.flow_version == o.flow_version
        # Shares the connection pool.
        assert copy._http.client is flow._http.client
        copy.messages.retrieve(MSG)
        h = route.calls.last.request.headers
        assert h["x-a"] == "1" and h["x-b"] == "2"
        assert h["authorization"] == f"Bearer {KEY}"
        other = flow.with_options(api_key="fk_live_x")
        other.messages.retrieve(MSG)
        assert route.calls.last.request.headers["authorization"] == "Bearer fk_live_x"
        assert flow.api_key == KEY
        # Closing the copy leaves the shared pool open.
        copy.close()
        flow.messages.retrieve(MSG)


def test_with_options_max_retries_zero_is_respected(mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(503, json={"error": {"type": "api_error", "message": "x"}})
    with Flow(KEY, base_url=BASE) as flow:
        copy = flow.with_options(max_retries=0)
        with pytest.raises(flow_messaging.APIError):
            copy.messages.retrieve(MSG)
    assert route.call_count == 1


def test_context_manager_closes_own_client() -> None:
    with Flow(KEY, base_url=BASE) as flow:
        inner = flow._http.client
        assert not inner.is_closed
    assert inner.is_closed


def test_context_manager_leaves_callers_client_open() -> None:
    client = httpx.Client()
    with Flow(KEY, base_url=BASE, http_client=client) as flow:
        assert flow._http.client is client
    assert not client.is_closed
    client.close()


def test_timeout_passed_per_request(mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(json=message())
    with Flow(KEY, base_url=BASE, timeout=7) as flow:
        flow.messages.retrieve(MSG)
    assert route.calls.last.request.extensions["timeout"]["read"] == 7
