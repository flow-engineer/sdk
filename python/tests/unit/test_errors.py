"""Typed errors: one class per error type, with the error body's details."""

from __future__ import annotations

import typing

import httpx
import pytest
import respx
from conftest import MSG, url

from flow_messaging import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    ChannelError,
    DeviceSignInError,
    FileBlockedError,
    Flow,
    FlowError,
    IdempotencyConflictError,
    InvalidRequestError,
    NewContactLimitError,
    NotFoundError,
    NotImplementedYetError,
    OutsideWindowError,
    PermissionDeniedError,
    RateLimitError,
    SenderThrottledError,
    UnsupportedContentError,
)
from flow_messaging.errors import ErrorType, error_from_body

CASES: list[tuple[str, int, type[FlowError]]] = [
    ("invalid_request", 400, InvalidRequestError),
    ("authentication", 401, AuthenticationError),
    ("permission", 403, PermissionDeniedError),
    ("not_found", 404, NotFoundError),
    ("idempotency_conflict", 409, IdempotencyConflictError),
    ("outside_window", 409, OutsideWindowError),
    ("unsupported_content", 422, UnsupportedContentError),
    ("new_contact_limit", 429, NewContactLimitError),
    ("sender_throttled", 429, SenderThrottledError),
    ("file_blocked", 422, FileBlockedError),
    ("rate_limited", 429, RateLimitError),
    ("channel_error", 502, ChannelError),
    ("not_implemented", 501, NotImplementedYetError),
    ("api_error", 500, APIError),
]


def test_cases_cover_every_error_type() -> None:
    assert sorted(t for t, _, _ in CASES) == sorted(typing.get_args(ErrorType))


@pytest.mark.parametrize(("etype", "status", "cls"), CASES)
def test_every_error_type_maps_to_its_class(
    etype: str, status: int, cls: type[FlowError], mock: respx.MockRouter
) -> None:
    body = {
        "error": {
            "type": etype,
            "message": f"The {etype} message.",
            "hint": "Change the thing.",
            "doc_url": f"https://api.flow.engineer/docs/errors/{etype}",
            "request_id": "req_body",
            "param": "content.text",
            "channel_code": "some_code",
            "retry_after": 120,
            "conversation": "conv_x",
            "sender": "snd_x",
        }
    }
    mock.get(url(f"/v1/messages/{MSG}")).respond(status, json=body, headers={"Flow-Request-Id": "req_header"})
    # max_retries=0 so the retryable types raise at once; a 120 s retry_after is never waited anyway.
    with Flow("fk_test_x", base_url="https://api.test", max_retries=0) as flow, pytest.raises(cls) as e:
        flow.messages.retrieve(MSG)
    err = e.value
    assert type(err) is cls
    assert isinstance(err, FlowError)
    assert err.type == etype
    assert err.status == status
    assert err.message == f"The {etype} message."
    assert err.hint == "Change the thing."
    assert err.doc_url == f"https://api.flow.engineer/docs/errors/{etype}"
    assert err.request_id == "req_body"
    assert err.param == "content.text"
    assert err.channel_code == err.code == "some_code"
    assert err.retry_after == 120
    assert err.conversation == "conv_x"
    assert err.sender == "snd_x"
    assert err.body is not None and err.body["type"] == etype
    assert err.headers is not None and err.headers["flow-request-id"] == "req_header"
    s = str(err)
    assert f"The {etype} message." in s
    assert "Hint: Change the thing." in s
    assert f"See https://api.flow.engineer/docs/errors/{etype}" in s
    assert "req_body" in s
    assert cls.__name__ in repr(err)


def test_request_id_from_header_when_body_has_none(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v1/messages/{MSG}")).respond(
        404,
        json={"error": {"type": "not_found", "message": "No such message.", "hint": "h", "doc_url": "d"}},
        headers={"Flow-Request-Id": "req_hdr"},
    )
    with pytest.raises(NotFoundError) as e:
        flow.messages.retrieve(MSG)
    assert e.value.request_id == "req_hdr"
    assert "(request req_hdr)" in str(e.value)


def test_unknown_type_becomes_flow_error() -> None:
    err = error_from_body(418, {"type": "teapot", "message": "Short and stout."})
    assert type(err) is FlowError
    assert err.type == "teapot"
    assert err.status == 418
    assert str(err) == "Short and stout."


def test_unknown_type_over_http(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v1/messages/{MSG}")).respond(400, json={"error": {"type": "brand_new", "message": "New."}})
    with pytest.raises(FlowError) as e:
        flow.messages.retrieve(MSG)
    assert type(e.value) is FlowError
    assert e.value.type == "brand_new"


@pytest.mark.parametrize(
    ("status", "cls", "etype"),
    [
        (400, InvalidRequestError, "invalid_request"),
        (404, InvalidRequestError, "invalid_request"),
        (500, APIError, "api_error"),
    ],
)
def test_non_json_body_gives_typed_error_by_status(
    status: int, cls: type[FlowError], etype: str, mock: respx.MockRouter
) -> None:
    mock.get(url(f"/v1/messages/{MSG}")).respond(status, text="<html>oops</html>", headers={"Flow-Request-Id": "req_h"})
    with Flow("fk_test_x", base_url="https://api.test", max_retries=0) as flow, pytest.raises(cls) as e:
        flow.messages.retrieve(MSG)
    assert e.value.type == etype
    assert e.value.status == status
    assert str(status) in e.value.message
    assert e.value.request_id == "req_h"
    assert e.value.hint is None


def test_json_body_without_error_object(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url(f"/v1/messages/{MSG}")).respond(403, json={"detail": "nope"})
    with pytest.raises(InvalidRequestError) as e:
        flow.messages.retrieve(MSG)
    assert e.value.status == 403


def test_str_without_hint_or_doc_url() -> None:
    err = error_from_body(404, {"type": "not_found", "message": "Gone."})
    assert str(err) == "Gone."
    assert err.code is None
    assert err.retry_after is None


def test_retry_after_header_parsed() -> None:
    err = error_from_body(429, {"type": "rate_limited", "message": "Slow down."}, httpx.Headers({"Retry-After": " 5 "}))
    assert err.retry_after == 5
    err = error_from_body(429, {"type": "rate_limited", "message": "x"}, httpx.Headers({"Retry-After": "soon"}))
    assert err.retry_after is None


def test_sdk_error_classes() -> None:
    assert issubclass(APIConnectionError, FlowError)
    d = DeviceSignInError("denied")
    assert d.reason == "denied" and d.type == "device_sign_in"
    assert DeviceSignInError("expired").reason == "expired"
