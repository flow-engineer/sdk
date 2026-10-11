# Generated from src/flow_messaging/_async/conversation.py by python/scripts/generate.py. Do not edit.
"""A handle to act in one conversation. The sync client is generated from this file."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal

from ..pagination import Pager
from ..types import ConversationAction, Message

if TYPE_CHECKING:
    from .client import Flow


class ConversationHandle:
    """A conversation you can act in: one sender talking with one contact. Get one with
    ``flow.conversation(...)`` from an ID, a conversation, a ``ConversationRef`` or an event."""

    def __init__(self, flow: Flow, conversation_id: str, *, channel: str | None = None) -> None:
        self._flow = flow
        self.id = conversation_id
        #: The channel, when known from the event or conversation this handle came from.
        self.channel = channel

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, channel={self.channel!r})"

    def send(
        self,
        content: Any,
        *,
        reply_to: str | None = None,
        fallback: Any = None,
        channel_options: Any = None,
        metadata: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Message:
        """Sends one message: a string, or a content model or dict."""
        return self._flow.messages.send(
            self.id,
            content,
            reply_to=reply_to,
            fallback=fallback,
            channel_options=channel_options,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    def typing(self, state: Literal["on", "off"] = "on") -> ConversationAction:
        """Turns the typing indicator on or off."""
        return self._flow.conversations.typing(self.id, state)

    def mark_read(self, up_to: str | None = None) -> ConversationAction:
        """Marks the contact's messages as read, up to ``up_to`` (default: the latest)."""
        return self._flow.conversations.mark_read(self.id, up_to)

    def react(self, message_id: str, emoji: str | None) -> Message:
        """Reacts to a message with one emoji (None removes your reaction)."""
        return self.send({"type": "reaction", "message_id": message_id, "emoji": emoji}, fallback="auto")

    def messages(
        self, *, limit: int | None = None, after: str | None = None, before: str | None = None
    ) -> Pager[Message]:
        """This conversation's messages, newest first."""
        return self._flow.conversations.messages(self.id, limit=limit, after=after, before=before)
