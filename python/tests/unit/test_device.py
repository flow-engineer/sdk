"""The device sign-in: who gets the bearer, polling, slow-downs, transient failures."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from conftest import BASE, KEY, LIVE_KEY, device_authorization, device_token, error, url

from flow_messaging import APIConnectionError, APIError, DeviceSignInError, Flow
from flow_messaging.types import DeviceAuthorization

AUTH = url("/v0/device/authorizations")
TOKEN = url("/v0/device/token")


def client(key: str | None, sleeps: list[float]) -> Flow:
    f = Flow(key, base_url=BASE)
    f._http._sleep = sleeps.append
    return f


@pytest.mark.parametrize(
    ("key", "claim_token", "use_key", "bearer"),
    [
        (KEY, None, True, True),
        (KEY, "fct_x", True, False),
        (KEY, None, False, False),
        (LIVE_KEY, None, True, False),
        (None, None, True, False),
        (None, "fct_x", True, False),
    ],
)
def test_authorize_bearer_rules(
    key: str | None, claim_token: str | None, use_key: bool, bearer: bool, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.post(AUTH).respond(json=device_authorization())
    with client(key, sleeps) as flow:
        a = flow.device.authorize(claim_token=claim_token, client_name="my-cli", use_key=use_key)
    assert isinstance(a, DeviceAuthorization)
    h = route.calls.last.request.headers
    if bearer:
        assert h["authorization"] == f"Bearer {KEY}"
    else:
        assert "authorization" not in h
    expected = {"client_name": "my-cli"}
    if claim_token:
        expected["claim_token"] = claim_token
    assert json.loads(route.calls.last.request.read()) == expected


def test_authorize_idempotency_key_only_with_bearer(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(AUTH).respond(json=device_authorization())
    flow.device.authorize()
    # The bearer makes this an authenticated POST, so it carries an idempotency key.
    assert route.calls.last.request.headers["authorization"] == f"Bearer {KEY}"
    assert route.calls.last.request.headers["idempotency-key"]
    flow.device.authorize(claim_token="fct_x")
    assert "idempotency-key" not in route.calls.last.request.headers


def test_poll_body(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(TOKEN).respond(json=device_token())
    assert flow.device.poll("dc_x").status == "pending"
    assert json.loads(route.calls.last.request.read()) == {"device_code": "dc_x"}


@pytest.mark.parametrize("provider", ["flow", "github", "google", "a-provider-added-later"])
def test_poll_accepts_any_sign_in_provider(provider: str, flow: Flow, mock: respx.MockRouter) -> None:
    # The list of providers grows without a new API version, so a value this SDK
    # does not know yet still parses.
    mock.post(TOKEN).respond(
        json=device_token("approved", key="fk_test_new", user={"name": "Lin", "provider": provider})
    )
    tok = flow.device.poll("dc_x")
    assert tok.user is not None
    assert tok.user.provider == provider


def tokens(route: respx.Route, *answers: httpx.Response | Exception) -> None:
    route.side_effect = list(answers)


def ok(status: str, interval: int = 5, **extra: object) -> httpx.Response:
    return httpx.Response(200, json=device_token(status, interval, **extra))


def test_wait_for_key_pending_then_approved(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(TOKEN)
    tokens(route, ok("pending"), ok("pending"), ok("approved", key="fk_test_new"))
    tok = flow.device.wait_for_key("dc_x", interval=5)
    assert tok.status == "approved"
    assert tok.key == "fk_test_new"
    assert sleeps == [5, 5, 5]
    assert route.call_count == 3


def test_wait_for_key_grows_to_tokens_interval(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(TOKEN)
    tokens(route, ok("pending", 7), ok("pending", 3), ok("approved", 7, key="fk_test_new"))
    flow.device.wait_for_key("dc_x", interval=5)
    # Never shorter than the largest interval seen.
    assert sleeps == [5, 7, 7]


def test_wait_for_key_interval_at_least_one_second(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    tokens(mock.post(TOKEN), ok("approved", 0, key="fk_test_new"))
    flow.device.wait_for_key("dc_x", interval=0)
    assert sleeps == [1.0]


def test_wait_for_key_denied(flow: Flow, mock: respx.MockRouter) -> None:
    tokens(mock.post(TOKEN), ok("pending"), ok("denied"))
    with pytest.raises(DeviceSignInError) as e:
        flow.device.wait_for_key("dc_x")
    assert e.value.reason == "denied"
    assert e.value.type == "device_sign_in"


def test_wait_for_key_expired_status(flow: Flow, mock: respx.MockRouter) -> None:
    tokens(mock.post(TOKEN), ok("expired"))
    with pytest.raises(DeviceSignInError) as e:
        flow.device.wait_for_key("dc_x")
    assert e.value.reason == "expired"


def test_wait_for_key_past_expires_at(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(TOKEN)
    tokens(route, ok("pending"), ok("pending"))
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    with pytest.raises(DeviceSignInError) as e:
        flow.device.wait_for_key("dc_x", expires_at=past)
    assert e.value.reason == "expired"
    assert route.call_count == 1


def test_wait_for_key_429_slows_down(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(TOKEN)
    tokens(
        route,
        httpx.Response(429, json=error("rate_limited", retry_after=12)),
        httpx.Response(429, json=error("rate_limited", retry_after=1)),
        ok("pending", 5),
        ok("approved", key="fk_test_new"),
    )
    flow.device.wait_for_key("dc_x", interval=5)
    # 5; 429 -> interval 10, wait max(10, 12); 429 -> interval 15, wait 15; pending -> 15.
    assert sleeps == [5, 12, 15, 15]


def test_wait_for_key_tolerates_four_transient_failures(
    flow: Flow, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.post(TOKEN)
    tokens(
        route,
        httpx.Response(503, json=error("api_error")),
        httpx.ConnectError("down"),
        httpx.Response(500, text="oops"),
        httpx.ReadTimeout("slow"),
        ok("approved", key="fk_test_new"),
    )
    assert flow.device.wait_for_key("dc_x", interval=5).key == "fk_test_new"
    assert route.call_count == 5
    assert sleeps == [5] * 5


def test_wait_for_key_fifth_failure_in_a_row_raises(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(TOKEN)
    tokens(route, *[httpx.Response(503, json=error("api_error"))] * 4, httpx.ConnectError("down"))
    with pytest.raises(APIConnectionError):
        flow.device.wait_for_key("dc_x")
    assert route.call_count == 5


def test_wait_for_key_failures_reset_after_success(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(TOKEN)
    fail = httpx.Response(503, json=error("api_error"))
    tokens(route, *[fail] * 4, ok("pending"), *[fail] * 4, ok("approved", key="fk_test_new"))
    assert flow.device.wait_for_key("dc_x").status == "approved"
    assert route.call_count == 10


def test_wait_for_key_other_errors_raise_at_once(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.post(TOKEN).respond(400, json=error("invalid_request"))
    with pytest.raises(Exception) as e:
        flow.device.wait_for_key("dc_x")
    assert not isinstance(e.value, APIError)
    assert route.call_count == 1


def test_sign_in_prompts_once_then_polls(mock: respx.MockRouter, sleeps: list[float]) -> None:
    auth = mock.post(AUTH).respond(json=device_authorization(interval=6))
    route = mock.post(TOKEN)
    order: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        order.append("poll")
        n = len([o for o in order if o == "poll"])
        return httpx.Response(200, json=device_token("approved" if n == 2 else "pending", 6, key="fk_test_new"))

    route.side_effect = answer
    seen: list[DeviceAuthorization] = []

    def prompt(a: DeviceAuthorization) -> None:
        order.append("prompt")
        seen.append(a)

    with client(None, sleeps) as flow:
        tok = flow.device.sign_in(prompt, claim_token="fct_x", client_name="cli")
    assert tok.key == "fk_test_new"
    assert order == ["prompt", "poll", "poll"]
    assert len(seen) == 1
    assert seen[0].user_code == "ABCD-EFGH"
    assert sleeps == [6, 6]
    assert json.loads(auth.calls.last.request.read()) == {"claim_token": "fct_x", "client_name": "cli"}
    assert json.loads(route.calls.last.request.read()) == {"device_code": "dc_x"}


def test_sign_in_stops_at_authorizations_expiry(mock: respx.MockRouter, sleeps: list[float]) -> None:
    mock.post(AUTH).respond(json=device_authorization(expires_at="2020-01-01T00:00:00Z"))
    tokens(mock.post(TOKEN), ok("pending"))
    with client(None, sleeps) as flow, pytest.raises(DeviceSignInError) as e:
        flow.device.sign_in(lambda a: None)
    assert e.value.reason == "expired"
