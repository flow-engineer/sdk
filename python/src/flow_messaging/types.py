"""The API's shapes as Pydantic models, generated from the OpenAPI spec
(``_models.py``; never edit it), plus the unions and closed lists under friendly names.

Every model keeps fields the API adds later (``extra="allow"``), and ``Event`` and
``Content`` are discriminated unions on ``type``:

.. code-block:: python

    from flow_messaging.types import Event, MessageReceivedEvent

    def on_event(event: Event) -> None:
        if isinstance(event, MessageReceivedEvent):
            print(event.data.message.content)
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter

from ._models import (
    Account,
    AllowanceCount,
    AllowanceMessages,
    ApiKey,
    App,
    AppContext,
    AppSettings,
    ButtonReplyContent,
    ButtonsContent,
    Capabilities,
    ChannelLimits,
    ChannelOptions,
    Consent,
    Contact,
    ContactAddress,
    ContactCardContent,
    ContactConsent,
    ContactDeletedData,
    ContactDeletedEvent,
    ContentSupport,
    Conversation,
    ConversationAction,
    ConversationRef,
    ConversationStartedData,
    ConversationStartedEvent,
    ConversationWindowClosingEvent,
    Deleted,
    DeliveredAs,
    DeviceAuthorization,
    DeviceToken,
    EditContent,
    EffectContent,
    ErrorBody,
    EventBase,
    File,
    FileBlockedContent,
    LocationContent,
    MediaContent,
    Message,
    MessageDeliveredEvent,
    MessageEventData,
    MessageFailedEvent,
    MessageReadEvent,
    MessageReceivedEvent,
    MessageSentEvent,
    QuietHours,
    ReactionAddedEvent,
    ReactionContent,
    ReactionEventData,
    ReactionRemovedEvent,
    ReadContent,
    Recipient,
    ReplyButton,
    SandboxAllowance,
    SandboxKey,
    Sender,
    SenderAddress,
    SenderLimits,
    SenderStatusChangedData,
    SenderStatusChangedEvent,
    SendMessageRequest,
    SignedInUser,
    SimulatedButtonTap,
    SimulatedInbound,
    SmsSegments,
    SmsSender,
    StartConversationRequest,
    Template,
    TemplateButton,
    TemplateButtonParam,
    TemplateComponent,
    TemplateContent,
    TemplateCreateRequest,
    TemplateHeaderParam,
    TemplateParams,
    TemplateStatusChangedData,
    TemplateStatusChangedEvent,
    TestContactAddress,
    TextContent,
    Timing,
    TranscriptEntry,
    TypingContent,
    TypingEventData,
    TypingStartedEvent,
    TypingStoppedEvent,
    UnsendContent,
    UrlButton,
    VoiceContent,
    WebhookEndpoint,
    WebhookReply,
    WindowClosingData,
    WindowState,
)
from .errors import ErrorType

Channel = Literal["telegram", "whatsapp", "imessage", "sms"]
Mode = Literal["test", "live"]
SenderKind = Literal["shared", "dedicated", "simulated"]
SenderStatus = Literal["pending", "active", "warming_up", "throttled", "flagged", "banned"]
MessageDirection = Literal["in", "out"]
MessageStatus = Literal["received", "queued", "sent", "delivered", "read", "failed", "unsent"]
ContentType = Literal[
    "text",
    "media",
    "voice",
    "buttons",
    "button_reply",
    "reaction",
    "template",
    "location",
    "contact_card",
    "effect",
    "typing",
    "read",
    "edit",
    "unsend",
    "file_blocked",
]
EventType = Literal[
    "message.received",
    "message.sent",
    "message.delivered",
    "message.read",
    "message.failed",
    "reaction.added",
    "reaction.removed",
    "typing.started",
    "typing.stopped",
    "conversation.started",
    "conversation.window_closing",
    "sender.status_changed",
    "template.status_changed",
    "contact.deleted",
]

#: One piece of content, in either direction; ``type`` selects the shape.
Content = Annotated[
    TextContent
    | MediaContent
    | VoiceContent
    | ButtonsContent
    | ButtonReplyContent
    | ReactionContent
    | TemplateContent
    | LocationContent
    | ContactCardContent
    | EffectContent
    | TypingContent
    | ReadContent
    | EditContent
    | UnsendContent
    | FileBlockedContent,
    Field(discriminator="type"),
]

#: One entry in the app's event log; ``type`` selects the shape of ``data``.
Event = Annotated[
    MessageReceivedEvent
    | MessageSentEvent
    | MessageDeliveredEvent
    | MessageReadEvent
    | MessageFailedEvent
    | ReactionAddedEvent
    | ReactionRemovedEvent
    | TypingStartedEvent
    | TypingStoppedEvent
    | ConversationStartedEvent
    | ConversationWindowClosingEvent
    | SenderStatusChangedEvent
    | TemplateStatusChangedEvent
    | ContactDeletedEvent,
    Field(discriminator="type"),
]

#: Events that happened in a conversation, so their ``conversation`` is set.
MessageEvent = MessageReceivedEvent | MessageSentEvent | MessageDeliveredEvent | MessageReadEvent | MessageFailedEvent

_EVENT: TypeAdapter[Event] = TypeAdapter(Event)
_CONTENT: TypeAdapter[Content] = TypeAdapter(Content)


def parse_event(data: Any) -> Event:
    """An event from its JSON (a dict, or a JSON string or bytes)."""
    if isinstance(data, (str, bytes, bytearray)):
        return _EVENT.validate_json(data)
    return _EVENT.validate_python(data)


def parse_content(data: Any) -> Content:
    """A piece of content from its JSON (a dict)."""
    return _CONTENT.validate_python(data)


__all__ = [
    "Account",
    "AllowanceCount",
    "AllowanceMessages",
    "ApiKey",
    "App",
    "AppContext",
    "AppSettings",
    "ButtonReplyContent",
    "ButtonsContent",
    "Capabilities",
    "Channel",
    "ChannelLimits",
    "ChannelOptions",
    "Consent",
    "Contact",
    "ContactAddress",
    "ContactCardContent",
    "ContactConsent",
    "ContactDeletedData",
    "ContactDeletedEvent",
    "Content",
    "ContentSupport",
    "ContentType",
    "Conversation",
    "ConversationAction",
    "ConversationRef",
    "ConversationStartedData",
    "ConversationStartedEvent",
    "ConversationWindowClosingEvent",
    "Deleted",
    "DeliveredAs",
    "DeviceAuthorization",
    "DeviceToken",
    "EditContent",
    "EffectContent",
    "ErrorBody",
    "ErrorType",
    "Event",
    "EventBase",
    "EventType",
    "File",
    "FileBlockedContent",
    "LocationContent",
    "MediaContent",
    "Message",
    "MessageDeliveredEvent",
    "MessageDirection",
    "MessageEvent",
    "MessageEventData",
    "MessageFailedEvent",
    "MessageReadEvent",
    "MessageReceivedEvent",
    "MessageSentEvent",
    "MessageStatus",
    "Mode",
    "QuietHours",
    "ReactionAddedEvent",
    "ReactionContent",
    "ReactionEventData",
    "ReactionRemovedEvent",
    "ReadContent",
    "Recipient",
    "ReplyButton",
    "SandboxAllowance",
    "SandboxKey",
    "SendMessageRequest",
    "Sender",
    "SenderAddress",
    "SenderKind",
    "SenderLimits",
    "SenderStatus",
    "SenderStatusChangedData",
    "SenderStatusChangedEvent",
    "SignedInUser",
    "SimulatedButtonTap",
    "SimulatedInbound",
    "SmsSegments",
    "SmsSender",
    "StartConversationRequest",
    "Template",
    "TemplateButton",
    "TemplateButtonParam",
    "TemplateComponent",
    "TemplateContent",
    "TemplateCreateRequest",
    "TemplateHeaderParam",
    "TemplateParams",
    "TemplateStatusChangedData",
    "TemplateStatusChangedEvent",
    "TestContactAddress",
    "TextContent",
    "Timing",
    "TranscriptEntry",
    "TypingContent",
    "TypingEventData",
    "TypingStartedEvent",
    "TypingStoppedEvent",
    "UnsendContent",
    "UrlButton",
    "VoiceContent",
    "WebhookEndpoint",
    "WebhookReply",
    "WindowClosingData",
    "WindowState",
    "parse_content",
    "parse_event",
]
