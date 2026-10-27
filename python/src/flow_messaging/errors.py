"""Typed errors. Every error the API returns is a :class:`FlowError` subclass chosen by
the error's ``type`` (a closed list). Catch the class, or switch on ``type``; never on
the message.

.. code-block:: python

    try:
        flow.messages.send(conversation_id, "hi")
    except OutsideWindowError:
        flow.messages.send(conversation_id, template("tpl_...", "en"))
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

import httpx

ErrorType = Literal[
    "invalid_request",
    "authentication",
    "permission",
    "not_found",
    "idempotency_conflict",
    "outside_window",
    "unsupported_content",
    "new_contact_limit",
    "sender_throttled",
    "file_blocked",
    "rate_limited",
    "channel_error",
    "not_implemented",
    "api_error",
]

#: Error types raised by the SDK itself, never sent by the API.
SDKErrorType = Literal["connection_error", "timeout", "signature_verification", "device_sign_in"]


class FlowError(Exception):
    """Base class of every error this package raises.

    Attributes mirror the API's error body: ``type``, ``message``, ``hint`` (what to
    change), ``doc_url`` (the page for this error type), ``request_id`` (quote it when
    asking for help), ``param``, ``retry_after`` (seconds), ``conversation``,
    ``sender`` and ``channel_code`` (also as ``code``).
    """

    type: ErrorType | SDKErrorType | str
    message: str
    status: int | None
    hint: str | None
    doc_url: str | None
    request_id: str | None
    param: str | None
    retry_after: int | None
    conversation: str | None
    sender: str | None
    channel_code: str | None
    #: The error body as the API sent it.
    body: dict[str, Any] | None
    #: The answer's headers, when there was an answer.
    headers: httpx.Headers | None

    def __init__(
        self,
        message: str,
        *,
        type: ErrorType | SDKErrorType | str,
        status: int | None = None,
        body: Mapping[str, Any] | None = None,
        headers: httpx.Headers | None = None,
    ) -> None:
        super().__init__(message)
        b = dict(body) if body else {}
        self.message = message
        self.type = type
        self.status = status
        self.body = b or None
        self.headers = headers
        self.hint = b.get("hint")
        self.doc_url = b.get("doc_url")
        self.param = b.get("param")
        self.conversation = b.get("conversation")
        self.sender = b.get("sender")
        self.channel_code = b.get("channel_code")
        self.request_id = b.get("request_id") or (headers.get("flow-request-id") if headers is not None else None)
        retry_after = b.get("retry_after")
        if retry_after is None and headers is not None:
            h = headers.get("retry-after")
            if h and h.strip().isdigit():
                retry_after = int(h.strip())
        self.retry_after = retry_after

    @property
    def code(self) -> str | None:
        """The channel's or Flow's code for this case (``channel_code``), when there is one."""
        return self.channel_code

    def __str__(self) -> str:
        parts = [self.message]
        if self.hint:
            parts.append(f"Hint: {self.hint}")
        if self.doc_url:
            parts.append(f"See {self.doc_url}")
        if self.request_id:
            parts.append(f"(request {self.request_id})")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(type={self.type!r}, status={self.status!r}, message={self.message!r})"


class InvalidRequestError(FlowError):
    """400 ``invalid_request``: the request is malformed or a parameter is invalid; see ``param``."""


class AuthenticationError(FlowError):
    """401 ``authentication``: the API key is missing, unknown, revoked or expired.

    A sandbox key past its ``expires_at`` has ``code`` ``sandbox_key_expired``: sign in
    (``device.sign_in``) or get a new key.
    """


class PermissionDeniedError(FlowError):
    """403 ``permission``: the key may not do this (for example a test key using a live sender).

    Past the sandbox allowance ``code`` is ``sandbox_allowance_used`` (also
    ``sandbox_contact_limit``, ``sandbox_channel_not_included``, ``sign_in_required``):
    sign in to lift it (``device.sign_in``).
    """


class NotFoundError(FlowError):
    """404 ``not_found``: no such object for this app and mode."""


class IdempotencyConflictError(FlowError):
    """409 ``idempotency_conflict``: the idempotency key was used for a different request
    (``code`` ``body_mismatch``), that request is still running (``in_progress``; the
    client retries it after ``retry_after``), or its answer carried a secret shown only
    once (``secret_not_kept``)."""


class OutsideWindowError(FlowError):
    """409 ``outside_window``: WhatsApp's 24-hour window is closed (send a template), or an
    SMS contact is inside the sender's quiet hours. On iMessage, messages have no window:
    ``channel_code`` ``imessage_typing_window_closed`` or ``imessage_read_window_closed``
    is typing or a read receipt more than 5 minutes after your line's last message to the
    person (safe to ignore; send your reply first), and ``imessage_contact_must_write_first``
    (in ``message.failed``) a person who has not messaged the line yet."""


class UnsupportedContentError(FlowError):
    """422 ``unsupported_content``: the conversation's channel cannot take this kind or
    field, and Flow converts nothing. ``param`` names what was refused (``kind``, a field,
    a channel block) and ``hint`` says what to send instead. The answer is kept under the
    request's ``Idempotency-Key``, so send the replacement with a new key: the refused
    one's plus what it is (``evt_123:card:2:basic``)."""


class NewContactLimitError(FlowError):
    """429 ``new_contact_limit``: the sender used its budget for starting conversations; see ``retry_after``."""


class SenderThrottledError(FlowError):
    """429 ``sender_throttled``: abuse signals tripped; starts are paused until ``retry_after``, replies still go."""


class FileBlockedError(FlowError):
    """422 ``file_blocked``: the file failed the malware scan and was not stored."""


class RateLimitError(FlowError):
    """429 ``rate_limited``: too many requests for this key; see ``retry_after``. Retried automatically."""


class ChannelError(FlowError):
    """502 ``channel_error``: the channel refused or failed the message; see ``code``."""


class NotImplementedYetError(FlowError):
    """501 ``not_implemented``: this endpoint is not live yet."""


class APIError(FlowError):
    """500/503 ``api_error``: something went wrong on Flow's side. Retried automatically with the same idempotency key."""


class APIConnectionError(FlowError):
    """The request never got an answer (network failure). Retried automatically."""


class APITimeoutError(APIConnectionError):
    """The request took longer than ``timeout``. Retried automatically."""


class WebhookSignatureError(FlowError):
    """A webhook's ``Flow-Signature`` did not match, or its timestamp is outside the tolerance. Answer 400."""


class DeviceSignInError(FlowError):
    """A device sign-in ended without a key: the person refused (``reason`` ``denied``), or
    the codes ran out or were already used (``expired``). Start again with ``device.sign_in``."""

    reason: Literal["denied", "expired"]

    def __init__(self, reason: Literal["denied", "expired"]) -> None:
        super().__init__(
            "The sign-in was refused in the browser."
            if reason == "denied"
            else "The sign-in codes expired or were already used. Start the sign-in again.",
            type="device_sign_in",
        )
        self.reason = reason


_BY_TYPE: dict[str, type[FlowError]] = {
    "invalid_request": InvalidRequestError,
    "authentication": AuthenticationError,
    "permission": PermissionDeniedError,
    "not_found": NotFoundError,
    "idempotency_conflict": IdempotencyConflictError,
    "outside_window": OutsideWindowError,
    "unsupported_content": UnsupportedContentError,
    "new_contact_limit": NewContactLimitError,
    "sender_throttled": SenderThrottledError,
    "file_blocked": FileBlockedError,
    "rate_limited": RateLimitError,
    "channel_error": ChannelError,
    "not_implemented": NotImplementedYetError,
    "api_error": APIError,
}


def error_from_body(status: int, body: Mapping[str, Any] | None, headers: httpx.Headers | None = None) -> FlowError:
    """Builds the typed error for an API error body (the object under ``"error"``).
    Unknown types become :class:`FlowError`."""
    b = body or {}
    etype = b.get("type") or ("api_error" if status >= 500 else "invalid_request")
    cls = _BY_TYPE.get(etype, FlowError)
    message = b.get("message") or f"Flow Messaging answered {status} with no error body."
    return cls(message, type=etype, status=status, body=b, headers=headers)
