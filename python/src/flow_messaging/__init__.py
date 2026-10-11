"""Flow Messaging: let an AI agent talk with people on WhatsApp, Telegram, iMessage and
SMS through one API.

.. code-block:: python

    from flow_messaging import Flow

    flow = Flow()  # reads FLOW_MESSAGING_KEY
    for event in flow.events.stream(types=["message.received"]):
        flow.messages.send(event.conversation.id, "Hello from my agent")
"""

from . import content, types
from ._async.client import AsyncEvents, AsyncFlow
from ._async.conversation import AsyncConversationHandle
from ._async.stream import AsyncEventStream
from ._constants import API_VERSION, DEFAULT_BASE_URL, SDK_VERSION
from ._sync.client import Events, Flow
from ._sync.conversation import ConversationHandle
from ._sync.stream import EventStream
from .content import content_text
from .errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    ChannelError,
    DeviceSignInError,
    FileBlockedError,
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
    WebhookSignatureError,
)
from .pagination import AsyncPage, AsyncPager, Page, Pager
from .types import Event, parse_event
from .webhooks import construct_event, sign_payload, verify_signature, webhook_reply

__version__ = SDK_VERSION

__all__ = [
    "API_VERSION",
    "DEFAULT_BASE_URL",
    "SDK_VERSION",
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AsyncConversationHandle",
    "AsyncEventStream",
    "AsyncEvents",
    "AsyncFlow",
    "AsyncPage",
    "AsyncPager",
    "AuthenticationError",
    "ChannelError",
    "ConversationHandle",
    "DeviceSignInError",
    "Event",
    "EventStream",
    "Events",
    "FileBlockedError",
    "Flow",
    "FlowError",
    "IdempotencyConflictError",
    "InvalidRequestError",
    "NewContactLimitError",
    "NotFoundError",
    "NotImplementedYetError",
    "OutsideWindowError",
    "Page",
    "Pager",
    "PermissionDeniedError",
    "RateLimitError",
    "SenderThrottledError",
    "UnsupportedContentError",
    "WebhookSignatureError",
    "__version__",
    "construct_event",
    "content",
    "content_text",
    "parse_event",
    "sign_payload",
    "types",
    "verify_signature",
    "webhook_reply",
]
