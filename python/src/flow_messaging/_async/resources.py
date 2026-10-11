"""The API's resources, one class each, mirroring the endpoints in the spec. The sync
client is generated from this file."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import quote

from .. import _base
from .._base import body, parse, parser
from ..errors import APIConnectionError, APIError, DeviceSignInError, RateLimitError
from ..pagination import AsyncPager
from ..types import (
    AppContext,
    Capabilities,
    Channel,
    Contact,
    Conversation,
    ConversationAction,
    Deleted,
    DeviceAuthorization,
    DeviceToken,
    Event,
    EventType,
    File,
    Message,
    SandboxKey,
    Sender,
    SenderKind,
    SimulatedInbound,
    Template,
    TranscriptEntry,
    WebhookEndpoint,
    parse_event,
)
from .http import AsyncHTTPClient


def _path(base: str, object_id: str, *rest: str) -> str:
    """``base/<object_id>/rest...`` with the ID escaped."""
    return "/".join([base, quote(object_id, safe=""), *rest])


class AsyncMessages:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def send(
        self,
        conversation_id: str,
        content: Any,
        *,
        reply_to: str | None = None,
        fallback: Any = None,
        channel_options: Any = None,
        metadata: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Message:
        """Sends into a conversation (the normal reply). ``content`` is a string (a text
        message), a content model or a dict such as ``{"type": "text", "text": "Hi"}``.
        The answer is the queued message; progress arrives as ``message.sent``,
        ``.delivered``, ``.read`` or ``.failed`` events. ``fallback="auto"`` lets Flow
        convert content the channel cannot show; ``reply_to`` makes it an inline reply."""
        res = await self._http.request(
            "POST",
            _path("/v1/conversations", conversation_id, "messages"),
            json=body(
                content=_base.content(content),
                reply_to=reply_to,
                fallback=fallback,
                channel_options=channel_options,
                metadata=metadata,
            ),
            idempotency=idempotency_key,
        )
        return parse(Message, res)

    async def start(
        self,
        *,
        sender: str,
        to: Any,
        content: Any,
        fallback: Any = None,
        channel_options: Any = None,
        metadata: Mapping[str, Any] | None = None,
        consent: Any = None,
        idempotency_key: str | None = None,
    ) -> Message:
        """Starts a conversation from one of your senders. ``to`` is a contact ID
        (``ct_...``), a phone number (``+1...``) or a recipient dict. Spends the sender's
        new-contact budget; on WhatsApp outside the window only a template goes. In test
        mode ``to`` must be a contact who joined the sandbox through your app."""
        res = await self._http.request(
            "POST",
            "/v1/messages",
            json=body(
                sender=sender,
                to=_base.recipient(to),
                content=_base.content(content),
                fallback=fallback,
                channel_options=channel_options,
                metadata=metadata,
                consent=consent,
            ),
            idempotency=idempotency_key,
        )
        return parse(Message, res)

    async def retrieve(self, message_id: str) -> Message:
        """One message, inbound or outbound, with its current status."""
        return parse(Message, await self._http.request("GET", _path("/v1/messages", message_id)))

    async def edit(self, message_id: str, content: Any) -> Message:
        """Replaces the text of one of your sent messages (Telegram). ``content`` is a
        string or text content."""
        res = await self._http.request(
            "PATCH", _path("/v1/messages", message_id), json={"content": _base.content(content)}
        )
        return parse(Message, res)

    async def unsend(self, message_id: str) -> Message:
        """Removes one of your sent messages from the contact's chat (Telegram, within 48 hours)."""
        return parse(Message, await self._http.request("DELETE", _path("/v1/messages", message_id)))


class AsyncConversations:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        sender: str | None = None,
        contact: str | None = None,
        channel: Channel | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> AsyncPager[Conversation]:
        """Your app's conversations in this mode, newest first."""
        q = {"sender": sender, "contact": contact, "channel": channel, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/conversations", q, parser(Conversation))

    async def retrieve(self, conversation_id: str) -> Conversation:
        """One conversation with its window state."""
        return parse(Conversation, await self._http.request("GET", _path("/v1/conversations", conversation_id)))

    def messages(
        self,
        conversation_id: str,
        *,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> AsyncPager[Message]:
        """A conversation's messages, inbound and outbound, newest first."""
        q = {"limit": limit, "after": after, "before": before}
        return self._http.list(_path("/v1/conversations", conversation_id, "messages"), q, parser(Message))

    async def typing(
        self, conversation_id: str, state: Literal["on", "off"] = "on", *, idempotency_key: str | None = None
    ) -> ConversationAction:
        """Shows (``on``) or clears (``off``) the typing indicator. Channels clear it after a few seconds."""
        res = await self._http.request(
            "POST",
            _path("/v1/conversations", conversation_id, "typing"),
            json={"state": state},
            idempotency=idempotency_key,
        )
        return parse(ConversationAction, res)

    async def mark_read(
        self, conversation_id: str, up_to: str | None = None, *, idempotency_key: str | None = None
    ) -> ConversationAction:
        """Marks the contact's messages as read, up to and including ``up_to`` (default: the latest inbound)."""
        res = await self._http.request(
            "POST",
            _path("/v1/conversations", conversation_id, "read"),
            json=body(up_to=up_to),
            idempotency=idempotency_key,
        )
        return parse(ConversationAction, res)


class AsyncCapabilitiesResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def retrieve(self, conversation_id: str) -> Capabilities:
        """What the conversation's channel can show now, and whether its window is open."""
        res = await self._http.request("GET", "/v1/capabilities", query={"conversation": conversation_id})
        return parse(Capabilities, res)


class AsyncFiles:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def upload(
        self,
        file: Any,
        *,
        filename: str | None = None,
        channel: Channel | None = None,
        idempotency_key: str | None = None,
    ) -> File:
        """Uploads media to send later as ``media`` or ``voice`` content by ``file_id``.
        ``file`` is bytes, a binary file object or a path. The answer's ``id``
        (``file_...``) is the ``file_id``; ``channel`` checks the channel's size limit now."""
        name, data = _base.file_part(file, filename)
        form = {k: v for k, v in {"filename": filename, "channel": channel}.items() if v is not None}
        res = await self._http.request(
            "POST",
            "/v1/files",
            files={"file": (name, data)},
            data=form,
            idempotency=idempotency_key,
        )
        return parse(File, res)

    async def download(self, file_id_or_url: str) -> bytes:
        """A file's bytes, by ID or by the URL inbound media carries. Follows the redirect
        to the signed file URL without sending your key there."""
        res = await self._http.send("GET", _path("/v1/files", _base.file_id(file_id_or_url)))
        if res.is_redirect:
            location = res.headers.get("location")
            if not location:
                raise APIError("The file redirect had no Location.", type="api_error", status=res.status_code)
            signed = await self._http.client.get(str(res.url.join(location)), timeout=self._http.options.timeout)
            if not signed.is_success:
                raise APIError(
                    f"Fetching the file answered {signed.status_code}.", type="api_error", status=signed.status_code
                )
            return signed.content
        return res.content


class AsyncSenders:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        channel: Channel | None = None,
        kind: SenderKind | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> AsyncPager[Sender]:
        """Senders your app can use in this mode. Test keys see the shared sandbox senders,
        each with the link and ``join_code`` a person uses to join your app."""
        q = {"channel": channel, "kind": kind, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/senders", q, parser(Sender))

    async def retrieve(self, sender_id: str) -> Sender:
        """One sender with its status and limits."""
        return parse(Sender, await self._http.request("GET", _path("/v1/senders", sender_id)))

    async def request(
        self,
        *,
        channel: Channel,
        display_name: str | None = None,
        country: str | None = None,
        telegram_bot_token: str | None = None,
        idempotency_key: str | None = None,
    ) -> Sender:
        """Requests a dedicated sender (live keys). A Telegram bot connects at once with ``telegram_bot_token``."""
        res = await self._http.request(
            "POST",
            "/v1/senders",
            json=body(
                channel=channel, display_name=display_name, country=country, telegram_bot_token=telegram_bot_token
            ),
            idempotency=idempotency_key,
        )
        return parse(Sender, res)

    async def disconnect(self, sender_id: str) -> Sender:
        """Disconnects one of your Telegram bots (live keys): removes its webhook and token
        and retires the sender (status ``banned``)."""
        return parse(Sender, await self._http.request("DELETE", _path("/v1/senders", sender_id)))


class AsyncTemplates:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        sender: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> AsyncPager[Template]:
        """WhatsApp templates of your senders, newest first."""
        q = {"sender": sender, "status": status, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/templates", q, parser(Template))

    async def create(self, params: Mapping[str, Any] | Any, *, idempotency_key: str | None = None) -> Template:
        """Submits a WhatsApp template for review (a ``TemplateCreateRequest`` or a dict)."""
        res = await self._http.request(
            "POST", "/v1/templates", json=_base.jsonable(params), idempotency=idempotency_key
        )
        return parse(Template, res)

    async def retrieve(self, template_id: str) -> Template:
        return parse(Template, await self._http.request("GET", _path("/v1/templates", template_id)))

    async def delete(self, template_id: str) -> Deleted:
        return parse(Deleted, await self._http.request("DELETE", _path("/v1/templates", template_id)))


class AsyncWebhookEndpoints:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    def list(
        self, *, limit: int | None = None, after: str | None = None, before: str | None = None
    ) -> AsyncPager[WebhookEndpoint]:
        q = {"limit": limit, "after": after, "before": before}
        return self._http.list("/v1/webhook_endpoints", q, parser(WebhookEndpoint))

    async def create(
        self,
        *,
        url: str,
        events: Sequence[EventType],
        description: str | None = None,
        idempotency_key: str | None = None,
    ) -> WebhookEndpoint:
        """Registers an HTTPS URL for the listed event types. The answer's ``secret``
        (``whsec_...``) is shown only this once."""
        res = await self._http.request(
            "POST",
            "/v1/webhook_endpoints",
            json=body(url=url, events=list(events), description=description),
            idempotency=idempotency_key,
        )
        return parse(WebhookEndpoint, res)

    async def retrieve(self, endpoint_id: str) -> WebhookEndpoint:
        return parse(WebhookEndpoint, await self._http.request("GET", _path("/v1/webhook_endpoints", endpoint_id)))

    async def update(
        self,
        endpoint_id: str,
        *,
        url: str | None = None,
        events: Sequence[EventType] | None = None,
        description: str | None = None,
        enabled: bool | None = None,
    ) -> WebhookEndpoint:
        res = await self._http.request(
            "PATCH",
            _path("/v1/webhook_endpoints", endpoint_id),
            json=body(
                url=url, events=list(events) if events is not None else None, description=description, enabled=enabled
            ),
        )
        return parse(WebhookEndpoint, res)

    async def delete(self, endpoint_id: str) -> Deleted:
        return parse(Deleted, await self._http.request("DELETE", _path("/v1/webhook_endpoints", endpoint_id)))

    async def rotate_secret(
        self, endpoint_id: str, *, overlap_seconds: int | None = None, idempotency_key: str | None = None
    ) -> WebhookEndpoint:
        """Makes a new signing secret, shown only this once. The old secret keeps signing for
        ``overlap_seconds`` (default one day; 0 retires it at once)."""
        res = await self._http.request(
            "POST",
            _path("/v1/webhook_endpoints", endpoint_id, "rotate_secret"),
            json=body(overlap_seconds=overlap_seconds),
            idempotency=idempotency_key,
        )
        return parse(WebhookEndpoint, res)


class AsyncContacts:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        channel: Channel | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> AsyncPager[Contact]:
        q = {"channel": channel, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/contacts", q, parser(Contact))

    async def retrieve(self, contact_id: str) -> Contact:
        return parse(Contact, await self._http.request("GET", _path("/v1/contacts", contact_id)))

    async def delete(self, contact_id: str) -> None:
        """Erases the contact and their data in this app and mode (address, message content,
        files, events, queued sends); it cannot be undone. Safe to retry: a contact already
        deleted answers the same. Emits ``contact.deleted``."""
        await self._http.request("DELETE", _path("/v1/contacts", contact_id))


class AsyncAppResource:
    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def retrieve(self) -> AppContext:
        """The app, account and key making the request, its mode, the sandbox join code and,
        for sandbox apps, what is left of the sandbox ``allowance``."""
        return parse(AppContext, await self._http.request("GET", "/v1/app"))


class AsyncSandbox:
    """Test keys without an account. Needs no API key."""

    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def create_key(self, *, name: str | None = None) -> SandboxKey:
        """Makes a new app with a ``fk_test_`` key, without an account or an API key: the
        first call for an agent that has no key. The answer's ``key`` and ``claim_token``
        are shown only this once: save them (as ``FLOW_MESSAGING_KEY`` and
        ``FLOW_CLAIM_TOKEN``). Its ``senders`` carry the links and join code a person uses
        to join the sandbox. Do not call this when you already have a key."""
        res = await self._http.request("POST", "/v1/sandbox/keys", json=body(name=name), auth=False)
        return parse(SandboxKey, res)


#: Transient poll failures in a row before ``wait_for_key`` gives up.
MAX_POLL_FAILURES = 5


class AsyncDevice:
    """Sign-in from an agent or CLI (the device flow): a person approves in a browser, and
    the agent receives a key. Needs no API key."""

    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def authorize(
        self, *, claim_token: str | None = None, client_name: str | None = None, use_key: bool = True
    ) -> DeviceAuthorization:
        """Starts a sign-in. With ``claim_token`` (or, without one, when this client holds a
        ``fk_test_`` key, sent as the bearer) the person's approval claims that sandbox app:
        its data and keys are kept and its keys stop expiring."""
        bearer = not claim_token and use_key and self._http.options.test_mode
        res = await self._http.request(
            "POST",
            "/v1/device/authorizations",
            json=body(claim_token=claim_token, client_name=client_name),
            auth=bearer,
        )
        return parse(DeviceAuthorization, res)

    async def poll(self, device_code: str) -> DeviceToken:
        """One poll of a sign-in: ``pending``, ``approved`` (with ``key``), ``denied`` or ``expired``."""
        res = await self._http.request(
            "POST", "/v1/device/token", json={"device_code": device_code}, auth=False, max_retries=0
        )
        return parse(DeviceToken, res)

    async def wait_for_key(
        self, device_code: str, *, interval: float = 5, expires_at: datetime | None = None
    ) -> DeviceToken:
        """Polls a started sign-in every ``interval`` seconds until the person approves; a
        429 slows it down by 5 seconds. Returns the approved token (its ``key`` is shown
        once); raises ``DeviceSignInError`` when the person refuses or the codes expire."""
        interval = max(1.0, float(interval))
        wait = interval
        failures = 0
        while True:
            await self._http._sleep(wait)
            wait = interval
            try:
                token = await self.poll(device_code)
            except RateLimitError as e:
                interval += 5
                wait = max(interval, float(e.retry_after or 0))
                continue
            except (APIConnectionError, APIError):
                failures += 1
                if failures >= MAX_POLL_FAILURES:
                    raise
                continue
            failures = 0
            if token.status == "approved":
                return token
            if token.status in ("denied", "expired"):
                raise DeviceSignInError(token.status)
            interval = max(interval, float(token.interval))
            wait = interval
            if expires_at is not None and datetime.now(timezone.utc) >= expires_at:
                raise DeviceSignInError("expired")

    async def sign_in(
        self,
        prompt: Callable[[DeviceAuthorization], Any],
        *,
        claim_token: str | None = None,
        client_name: str | None = None,
        use_key: bool = True,
    ) -> DeviceToken:
        """Runs the whole sign-in: starts it, calls ``prompt`` with the authorization (show
        the person ``verification_uri_complete`` and ``user_code``; never ``device_code``),
        and polls until they approve. Store the answer's ``key`` in place of the sandbox key."""
        auth = await self.authorize(claim_token=claim_token, client_name=client_name, use_key=use_key)
        prompt(auth)
        return await self.wait_for_key(auth.device_code, interval=auth.interval, expires_at=auth.expires_at)


class AsyncTesting:
    """Simulated contacts (test keys only): play the end user's side with no phone and no
    real channel. Each inbound turn reaches your agent as a real ``message.received``; its
    replies pass the real send gate and end ``message.sent`` without touching a network.
    Live keys get ``PermissionDeniedError`` (``code`` ``test_mode_only``)."""

    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    async def create_conversation(
        self,
        channel: Channel,
        *,
        contact: Mapping[str, Any] | None = None,
        name: str | None = None,
        idempotency_key: str | None = None,
    ) -> Conversation:
        """A conversation with a simulated contact on ``telegram``, ``whatsapp``,
        ``imessage`` or ``sms``. Without ``contact`` (an address such as
        ``{"phone": "+15555550100"}``) each call is a fresh conversation."""
        res = await self._http.request(
            "POST",
            "/v1/test/conversations",
            json=body(channel=channel, contact=contact, name=name),
            idempotency=idempotency_key,
        )
        return parse(Conversation, res)

    async def inbound(
        self,
        conversation_id: str,
        content: Any,
        *,
        reply_to: str | None = None,
        idempotency_key: str | None = None,
    ) -> SimulatedInbound:
        """Writes one turn as the simulated contact: a string (text) or content. Media takes a
        ``file_id`` from ``files.upload``. The answer's ``message`` is the ID the
        ``message.received`` event will carry."""
        res = await self._http.request(
            "POST",
            _path("/v1/test/conversations", conversation_id, "inbound"),
            json=body(content=_base.content(content), reply_to=reply_to),
            idempotency=idempotency_key,
        )
        return parse(SimulatedInbound, res)

    def transcript(
        self, conversation_id: str, *, limit: int | None = None, after: str | None = None
    ) -> AsyncPager[TranscriptEntry]:
        """Both sides of a simulated conversation, oldest first; sent messages carry ``shown``."""
        q = {"limit": limit, "after": after}
        return self._http.list(
            _path("/v1/test/conversations", conversation_id, "transcript"), q, parser(TranscriptEntry)
        )


class AsyncEventLog:
    """The event log, read by page (``list``) or live (``stream``, on the client's ``events``)."""

    def __init__(self, http: AsyncHTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        type: EventType | Sequence[EventType] | None = None,
        conversation: str | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> AsyncPager[Event]:
        """The log, oldest first. Pass the last event you processed as ``after`` to catch up."""
        q = {"type": type, "conversation": conversation, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/events", q, parse_event)

    async def retrieve(self, event_id: str) -> Event:
        return parse_event(await self._http.request("GET", _path("/v1/events", event_id)))
