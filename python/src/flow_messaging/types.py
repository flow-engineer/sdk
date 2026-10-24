"""The API's shapes as Pydantic models, generated from the OpenAPI spec
(``_models.py``; never edit it), plus the unions and closed lists under friendly names.

Every model keeps fields the API adds later (``extra="allow"``). ``Event`` is a
discriminated union on ``type``; ``MessageContent`` (a message's ``content``) and
``OutboundKind`` (one message to send) are discriminated unions on ``kind``. Each
member of ``MessageContent`` is a subclass of its kind's model, so ``isinstance`` checks
read naturally:

.. code-block:: python

    from flow_messaging.types import BasicMessage, ButtonReplyMessage, Event, MessageReceivedEvent

    def on_event(event: Event) -> None:
        if isinstance(event, MessageReceivedEvent):
            content = event.data.message.content
            if isinstance(content, BasicMessage):
                print(content.text)
            elif isinstance(content, ButtonReplyMessage):
                print("tapped", content.button_id)
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
    BasicImessageOptions,
    BasicKind,
    BasicMessage,
    BasicTelegramOptions,
    ButtonReplyMessage,
    ButtonsKind,
    ButtonsMessage,
    ButtonsTelegramOptions,
    Call,
    CallData,
    CallForwarding,
    CallReceivedEvent,
    CarouselCard,
    CarouselKind,
    CarouselMessage,
    ChannelPeople,
    Consent,
    Contact,
    ContactAddress,
    ContactCardKind,
    ContactCardMessage,
    ContactConsent,
    ContactDeletedData,
    ContactDeletedEvent,
    ContactLeftData,
    ContactLeftEvent,
    ContentHeader,
    Conversation,
    ConversationAction,
    ConversationRef,
    ConversationStartedData,
    ConversationStartedEvent,
    ConversationWindowClosingEvent,
    Deleted,
    DeviceAuthorization,
    DeviceToken,
    EditImessageOptions,
    EditMessage,
    EditMessageRequest,
    EditTelegramOptions,
    EffectKind,
    EffectMessage,
    ErrorBody,
    EventBase,
    File,
    FileBlockedMessage,
    Group,
    GroupParticipant,
    ImessageSender,
    ImessageStyle,
    ListKind,
    ListMessage,
    ListRow,
    ListSection,
    LocationKind,
    LocationMessage,
    Media,
    Message,
    MessageContent1,
    MessageContent2,
    MessageContent3,
    MessageContent4,
    MessageContent5,
    MessageContent6,
    MessageContent7,
    MessageContent8,
    MessageContent9,
    MessageContent10,
    MessageContent11,
    MessageContent12,
    MessageContent13,
    MessageContent14,
    MessageContent15,
    MessageContent16,
    MessageDeliveredEvent,
    MessageEventData,
    MessageFailedEvent,
    MessageReadEvent,
    MessageReceivedEvent,
    MessageSentEvent,
    PeopleLimits,
    PeopleWindow,
    QuietHours,
    ReactionAddedEvent,
    ReactionEventData,
    ReactionKind,
    ReactionMessage,
    ReactionRemovedEvent,
    ReactionTelegramOptions,
    ReadKind,
    ReadMessage,
    Recipient,
    ReplyButton,
    SandboxAllowance,
    SandboxKey,
    Sender,
    SenderAddress,
    SenderLimits,
    SenderRequest,
    SenderSetup,
    SenderStatusChangedData,
    SenderStatusChangedEvent,
    SignedInUser,
    SimulatedButtonTap,
    SimulatedInbound,
    SimulatedInboundRequest,
    SmsSegments,
    SmsSender,
    StartBasicMessage,
    StartConversationTarget,
    StartTemplateMessage,
    StreamSendFrame,
    StreamStartFrame,
    Template,
    TemplateButton,
    TemplateButtonParam,
    TemplateCardParams,
    TemplateComponent,
    TemplateCreateRequest,
    TemplateHeaderParam,
    TemplateKind,
    TemplateMessage,
    TemplateParams,
    TemplateStatusChangedData,
    TemplateStatusChangedEvent,
    TestContactAddress,
    TestConversationRequest,
    TestGroupParticipant,
    TestGroupRequest,
    TestTranscript,
    Timing,
    TranscriptEntry,
    TypingEventData,
    TypingImessageOptions,
    TypingKind,
    TypingMessage,
    TypingStartedEvent,
    TypingStoppedEvent,
    UnsendMessage,
    UrlButton,
    VoiceKind,
    VoiceMessage,
    WebhookEndpoint,
    WebhookEndpointCreateRequest,
    WebhookEndpointUpdateRequest,
    WebhookReply,
    WebhookSecretRotateRequest,
    WindowClosingData,
)
from .errors import ErrorType

Channel = Literal["telegram", "whatsapp", "imessage", "sms"]
Mode = Literal["test", "live"]
SenderKind = Literal["shared", "dedicated", "simulated"]
SenderStatus = Literal["pending", "active", "warming_up", "throttled", "flagged", "banned"]
MessageDirection = Literal["in", "out"]
MessageStatus = Literal["received", "queued", "sent", "delivered", "read", "failed", "unsent"]
MessageNetwork = Literal["imessage", "sms", "rcs"]
ConversationType = Literal["direct", "group"]
#: The kinds of message (a closed list). Each kind you send has its own endpoint and
#: model (``BasicMessage``, ``ButtonsMessage``, ...); ``button_reply`` and
#: ``file_blocked`` are inbound only.
MessageKind = Literal[
    "basic",
    "voice",
    "buttons",
    "list",
    "carousel",
    "template",
    "contact_card",
    "location",
    "effect",
    "reaction",
    "typing",
    "read",
    "edit",
    "unsend",
    "button_reply",
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
    "contact.left",
    "call.received",
]

#: A button of a ``buttons`` message or a carousel card: a reply button or a URL button.
Button = ReplyButton | UrlButton

#: A message's ``content``: one kind object, in either direction, with ``kind`` saying
#: which. Each member subclasses its kind's model (the ``basic`` member is a
#: ``BasicKind``, so a ``BasicMessage``; ``button_reply`` a ``ButtonReplyMessage``).
MessageContent = Annotated[
    MessageContent1
    | MessageContent2
    | MessageContent3
    | MessageContent4
    | MessageContent5
    | MessageContent6
    | MessageContent7
    | MessageContent8
    | MessageContent9
    | MessageContent10
    | MessageContent11
    | MessageContent12
    | MessageContent13
    | MessageContent14
    | MessageContent15
    | MessageContent16,
    Field(discriminator="kind"),
]

#: One message to send where no URL names the kind (``messages.send``, a webhook reply
#: piece, a stream ``send`` frame): a kind object with ``kind`` set.
OutboundKind = Annotated[
    BasicKind
    | VoiceKind
    | ButtonsKind
    | ListKind
    | CarouselKind
    | TemplateKind
    | ContactCardKind
    | LocationKind
    | EffectKind
    | ReactionKind
    | TypingKind
    | ReadKind
    | EditMessage
    | UnsendMessage,
    Field(discriminator="kind"),
]

#: The body of ``POST /v0/messages`` (``messages.start``): a ``basic`` or ``template``
#: message with ``sender``, ``to`` and, on SMS, ``consent``, in one flat object.
StartConversationRequest = Annotated[StartBasicMessage | StartTemplateMessage, Field(discriminator="kind")]

#: What a simulated contact sends in one turn (``test.inbound``).
SimulatedInboundContent = Annotated[
    BasicKind | VoiceKind | LocationKind | ContactCardKind | SimulatedButtonTap,
    Field(discriminator="kind"),
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
    | ContactDeletedEvent
    | ContactLeftEvent
    | CallReceivedEvent,
    Field(discriminator="type"),
]

#: Events that happened in a conversation, so their ``conversation`` is set.
MessageEvent = MessageReceivedEvent | MessageSentEvent | MessageDeliveredEvent | MessageReadEvent | MessageFailedEvent

_EVENT: TypeAdapter[Event] = TypeAdapter(Event)
_CONTENT: TypeAdapter[MessageContent] = TypeAdapter(MessageContent)
_OUTBOUND: TypeAdapter[OutboundKind] = TypeAdapter(OutboundKind)


def parse_event(data: Any) -> Event:
    """An event from its JSON (a dict, or a JSON string or bytes)."""
    if isinstance(data, (str, bytes, bytearray)):
        return _EVENT.validate_json(data)
    return _EVENT.validate_python(data)


def parse_content(data: Any) -> MessageContent:
    """A message's content from its JSON (a dict with ``kind``)."""
    return _CONTENT.validate_python(data)


def parse_outbound(data: Any) -> OutboundKind:
    """A kind object to send from its JSON (a dict with ``kind``), checked against its kind's model."""
    return _OUTBOUND.validate_python(data)


__all__ = [
    "Account",
    "AllowanceCount",
    "AllowanceMessages",
    "ApiKey",
    "App",
    "AppContext",
    "AppSettings",
    "BasicImessageOptions",
    "BasicKind",
    "BasicMessage",
    "BasicTelegramOptions",
    "Button",
    "ButtonReplyMessage",
    "ButtonsKind",
    "ButtonsMessage",
    "ButtonsTelegramOptions",
    "Call",
    "CallData",
    "CallForwarding",
    "CallReceivedEvent",
    "CarouselCard",
    "CarouselKind",
    "CarouselMessage",
    "Channel",
    "ChannelPeople",
    "Consent",
    "Contact",
    "ContactAddress",
    "ContactCardKind",
    "ContactCardMessage",
    "ContactConsent",
    "ContactDeletedData",
    "ContactDeletedEvent",
    "ContactLeftData",
    "ContactLeftEvent",
    "ContentHeader",
    "Conversation",
    "ConversationAction",
    "ConversationRef",
    "ConversationStartedData",
    "ConversationStartedEvent",
    "ConversationType",
    "ConversationWindowClosingEvent",
    "Deleted",
    "DeviceAuthorization",
    "DeviceToken",
    "EditImessageOptions",
    "EditMessage",
    "EditMessageRequest",
    "EditTelegramOptions",
    "EffectKind",
    "EffectMessage",
    "ErrorBody",
    "ErrorType",
    "Event",
    "EventBase",
    "EventType",
    "File",
    "FileBlockedMessage",
    "Group",
    "GroupParticipant",
    "ImessageSender",
    "ImessageStyle",
    "ListKind",
    "ListMessage",
    "ListRow",
    "ListSection",
    "LocationKind",
    "LocationMessage",
    "Media",
    "Message",
    "MessageContent",
    "MessageDeliveredEvent",
    "MessageDirection",
    "MessageEvent",
    "MessageEventData",
    "MessageFailedEvent",
    "MessageKind",
    "MessageNetwork",
    "MessageReadEvent",
    "MessageReceivedEvent",
    "MessageSentEvent",
    "MessageStatus",
    "Mode",
    "OutboundKind",
    "PeopleLimits",
    "PeopleWindow",
    "QuietHours",
    "ReactionAddedEvent",
    "ReactionEventData",
    "ReactionKind",
    "ReactionMessage",
    "ReactionRemovedEvent",
    "ReactionTelegramOptions",
    "ReadKind",
    "ReadMessage",
    "Recipient",
    "ReplyButton",
    "SandboxAllowance",
    "SandboxKey",
    "Sender",
    "SenderAddress",
    "SenderKind",
    "SenderLimits",
    "SenderRequest",
    "SenderSetup",
    "SenderStatus",
    "SenderStatusChangedData",
    "SenderStatusChangedEvent",
    "SignedInUser",
    "SimulatedButtonTap",
    "SimulatedInbound",
    "SimulatedInboundContent",
    "SimulatedInboundRequest",
    "SmsSegments",
    "SmsSender",
    "StartBasicMessage",
    "StartConversationRequest",
    "StartConversationTarget",
    "StartTemplateMessage",
    "StreamSendFrame",
    "StreamStartFrame",
    "Template",
    "TemplateButton",
    "TemplateButtonParam",
    "TemplateCardParams",
    "TemplateComponent",
    "TemplateCreateRequest",
    "TemplateHeaderParam",
    "TemplateKind",
    "TemplateMessage",
    "TemplateParams",
    "TemplateStatusChangedData",
    "TemplateStatusChangedEvent",
    "TestContactAddress",
    "TestConversationRequest",
    "TestGroupParticipant",
    "TestGroupRequest",
    "TestTranscript",
    "Timing",
    "TranscriptEntry",
    "TypingEventData",
    "TypingImessageOptions",
    "TypingKind",
    "TypingMessage",
    "TypingStartedEvent",
    "TypingStoppedEvent",
    "UnsendMessage",
    "UrlButton",
    "VoiceKind",
    "VoiceMessage",
    "WebhookEndpoint",
    "WebhookEndpointCreateRequest",
    "WebhookEndpointUpdateRequest",
    "WebhookReply",
    "WebhookSecretRotateRequest",
    "WindowClosingData",
    "parse_content",
    "parse_event",
    "parse_outbound",
]
