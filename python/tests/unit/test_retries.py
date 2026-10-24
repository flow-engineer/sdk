"""Retries: what is retried, how long the client waits, and what is raised in the end.
Waits go through the client's fake ``_sleep`` (the ``flow`` fixture)."""

from __future__ import annotations

import httpx
import pytest
import respx
from conftest import BASE, CONV, KEY, MSG, error, message, url

from flow_messaging import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    ChannelError,
    Flow,
    IdempotencyConflictError,
    NewContactLimitError,
    RateLimitError,
    SenderThrottledError,
)

SEND = url(f"/v0/conversations/{CONV}/messages")


def ok() -> httpx.Response:
    return httpx.Response(200, json=message())


def test_rate_limited_waits_retry_after_then_succeeds(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(SEND)
    route.side_effect = [httpx.Response(429, json=error("rate_limited", retry_after=3)), ok()]
    msg = flow.messages.send(CONV, "hi")
    assert msg.id == MSG
    assert route.call_count == 2
    assert sleeps == [3.0]


def test_retry_after_header_used_when_body_has_none(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(SEND)
    route.side_effect = [httpx.Response(429, json=error("rate_limited"), headers={"Retry-After": "7"}), ok()]
    flow.messages.send(CONV, "hi")
    assert sleeps == [7.0]


def test_body_retry_after_wins_over_header(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(SEND)
    route.side_effect = [
        httpx.Response(429, json=error("rate_limited", retry_after=2), headers={"Retry-After": "9"}),
        ok(),
    ]
    flow.messages.send(CONV, "hi")
    assert sleeps == [2.0]


def test_retry_after_over_sixty_seconds_is_raised(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(SEND).respond(429, json=error("rate_limited", retry_after=61))
    with pytest.raises(RateLimitError) as e:
        flow.messages.send(CONV, "hi")
    assert e.value.retry_after == 61
    assert route.call_count == 1
    assert sleeps == []


def test_retry_after_of_exactly_sixty_is_waited(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(SEND)
    route.side_effect = [httpx.Response(429, json=error("rate_limited", retry_after=60)), ok()]
    flow.messages.send(CONV, "hi")
    assert sleeps == [60.0]


@pytest.mark.parametrize("status", [500, 502, 503, 504, 408])
def test_server_errors_retried_with_backoff(
    status: int, flow: Flow, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}"))
    route.side_effect = [
        httpx.Response(status, json=error("api_error")),
        httpx.Response(status, text="Bad gateway"),
        ok(),
    ]
    assert flow.messages.retrieve(MSG).id == MSG
    assert route.call_count == 3
    assert len(sleeps) == 2
    # Exponential with jitter: retry 1 waits 0.25..0.5 s, retry 2 waits 0.5..1 s.
    assert 0.25 <= sleeps[0] <= 0.5
    assert 0.5 <= sleeps[1] <= 1.0


def test_server_error_with_retry_after_waits_that(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}"))
    route.side_effect = [httpx.Response(503, json=error("api_error", retry_after=4)), ok()]
    flow.messages.retrieve(MSG)
    assert sleeps == [4.0]


def test_default_max_retries_is_two(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(500, json=error("api_error", request_id="req_1"))
    with pytest.raises(APIError) as e:
        flow.messages.retrieve(MSG)
    assert route.call_count == 3
    assert len(sleeps) == 2
    assert e.value.status == 500
    assert e.value.request_id == "req_1"


@pytest.mark.parametrize("max_retries", [0, 1, 4])
def test_max_retries_respected(max_retries: int, mock: respx.MockRouter) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(503, json=error("api_error"))
    waits: list[float] = []
    with Flow(KEY, base_url=BASE, max_retries=max_retries) as flow:
        flow._http._sleep = waits.append
        with pytest.raises(APIError):
            flow.messages.retrieve(MSG)
    assert route.call_count == max_retries + 1
    assert len(waits) == max_retries


def test_channel_error_502_not_retried(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(SEND).respond(502, json=error("channel_error", channel_code="bot_blocked"))
    with pytest.raises(ChannelError) as e:
        flow.messages.send(CONV, "hi")
    assert e.value.code == "bot_blocked"
    assert route.call_count == 1
    assert sleeps == []


def test_idempotency_in_progress_retried(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(SEND)
    route.side_effect = [
        httpx.Response(409, json=error("idempotency_conflict", channel_code="in_progress", retry_after=1)),
        ok(),
    ]
    flow.messages.send(CONV, "hi", idempotency_key="k1")
    assert route.call_count == 2
    assert sleeps == [1.0]
    assert {c.request.headers["idempotency-key"] for c in route.calls} == {"k1"}


@pytest.mark.parametrize("code", ["body_mismatch", "secret_not_kept"])
def test_other_idempotency_conflicts_not_retried(
    code: str, flow: Flow, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.post(SEND).respond(409, json=error("idempotency_conflict", channel_code=code))
    with pytest.raises(IdempotencyConflictError) as e:
        flow.messages.send(CONV, "hi")
    assert e.value.channel_code == code
    assert route.call_count == 1
    assert sleeps == []


@pytest.mark.parametrize(
    ("etype", "cls"), [("new_contact_limit", NewContactLimitError), ("sender_throttled", SenderThrottledError)]
)
def test_send_gate_budgets_not_retried(
    etype: str, cls: type[Exception], flow: Flow, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.post(url("/v0/messages")).respond(429, json=error(etype, retry_after=3600))
    with pytest.raises(cls):
        flow.messages.start(sender="snd_x", to="+15555550100", content="hi")
    assert route.call_count == 1
    assert sleeps == []


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_client_errors_not_retried(status: int, flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).respond(status, json=error("invalid_request"))
    with pytest.raises(Exception):  # noqa: B017 - the class is tested in test_errors.py
        flow.messages.retrieve(MSG)
    assert route.call_count == 1
    assert sleeps == []


def test_connection_errors_retried_then_succeed(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}"))
    route.side_effect = [httpx.ConnectError("refused"), httpx.RemoteProtocolError("reset"), ok()]
    assert flow.messages.retrieve(MSG).id == MSG
    assert route.call_count == 3
    assert len(sleeps) == 2


def test_connection_errors_raised_as_api_connection_error(
    flow: Flow, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(APIConnectionError) as e:
        flow.messages.retrieve(MSG)
    assert not isinstance(e.value, APITimeoutError)
    assert e.value.type == "connection_error"
    assert isinstance(e.value.__cause__, httpx.ConnectError)
    assert BASE in str(e.value)
    assert route.call_count == 3
    assert len(sleeps) == 2


def test_timeouts_retried_then_raised_as_api_timeout_error(
    flow: Flow, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}")).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(APITimeoutError) as e:
        flow.messages.retrieve(MSG)
    assert isinstance(e.value, APIConnectionError)
    assert e.value.type == "timeout"
    assert route.call_count == 3
    assert len(sleeps) == 2


def test_timeout_then_success(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.get(url(f"/v0/messages/{MSG}"))
    route.side_effect = [httpx.ConnectTimeout("slow"), ok()]
    assert flow.messages.retrieve(MSG).id == MSG
    assert len(sleeps) == 1


def test_per_call_max_retries_zero_for_device_poll(flow: Flow, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(url("/v0/device/token")).respond(503, json=error("api_error"))
    with pytest.raises(APIError):
        flow.device.poll("dc_x")
    assert route.call_count == 1
    assert sleeps == []
