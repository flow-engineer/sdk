"""Webhook signatures and replies.

``Flow-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256 of "t.<t>.<raw body>">``, with one
``v1`` per active secret while a secret is being rotated. Verify against the **raw**
request body, before parsing it.

.. code-block:: python

    from flow_messaging import construct_event, webhook_reply

    event = construct_event(raw_body, request.headers.get("Flow-Signature"), secret)
    if event.type == "message.received":
        return webhook_reply("Got it!")   # answer the delivery with this JSON
        # or several pieces, up to 11: webhook_reply(["Here you go:", content.image(url)])
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping, Sequence
from typing import Any

from ._base import read_env, sendable
from ._constants import ENV_WEBHOOK_SECRET
from .errors import WebhookSignatureError
from .types import Event, WebhookReply, parse_event

SIGNATURE_HEADER = "Flow-Signature"
#: Seconds a signature's timestamp may differ from now (the API's 5-minute replay window).
DEFAULT_TOLERANCE = 300

Body = str | bytes | bytearray
Secret = str | Sequence[str]


def _bytes(body: Body) -> bytes:
    return body.encode() if isinstance(body, str) else bytes(body)


def _secrets(secret: Secret | None) -> list[str]:
    if secret is None:
        env = read_env(ENV_WEBHOOK_SECRET)
        if not env:
            raise WebhookSignatureError(
                f"No webhook secret: pass the endpoint's whsec_ secret or set {ENV_WEBHOOK_SECRET}.",
                type="signature_verification",
            )
        return [env]
    return [secret] if isinstance(secret, str) else list(secret)


def _hmac(secret: str, timestamp: int, body: bytes) -> str:
    return hmac.new(secret.encode(), f"t.{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def parse_signature_header(header: str) -> tuple[int, list[str]] | None:
    """``(timestamp, [v1 signatures])`` from a ``Flow-Signature`` value, or None when malformed."""
    timestamp: int | None = None
    signatures: list[str] = []
    for part in header.split(","):
        k, _, v = part.strip().partition("=")
        if k == "t" and v.isdigit():
            timestamp = int(v)
        elif k == "v1" and v:
            signatures.append(v.lower())
    if timestamp is None or not signatures:
        return None
    return timestamp, signatures


def verify_signature(
    body: Body,
    header: str | None,
    secret: Secret | None = None,
    *,
    tolerance: int = DEFAULT_TOLERANCE,
    now: float | None = None,
) -> None:
    """Checks a delivery's ``Flow-Signature`` against your endpoint's secret (or several,
    while rotating; default ``FLOW_MESSAGING_WEBHOOK_SECRET``). Raises
    ``WebhookSignatureError`` when it does not match or is outside the replay window."""
    if not header:
        raise WebhookSignatureError("No Flow-Signature header.", type="signature_verification")
    parsed = parse_signature_header(header)
    if parsed is None:
        raise WebhookSignatureError("Flow-Signature is malformed.", type="signature_verification")
    timestamp, signatures = parsed
    current = time.time() if now is None else now
    if abs(current - timestamp) > tolerance:
        raise WebhookSignatureError(
            f"Flow-Signature timestamp is more than {tolerance}s from now (a replay, or a wrong clock).",
            type="signature_verification",
        )
    raw = _bytes(body)
    for s in _secrets(secret):
        want = _hmac(s, timestamp, raw)
        if any(hmac.compare_digest(got, want) for got in signatures):
            return
    raise WebhookSignatureError(
        "Flow-Signature does not match. Pass the raw request body, unparsed, and the endpoint's whsec_ secret.",
        type="signature_verification",
    )


def sign_payload(body: Body, secret: Secret, timestamp: int | None = None) -> str:
    """A ``Flow-Signature`` value for a body (for tests of your webhook handler)."""
    t = int(time.time()) if timestamp is None else timestamp
    raw = _bytes(body)
    return ",".join([f"t={t}", *(f"v1={_hmac(s, t, raw)}" for s in _secrets(secret))])


def construct_event(
    body: Body,
    header: str | None,
    secret: Secret | None = None,
    *,
    tolerance: int = DEFAULT_TOLERANCE,
    now: float | None = None,
) -> Event:
    """Verifies a delivery and returns its typed event. Pass the **raw** body."""
    verify_signature(body, header, secret, tolerance=tolerance, now=now)
    return parse_event(_bytes(body))


#: The most pieces one webhook reply may hold.
MAX_REPLY_PIECES = 11


def webhook_reply(reply: Any = None) -> dict[str, Any]:
    """The JSON to answer a ``message.received`` delivery with to reply at once
    (``{"reply": ...}``): a kind object (a dict with ``kind``, a model, or a builder from
    ``flow_messaging.content``), a string (short for basic text), or a list of 1 to 11 of
    those, sent in order as given; nothing is converted. None or an empty list answers
    ``{}`` (send nothing now). Raises ``ValueError`` for a piece without a ``kind`` that can
    be sent, or for more than 11 pieces, so a bad reply is caught in your handler."""
    if reply is None:
        return {}
    if isinstance(reply, (list, tuple)):
        if len(reply) > MAX_REPLY_PIECES:
            raise ValueError(f"A webhook reply holds at most {MAX_REPLY_PIECES} pieces; this one has {len(reply)}.")
        return {"reply": [sendable(p) for p in reply]} if reply else {}
    if isinstance(reply, WebhookReply) or (isinstance(reply, Mapping) and "reply" in reply and "kind" not in reply):
        inner = reply.reply if isinstance(reply, WebhookReply) else reply["reply"]
        return webhook_reply(inner)
    return {"reply": sendable(reply)}


class Webhooks:
    """``flow.webhooks``: the module's functions, with the secret defaulting to
    ``FLOW_MESSAGING_WEBHOOK_SECRET``."""

    SIGNATURE_HEADER = SIGNATURE_HEADER

    def construct_event(
        self, body: Body, header: str | None, secret: Secret | None = None, *, tolerance: int = DEFAULT_TOLERANCE
    ) -> Event:
        return construct_event(body, header, secret, tolerance=tolerance)

    def verify(
        self, body: Body, header: str | None, secret: Secret | None = None, *, tolerance: int = DEFAULT_TOLERANCE
    ) -> bool:
        """The same check as ``construct_event``, as a boolean."""
        try:
            verify_signature(body, header, secret, tolerance=tolerance)
        except WebhookSignatureError:
            return False
        return True

    def reply(self, reply: Any = None) -> dict[str, Any]:
        """``webhook_reply``: the body that answers a delivery with a reply."""
        return webhook_reply(reply)

    @staticmethod
    def header(headers: Mapping[str, str]) -> str | None:
        """The ``Flow-Signature`` value from a headers mapping, whatever its case."""
        for k, v in headers.items():
            if k.lower() == "flow-signature":
                return v
        return None


__all__ = [
    "DEFAULT_TOLERANCE",
    "MAX_REPLY_PIECES",
    "SIGNATURE_HEADER",
    "Webhooks",
    "construct_event",
    "parse_signature_header",
    "sign_payload",
    "verify_signature",
    "webhook_reply",
]
