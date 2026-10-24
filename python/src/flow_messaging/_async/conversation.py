"""A handle to act in one conversation. The sync client is generated from this file."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, overload

from ..pagination import AsyncPager
from ..types import ConversationAction, Message, ReadMessage, TypingImessageOptions, TypingMessage

if TYPE_CHECKING:
    from .client import AsyncFlow
    from .resources import MessageModel


class AsyncConversationHandle:
    """A conversation you can act in: one sender talking with one contact (or an iMessage
    group). Get one with ``flow.conversation(...)`` from an ID, a conversation, a
    ``ConversationRef`` or an event."""

    def __init__(self, flow: AsyncFlow, conversation_id: str, *, channel: str | None = None) -> None:
        self._flow = flow
        self.id = conversation_id
        #: The channel, when known from the event or conversation this handle came from.
        self.channel = channel

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, channel={self.channel!r})"

    @overload
    async def send(self, message: str | MessageModel, *, idempotency_key: str | None = None) -> Message: ...

    @overload
    async def send(
        self, message: TypingMessage | ReadMessage, *, idempotency_key: str | None = None
    ) -> ConversationAction: ...

    @overload
    async def send(
        self, message: Mapping[str, Any], *, idempotency_key: str | None = None
    ) -> Message | ConversationAction: ...

    async def send(self, message: Any, *, idempotency_key: str | None = None) -> Message | ConversationAction:
        """Sends one kind object to its kind's endpoint, exactly as given (a string is short
        for ``{"kind": "basic", "text": ...}``); see ``flow.messages.send``. Answers the
        ``Message``, or a ``ConversationAction`` for ``typing`` and ``read``."""
        result: Message | ConversationAction = await self._flow.messages.send(
            self.id, message, idempotency_key=idempotency_key
        )
        return result

    async def typing(
        self,
        *,
        imessage: Mapping[str, Any] | TypingImessageOptions | None = None,
        idempotency_key: str | None = None,
    ) -> ConversationAction:
        """Shows the typing indicator; it clears itself when your next message goes or after
        a few seconds. On iMessage, ``imessage={"duration_seconds": 10}`` sets how long."""
        return await self._flow.conversations.typing(self.id, imessage=imessage, idempotency_key=idempotency_key)

    async def read(self, up_to: str | None = None, *, idempotency_key: str | None = None) -> ConversationAction:
        """Sends a read receipt for the contact's messages (WhatsApp up to ``up_to``, default
        the latest; iMessage the whole conversation)."""
        return await self._flow.conversations.read(self.id, up_to, idempotency_key=idempotency_key)

    async def react(self, message_id: str, emoji: str | None, *, idempotency_key: str | None = None) -> Message:
        """Reacts to a message with one emoji (None removes your reaction)."""
        return await self._flow.messages.reaction(
            self.id, {"message_id": message_id, "emoji": emoji}, idempotency_key=idempotency_key
        )

    def messages(
        self, *, limit: int | None = None, after: str | None = None, before: str | None = None
    ) -> AsyncPager[Message]:
        """This conversation's messages, newest first."""
        return self._flow.conversations.messages(self.id, limit=limit, after=after, before=before)
