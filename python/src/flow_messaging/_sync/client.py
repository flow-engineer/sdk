# Generated from src/flow_messaging/_async/client.py by python/scripts/generate.py. Do not edit.
"""The client. The sync client (``Flow``) is generated from this file (``AsyncFlow``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

import httpx

from .._base import NOT_GIVEN, Options
from .._constants import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from ..types import Conversation, ConversationRef, EventType
from ..webhooks import Webhooks
from .conversation import ConversationHandle
from .http import HTTPClient
from .resources import (
    AppResource,
    Contacts,
    Conversations,
    Device,
    EventLog,
    Files,
    Messages,
    Sandbox,
    Senders,
    Templates,
    Testing,
    WebhookEndpoints,
)
from .stream import EventStream, OnStatus


class Events(EventLog):
    """The event log: ``list`` and ``retrieve`` by page, ``stream`` live."""

    def stream(
        self,
        *,
        types: Sequence[EventType] | None = None,
        after: str | None = None,
        transport: Literal["websocket", "poll"] = "websocket",
        poll_interval: float = 1.0,
        on_status: OnStatus | None = None,
    ) -> EventStream:
        """Live events over a WebSocket. Resumes with ``after`` on every reconnect, so no
        event is lost; pass ``after`` to replay from an event first. Ends with a typed
        error when the key is refused (``AuthenticationError``, ``PermissionDeniedError``)
        instead of reconnecting. ``transport="poll"`` reads the event log instead, for
        networks that block WebSockets."""
        return EventStream(
            self._http,
            self,
            types=types,
            after=after,
            transport=transport,
            poll_interval=poll_interval,
            on_status=on_status,
        )


class Flow:
    """The Flow Messaging client: one API for WhatsApp, Telegram, iMessage and SMS.

    ``api_key`` defaults to the ``FLOW_MESSAGING_KEY`` environment variable and
    ``base_url`` to ``FLOW_MESSAGING_BASE_URL``, else ``https://api.flow.engineer``.
    Without a key only the keyless calls work (``sandbox.create_key`` and the device
    sign-in); every other call raises ``AuthenticationError`` before sending anything.
    ``flow_version`` is the ``Flow-Version`` to send (default: the version this SDK was
    built for, so answers match its models; None sends none). Retries cover connection
    errors, timeouts, 429 ``rate_limited`` and 5xx answers (``max_retries``, default 2).
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        flow_version: str | None = NOT_GIVEN,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        options = Options(
            api_key=api_key,
            base_url=base_url,
            flow_version=flow_version,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )
        self._init(HTTPClient(options, http_client))

    def _init(self, http: HTTPClient) -> None:
        self._http = http
        self.messages = Messages(http)
        self.conversations = Conversations(http)
        self.events = Events(http)
        self.files = Files(http)
        self.senders = Senders(http)
        self.templates = Templates(http)
        self.webhook_endpoints = WebhookEndpoints(http)
        self.contacts = Contacts(http)
        self.app = AppResource(http)
        #: Test keys without an account (``create_key``); needs no API key.
        self.sandbox = Sandbox(http)
        #: Sign-in from an agent or CLI that claims a sandbox app (``sign_in``); needs no API key.
        self.device = Device(http)
        #: Simulated contacts for tests (test keys only).
        self.test = Testing(http)
        #: Verify deliveries (``construct_event``) and build replies.
        self.webhooks = Webhooks()

    @property
    def api_key(self) -> str | None:
        return self._http.options.api_key

    @property
    def base_url(self) -> str:
        return self._http.options.base_url

    @property
    def test_mode(self) -> bool:
        """Whether the key is a test key (sandbox senders, test data)."""
        return self._http.options.test_mode

    def with_options(
        self,
        *,
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> Flow:
        """A copy of this client with other settings, sharing its connection pool."""
        o = self._http.options
        options = Options(
            api_key=api_key or o.api_key,
            base_url=o.base_url,
            flow_version=o.flow_version,
            timeout=o.timeout if timeout is None else timeout,
            max_retries=o.max_retries if max_retries is None else max_retries,
            default_headers={**o.default_headers, **(default_headers or {})},
        )
        copy = object.__new__(type(self))
        copy._init(HTTPClient(options, self._http.client))
        return copy

    def conversation(self, ref: Any) -> ConversationHandle:
        """A handle to act in a conversation, from its ID, a ``Conversation``, a
        ``ConversationRef`` or an event that happened in one."""
        if isinstance(ref, str):
            return ConversationHandle(self, ref)
        if isinstance(ref, (Conversation, ConversationRef)):
            return ConversationHandle(self, ref.id, channel=ref.channel)
        conv = getattr(ref, "conversation", None)
        if isinstance(conv, ConversationRef):
            return ConversationHandle(self, conv.id, channel=conv.channel)
        if isinstance(ref, Mapping) and isinstance(ref.get("id"), str):
            return ConversationHandle(self, ref["id"], channel=ref.get("channel"))
        raise ValueError("Pass a conversation ID, a Conversation, a ConversationRef or an event with a conversation.")

    def close(self) -> None:
        """Closes the connection pool (unless you passed your own ``http_client``)."""
        self._http.close()

    def __enter__(self) -> Flow:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
