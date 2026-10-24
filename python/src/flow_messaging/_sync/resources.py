# Generated from src/flow_messaging/_async/resources.py by python/scripts/generate.py. Do not edit.
"""The API's resources, one class each, mirroring the endpoints in the spec. The sync
client is generated from this file."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, overload
from urllib.parse import quote

from .. import _base
from .._base import body, parse, parser
from ..errors import APIConnectionError, APIError, DeviceSignInError, RateLimitError
from ..pagination import Pager
from ..types import (
    AppContext,
    BasicMessage,
    ButtonsMessage,
    CarouselMessage,
    Channel,
    Contact,
    ContactCardMessage,
    Conversation,
    ConversationAction,
    Deleted,
    DeviceAuthorization,
    DeviceToken,
    EditMessage,
    EffectMessage,
    Event,
    EventType,
    File,
    ListMessage,
    LocationMessage,
    Message,
    ReactionMessage,
    ReadMessage,
    SandboxKey,
    Sender,
    SenderKind,
    SimulatedInbound,
    Template,
    TemplateMessage,
    TranscriptEntry,
    TypingMessage,
    UnsendMessage,
    VoiceMessage,
    WebhookEndpoint,
    parse_event,
)
from .http import HTTPClient


def _path(base: str, object_id: str, *rest: str) -> str:
    """``base/<object_id>/rest...`` with the ID escaped."""
    return "/".join([base, quote(object_id, safe=""), *rest])


#: The endpoint of each kind sent with ``POST /v1/conversations/{id}/<path>``.
KIND_PATHS: dict[str, str] = {
    "basic": "basic",
    "voice": "voice",
    "buttons": "buttons",
    "list": "list",
    "carousel": "carousel",
    "template": "template",
    "contact_card": "contact-card",
    "location": "location",
    "effect": "effect",
    "reaction": "reaction",
}
#: Kinds ``send`` takes besides those: the conversation actions and the changes to a sent message.
OTHER_SENDABLE_KINDS = ("typing", "read", "edit", "unsend")

#: A message model ``send`` answers with a ``Message`` for.
MessageModel = (
    BasicMessage
    | VoiceMessage
    | ButtonsMessage
    | ListMessage
    | CarouselMessage
    | TemplateMessage
    | ContactCardMessage
    | LocationMessage
    | EffectMessage
    | ReactionMessage
    | EditMessage
    | UnsendMessage
)


def _sendable_kind(obj: Mapping[str, Any]) -> str:
    kind = obj.get("kind")
    if kind in KIND_PATHS or kind in OTHER_SENDABLE_KINDS:
        return str(kind)
    known = ", ".join([*KIND_PATHS, *OTHER_SENDABLE_KINDS])
    if kind is None:
        raise ValueError(f"The message has no `kind`: give one of {known}, or pass a string for a basic message.")
    if kind in ("button_reply", "file_blocked"):
        raise ValueError(f"`{kind}` is a kind Flow receives, never one you send.")
    raise ValueError(f"Unknown kind {kind!r}: give one of {known}.")


def _target(obj: Mapping[str, Any]) -> str:
    message_id = obj.get("message_id")
    if not isinstance(message_id, str) or not message_id:
        raise ValueError(f"An `{obj.get('kind')}` message needs the `message_id` of the message it changes.")
    return message_id


class Messages:
    """Sending and changing messages: one method per kind (``basic``, ``buttons``, ...),
    each posting to that kind's endpoint exactly what it is given, and ``send``, which
    picks the endpoint from the message's ``kind``. Flow never converts a message: a
    kind or field the conversation's channel does not take raises
    ``UnsupportedContentError`` (``param`` names it, ``hint`` says what to send instead)."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def _post(
        self, conversation_id: str, path: str, message: Any, fields: Mapping[str, Any], idempotency_key: str | None
    ) -> Message:
        res = self._http.request(
            "POST",
            _path("/v1/conversations", conversation_id, path),
            json=_base.fields(message, fields),
            idempotency=idempotency_key,
        )
        return parse(Message, res)

    def basic(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends text, or one media file with an optional caption, on every channel
        (``POST /v1/conversations/{id}/basic``). The body is ``message`` (a dict or a
        model, such as ``content.image(...)``) with the keyword fields laid over it:
        ``basic(id, text="Hi")``, ``basic(id, text="See https://example.com", link_preview=False)``.
        The text is sent exactly as written: no markdown."""
        return self._post(conversation_id, "basic", message, fields, idempotency_key)

    def voice(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends a voice note by ``url`` or ``file_id`` (Telegram, WhatsApp, iMessage)."""
        return self._post(conversation_id, "voice", message, fields, idempotency_key)

    def buttons(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends text with buttons (Telegram, WhatsApp). On WhatsApp 1 to 3 reply buttons or
        one URL button; send a ``list`` for more choices. A tap arrives as ``button_reply``."""
        return self._post(conversation_id, "buttons", message, fields, idempotency_key)

    def list(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends a WhatsApp list message: ``text``, the menu ``button``'s label and its
        ``sections`` of rows. A tap on a row arrives as ``button_reply`` with the row's ``id``."""
        return self._post(conversation_id, "list", message, fields, idempotency_key)

    def carousel(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends a WhatsApp carousel: ``text`` and 2 to 10 ``cards``."""
        return self._post(conversation_id, "carousel", message, fields, idempotency_key)

    def template(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends an approved WhatsApp template (``template_id``, ``language``, ``params``):
        the only kind WhatsApp delivers outside its 24-hour window."""
        return self._post(conversation_id, "template", message, fields, idempotency_key)

    def contact_card(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends a contact card (Telegram, WhatsApp; Telegram needs at least one phone)."""
        return self._post(conversation_id, "contact-card", message, fields, idempotency_key)

    def location(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends a place: ``lat``, ``lng`` and optionally ``name`` and ``address`` (Telegram, WhatsApp)."""
        return self._post(conversation_id, "location", message, fields, idempotency_key)

    def effect(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Sends iMessage text with a screen or bubble ``effect`` (iMessage only)."""
        return self._post(conversation_id, "effect", message, fields, idempotency_key)

    def reaction(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> Message:
        """Reacts to a message: ``message_id`` and one ``emoji``, or ``emoji=None`` to remove
        your reaction (Telegram, WhatsApp, iMessage)."""
        return self._post(conversation_id, "reaction", message, fields, idempotency_key)

    @overload
    def send(
        self, conversation_id: str, message: str | MessageModel, *, idempotency_key: str | None = None
    ) -> Message: ...

    @overload
    def send(
        self, conversation_id: str, message: TypingMessage | ReadMessage, *, idempotency_key: str | None = None
    ) -> ConversationAction: ...

    @overload
    def send(
        self, conversation_id: str, message: Mapping[str, Any], *, idempotency_key: str | None = None
    ) -> Message | ConversationAction: ...

    def send(
        self, conversation_id: str, message: Any, *, idempotency_key: str | None = None
    ) -> Message | ConversationAction:
        """Sends one kind object to the endpoint of its ``kind``, exactly as given. A string
        is short for ``{"kind": "basic", "text": ...}``. ``typing`` and ``read`` go to the
        conversation's typing and read endpoints and answer a ``ConversationAction``;
        ``edit`` and ``unsend`` change the message named by their ``message_id`` (``PATCH``
        and ``DELETE /v1/messages/{message_id}``). A missing or unknown ``kind`` raises
        ``ValueError`` before any request."""
        obj = _base.kind_object(message)
        kind = _sendable_kind(obj)
        if kind in KIND_PATHS:
            return self._post(conversation_id, KIND_PATHS[kind], obj, {}, idempotency_key)
        if kind in ("typing", "read"):
            return _action(self._http, conversation_id, kind, obj, idempotency_key)
        message_id = _target(obj)
        if kind == "edit":
            return self.edit(message_id, {k: v for k, v in obj.items() if k not in ("kind", "message_id")})
        return self.unsend(message_id)

    def start(
        self,
        *,
        sender: str,
        to: Any,
        message: Any,
        consent: Any = None,
        idempotency_key: str | None = None,
    ) -> Message:
        """Starts a conversation from one of your senders with a ``basic`` or ``template``
        message (a kind object; a string is a basic message's text), sent as one flat body:
        ``{"sender", "to", "kind", ...the message's fields}``. ``to`` is a contact ID
        (``ct_...``), a phone number (``+1...``) or a recipient dict; ``consent`` is for SMS.
        Spends the sender's new-contact budget; on WhatsApp only a template starts one. In
        test mode ``to`` must be a contact who joined the sandbox through your app."""
        obj = _base.kind_object(message)
        if obj.get("kind") is None:
            raise ValueError('A start needs the message\'s `kind`: "basic" or "template".')
        res = self._http.request(
            "POST",
            "/v1/messages",
            json={**body(sender=sender, to=_base.recipient(to), consent=consent), **obj},
            idempotency=idempotency_key,
        )
        return parse(Message, res)

    def retrieve(self, message_id: str) -> Message:
        """One message, inbound or outbound, with its current status."""
        return parse(Message, self._http.request("GET", _path("/v1/messages", message_id)))

    def edit(self, message_id: str, message: Any = None, **fields: Any) -> Message:
        """Replaces the text of one of your sent messages (Telegram; iMessage within 15
        minutes): ``edit(id, text="New")``, with an optional ``telegram`` or ``imessage``
        block. ``message`` may be a string (the new text), a dict or an
        ``EditMessageRequest``."""
        payload = {"text": message} if isinstance(message, str) else message
        res = self._http.request("PATCH", _path("/v1/messages", message_id), json=_base.fields(payload, fields))
        return parse(Message, res)

    def unsend(self, message_id: str) -> Message:
        """Removes one of your sent messages from the contact's chat (Telegram within 48
        hours, iMessage within 2 minutes)."""
        return parse(Message, self._http.request("DELETE", _path("/v1/messages", message_id)))


def _action(
    http: HTTPClient, conversation_id: str, name: str, payload: Mapping[str, Any], idempotency_key: str | None
) -> ConversationAction:
    res = http.request(
        "POST", _path("/v1/conversations", conversation_id, name), json=dict(payload), idempotency=idempotency_key
    )
    return parse(ConversationAction, res)


class Conversations:
    def __init__(self, http: HTTPClient) -> None:
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
    ) -> Pager[Conversation]:
        """Your app's conversations in this mode, newest first."""
        q = {"sender": sender, "contact": contact, "channel": channel, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/conversations", q, parser(Conversation))

    def retrieve(self, conversation_id: str) -> Conversation:
        """One conversation with its window state."""
        return parse(Conversation, self._http.request("GET", _path("/v1/conversations", conversation_id)))

    def messages(
        self,
        conversation_id: str,
        *,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> Pager[Message]:
        """A conversation's messages, inbound and outbound, newest first."""
        q = {"limit": limit, "after": after, "before": before}
        return self._http.list(_path("/v1/conversations", conversation_id, "messages"), q, parser(Message))

    def typing(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> ConversationAction:
        """Shows the typing indicator (Telegram, WhatsApp, iMessage). It clears itself when
        your next message goes or after a few seconds; no channel can clear it on request.
        On iMessage, ``imessage={"duration_seconds": 10}`` sets how long it shows."""
        return _action(self._http, conversation_id, "typing", _base.fields(message, fields), idempotency_key)

    def read(
        self, conversation_id: str, message: Any = None, *, idempotency_key: str | None = None, **fields: Any
    ) -> ConversationAction:
        """Marks the contact's messages as read (WhatsApp, iMessage). On WhatsApp ``up_to``
        names the latest inbound message to mark (default: the latest); iMessage marks the
        whole conversation and refuses ``up_to``."""
        return _action(self._http, conversation_id, "read", _base.fields(message, fields), idempotency_key)


class Files:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def upload(
        self,
        file: Any,
        *,
        filename: str | None = None,
        channel: Channel | None = None,
        idempotency_key: str | None = None,
    ) -> File:
        """Uploads a file to send later by ``file_id``, as a basic message's ``media`` or a voice note.
        ``file`` is bytes, a binary file object or a path. The answer's ``id``
        (``file_...``) is the ``file_id``; ``channel`` checks the channel's size limit now."""
        name, data = _base.file_part(file, filename)
        form = {k: v for k, v in {"filename": filename, "channel": channel}.items() if v is not None}
        res = self._http.request(
            "POST",
            "/v1/files",
            files={"file": (name, data)},
            data=form,
            idempotency=idempotency_key,
        )
        return parse(File, res)

    def download(self, file_id_or_url: str) -> bytes:
        """A file's bytes, by ID or by the URL inbound media carries. Follows the redirect
        to the signed file URL without sending your key there."""
        res = self._http.send("GET", _path("/v1/files", _base.file_id(file_id_or_url)))
        if res.is_redirect:
            location = res.headers.get("location")
            if not location:
                raise APIError("The file redirect had no Location.", type="api_error", status=res.status_code)
            signed = self._http.client.get(str(res.url.join(location)), timeout=self._http.options.timeout)
            if not signed.is_success:
                raise APIError(
                    f"Fetching the file answered {signed.status_code}.", type="api_error", status=signed.status_code
                )
            return signed.content
        return res.content


class Senders:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        channel: Channel | None = None,
        kind: SenderKind | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> Pager[Sender]:
        """Senders your app can use in this mode. Test keys see the shared sandbox senders,
        each with the link and ``join_code`` a person uses to join your app."""
        q = {"channel": channel, "kind": kind, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/senders", q, parser(Sender))

    def retrieve(self, sender_id: str) -> Sender:
        """One sender with its status and limits."""
        return parse(Sender, self._http.request("GET", _path("/v1/senders", sender_id)))

    def request(
        self,
        *,
        channel: Channel,
        display_name: str | None = None,
        country: str | None = None,
        telegram_bot_token: str | None = None,
        whatsapp_phone_number_id: str | None = None,
        whatsapp_business_account_id: str | None = None,
        whatsapp_access_token: str | None = None,
        whatsapp_app_secret: str | None = None,
        whatsapp_registration_pin: str | None = None,
        idempotency_key: str | None = None,
    ) -> Sender:
        """Requests a dedicated sender (live keys).

        A Telegram bot connects at once with ``telegram_bot_token``. Your own WhatsApp number
        connects at once with ``whatsapp_phone_number_id``, ``whatsapp_business_account_id``,
        ``whatsapp_access_token`` and ``whatsapp_app_secret``; the answer's ``setup`` says what
        to enter in your Meta app.
        """
        res = self._http.request(
            "POST",
            "/v1/senders",
            json=body(
                channel=channel,
                display_name=display_name,
                country=country,
                telegram_bot_token=telegram_bot_token,
                whatsapp_phone_number_id=whatsapp_phone_number_id,
                whatsapp_business_account_id=whatsapp_business_account_id,
                whatsapp_access_token=whatsapp_access_token,
                whatsapp_app_secret=whatsapp_app_secret,
                whatsapp_registration_pin=whatsapp_registration_pin,
            ),
            idempotency=idempotency_key,
        )
        return parse(Sender, res)

    def disconnect(self, sender_id: str) -> Sender:
        """Disconnects one of your Telegram bots or WhatsApp numbers (live keys): deletes its
        stored credentials and retires the sender (status ``banned``)."""
        return parse(Sender, self._http.request("DELETE", _path("/v1/senders", sender_id)))


class Templates:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        sender: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> Pager[Template]:
        """WhatsApp templates of your senders, newest first."""
        q = {"sender": sender, "status": status, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/templates", q, parser(Template))

    def create(self, params: Mapping[str, Any] | Any, *, idempotency_key: str | None = None) -> Template:
        """Submits a WhatsApp template for review (a ``TemplateCreateRequest`` or a dict)."""
        res = self._http.request(
            "POST", "/v1/templates", json=_base.jsonable(params), idempotency=idempotency_key
        )
        return parse(Template, res)

    def retrieve(self, template_id: str) -> Template:
        return parse(Template, self._http.request("GET", _path("/v1/templates", template_id)))

    def delete(self, template_id: str) -> Deleted:
        return parse(Deleted, self._http.request("DELETE", _path("/v1/templates", template_id)))


class WebhookEndpoints:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(
        self, *, limit: int | None = None, after: str | None = None, before: str | None = None
    ) -> Pager[WebhookEndpoint]:
        q = {"limit": limit, "after": after, "before": before}
        return self._http.list("/v1/webhook_endpoints", q, parser(WebhookEndpoint))

    def create(
        self,
        *,
        url: str,
        events: Sequence[EventType],
        description: str | None = None,
        idempotency_key: str | None = None,
    ) -> WebhookEndpoint:
        """Registers an HTTPS URL for the listed event types. The answer's ``secret``
        (``whsec_...``) is shown only this once."""
        res = self._http.request(
            "POST",
            "/v1/webhook_endpoints",
            json=body(url=url, events=list(events), description=description),
            idempotency=idempotency_key,
        )
        return parse(WebhookEndpoint, res)

    def retrieve(self, endpoint_id: str) -> WebhookEndpoint:
        return parse(WebhookEndpoint, self._http.request("GET", _path("/v1/webhook_endpoints", endpoint_id)))

    def update(
        self,
        endpoint_id: str,
        *,
        url: str | None = None,
        events: Sequence[EventType] | None = None,
        description: str | None = None,
        enabled: bool | None = None,
    ) -> WebhookEndpoint:
        res = self._http.request(
            "PATCH",
            _path("/v1/webhook_endpoints", endpoint_id),
            json=body(
                url=url, events=list(events) if events is not None else None, description=description, enabled=enabled
            ),
        )
        return parse(WebhookEndpoint, res)

    def delete(self, endpoint_id: str) -> Deleted:
        return parse(Deleted, self._http.request("DELETE", _path("/v1/webhook_endpoints", endpoint_id)))

    def rotate_secret(
        self, endpoint_id: str, *, overlap_seconds: int | None = None, idempotency_key: str | None = None
    ) -> WebhookEndpoint:
        """Makes a new signing secret, shown only this once. The old secret keeps signing for
        ``overlap_seconds`` (default one day; 0 retires it at once)."""
        res = self._http.request(
            "POST",
            _path("/v1/webhook_endpoints", endpoint_id, "rotate_secret"),
            json=body(overlap_seconds=overlap_seconds),
            idempotency=idempotency_key,
        )
        return parse(WebhookEndpoint, res)


class Contacts:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        channel: Channel | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> Pager[Contact]:
        q = {"channel": channel, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/contacts", q, parser(Contact))

    def retrieve(self, contact_id: str) -> Contact:
        return parse(Contact, self._http.request("GET", _path("/v1/contacts", contact_id)))

    def delete(self, contact_id: str) -> None:
        """Erases the contact and their data in this app and mode (address, message content,
        files, events, queued sends); it cannot be undone. Safe to retry: a contact already
        deleted answers the same. Emits ``contact.deleted``."""
        self._http.request("DELETE", _path("/v1/contacts", contact_id))


class AppResource:
    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def retrieve(self) -> AppContext:
        """The app, account and key making the request, its mode, the sandbox join code and,
        for sandbox apps, what is left of the sandbox ``allowance``."""
        return parse(AppContext, self._http.request("GET", "/v1/app"))


class Sandbox:
    """Test keys without an account. Needs no API key."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def create_key(self, *, name: str | None = None) -> SandboxKey:
        """Makes a new app with a ``fk_test_`` key, without an account or an API key: the
        first call for an agent that has no key. The answer's ``key`` and ``claim_token``
        are shown only this once: save them (as ``FLOW_MESSAGING_KEY`` and
        ``FLOW_CLAIM_TOKEN``). Its ``senders`` carry the links and join code a person uses
        to join the sandbox. Do not call this when you already have a key."""
        res = self._http.request("POST", "/v1/sandbox/keys", json=body(name=name), auth=False)
        return parse(SandboxKey, res)


#: Transient poll failures in a row before ``wait_for_key`` gives up.
MAX_POLL_FAILURES = 5


class Device:
    """Sign-in from an agent or CLI (the device flow): a person approves in a browser, and
    the agent receives a key. Needs no API key."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def authorize(
        self, *, claim_token: str | None = None, client_name: str | None = None, use_key: bool = True
    ) -> DeviceAuthorization:
        """Starts a sign-in. With ``claim_token`` (or, without one, when this client holds a
        ``fk_test_`` key, sent as the bearer) the person's approval claims that sandbox app:
        its data and keys are kept and its keys stop expiring."""
        bearer = not claim_token and use_key and self._http.options.test_mode
        res = self._http.request(
            "POST",
            "/v1/device/authorizations",
            json=body(claim_token=claim_token, client_name=client_name),
            auth=bearer,
        )
        return parse(DeviceAuthorization, res)

    def poll(self, device_code: str) -> DeviceToken:
        """One poll of a sign-in: ``pending``, ``approved`` (with ``key``), ``denied`` or ``expired``."""
        res = self._http.request(
            "POST", "/v1/device/token", json={"device_code": device_code}, auth=False, max_retries=0
        )
        return parse(DeviceToken, res)

    def wait_for_key(
        self, device_code: str, *, interval: float = 5, expires_at: datetime | None = None
    ) -> DeviceToken:
        """Polls a started sign-in every ``interval`` seconds until the person approves; a
        429 slows it down by 5 seconds. Returns the approved token (its ``key`` is shown
        once); raises ``DeviceSignInError`` when the person refuses or the codes expire."""
        interval = max(1.0, float(interval))
        wait = interval
        failures = 0
        while True:
            self._http._sleep(wait)
            wait = interval
            try:
                token = self.poll(device_code)
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

    def sign_in(
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
        auth = self.authorize(claim_token=claim_token, client_name=client_name, use_key=use_key)
        prompt(auth)
        return self.wait_for_key(auth.device_code, interval=auth.interval, expires_at=auth.expires_at)


class Testing:
    """Simulated contacts (test keys only): play the end user's side with no phone and no
    real channel. Each inbound turn reaches your agent as a real ``message.received``; its
    replies pass the real send gate and end ``message.sent`` without touching a network.
    Live keys get ``PermissionDeniedError`` (``code`` ``test_mode_only``)."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def create_conversation(
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
        res = self._http.request(
            "POST",
            "/v1/test/conversations",
            json=body(channel=channel, contact=contact, name=name),
            idempotency=idempotency_key,
        )
        return parse(Conversation, res)

    def inbound(
        self,
        conversation_id: str,
        content: Any,
        *,
        reply_to: str | None = None,
        from_: str | None = None,
        idempotency_key: str | None = None,
    ) -> SimulatedInbound:
        """Writes one turn as the simulated contact: a kind object with ``kind`` (``basic``,
        ``voice``, ``location``, ``contact_card``, or ``button_reply`` to tap a button or
        list row: ``{"kind": "button_reply", "message_id": ..., "button_id": ...}``); a
        string is short for ``{"kind": "basic", "text": ...}``. Media takes a ``file_id``
        from ``files.upload``. ``from_`` names the participant in a simulated group. The
        answer's ``message`` is the ID the ``message.received`` event will carry."""
        res = self._http.request(
            "POST",
            _path("/v1/test/conversations", conversation_id, "inbound"),
            json=body(content=_base.kind_object(content), reply_to=reply_to, **{"from": from_}),
            idempotency=idempotency_key,
        )
        return parse(SimulatedInbound, res)

    def transcript(
        self, conversation_id: str, *, limit: int | None = None, after: str | None = None
    ) -> Pager[TranscriptEntry]:
        """Both sides of a simulated conversation, oldest first, each as the ``Message`` it is."""
        q = {"limit": limit, "after": after}
        return self._http.list(
            _path("/v1/test/conversations", conversation_id, "transcript"), q, parser(TranscriptEntry)
        )


class EventLog:
    """The event log, read by page (``list``) or live (``stream``, on the client's ``events``)."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(
        self,
        *,
        type: EventType | Sequence[EventType] | None = None,
        conversation: str | None = None,
        limit: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> Pager[Event]:
        """The log, oldest first. Pass the last event you processed as ``after`` to catch up."""
        q = {"type": type, "conversation": conversation, "limit": limit, "after": after, "before": before}
        return self._http.list("/v1/events", q, parse_event)

    def retrieve(self, event_id: str) -> Event:
        return parse_event(self._http.request("GET", _path("/v1/events", event_id)))
