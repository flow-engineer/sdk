"""Builders for the content union. Every send takes a plain string (a text message) or
one of these; they build plain dicts, so the API's shape stays visible.

.. code-block:: python

    from flow_messaging.content import buttons, image, markdown

    flow.messages.send(conversation_id, buttons("Size?", ["S", "M", "L"]), fallback="auto")
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel

MediaKind = Literal["image", "video", "document", "audio"]


def text(value: str) -> dict[str, Any]:
    """Plain text."""
    return {"type": "text", "text": value}


def markdown(value: str) -> dict[str, Any]:
    """Markdown text, shown in each channel's own formatting. Pair with ``fallback="auto"``
    for channels without formatting."""
    return {"type": "text", "text": value, "format": "markdown"}


def _source(source: str | Mapping[str, str]) -> dict[str, str]:
    if isinstance(source, str):
        return {"file_id": source} if source.startswith("file_") else {"url": source}
    return dict(source)


def media(
    kind: MediaKind, source: str | Mapping[str, str], *, caption: str | None = None, filename: str | None = None
) -> dict[str, Any]:
    """An image, video, document or audio file, by HTTPS URL or by ``file_id`` (``file_...``)
    from ``files.upload``."""
    out: dict[str, Any] = {"type": "media", "kind": kind, **_source(source)}
    if caption is not None:
        out["caption"] = caption
    if filename is not None:
        out["filename"] = filename
    return out


def image(source: str | Mapping[str, str], *, caption: str | None = None) -> dict[str, Any]:
    return media("image", source, caption=caption)


def video(source: str | Mapping[str, str], *, caption: str | None = None) -> dict[str, Any]:
    return media("video", source, caption=caption)


def document(
    source: str | Mapping[str, str], *, caption: str | None = None, filename: str | None = None
) -> dict[str, Any]:
    return media("document", source, caption=caption, filename=filename)


def audio(source: str | Mapping[str, str], *, caption: str | None = None) -> dict[str, Any]:
    return media("audio", source, caption=caption)


def voice(source: str | Mapping[str, str]) -> dict[str, Any]:
    """A voice note, by HTTPS URL or ``file_id``."""
    return {"type": "voice", **_source(source)}


def buttons(value: str, items: Sequence[str | Mapping[str, Any]]) -> dict[str, Any]:
    """Text with reply buttons (1 to 10). A tap arrives as ``message.received`` with
    ``button_reply`` content carrying the button's ``id``. A string becomes a button whose
    id and label are that string."""
    return {
        "type": "buttons",
        "text": value,
        "buttons": [{"id": b, "label": b} if isinstance(b, str) else dict(b) for b in items],
    }


def reaction(message_id: str, emoji: str | None) -> dict[str, Any]:
    """React to a message with one emoji, or None to remove your reaction."""
    return {"type": "reaction", "message_id": message_id, "emoji": emoji}


def template(template_id: str, language: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """A WhatsApp template (to start a conversation or write after the 24-hour window)."""
    out: dict[str, Any] = {"type": "template", "template_id": template_id, "language": language}
    if params is not None:
        out["params"] = dict(params)
    return out


def location(lat: float, lng: float, *, name: str | None = None, address: str | None = None) -> dict[str, Any]:
    """A place."""
    out: dict[str, Any] = {"type": "location", "lat": lat, "lng": lng}
    if name is not None:
        out["name"] = name
    if address is not None:
        out["address"] = address
    return out


def contact_card(
    name: str, *, phones: Sequence[str] | None = None, emails: Sequence[str] | None = None
) -> dict[str, Any]:
    """A contact card."""
    out: dict[str, Any] = {"type": "contact_card", "name": name}
    if phones is not None:
        out["phones"] = list(phones)
    if emails is not None:
        out["emails"] = list(emails)
    return out


def effect(value: str, name: str) -> dict[str, Any]:
    """Text with an iMessage effect (other channels need ``fallback="auto"``)."""
    return {"type": "effect", "text": value, "effect": name}


def content_text(content: Any) -> str:
    """The text a person would read in a piece of content (a model or a dict): the text, a
    media caption, a voice note's transcript, a tapped button's label, a place's name.
    ``""`` when there is none."""
    if content is None:
        return ""
    c = content.model_dump() if isinstance(content, BaseModel) else dict(content)
    kind = c.get("type")
    if kind in ("text", "effect", "buttons"):
        return str(c.get("text") or "")
    if kind in ("media", "file_blocked"):
        return str(c.get("caption") or "")
    if kind == "voice":
        return str(c.get("transcript") or "")
    if kind == "button_reply":
        return str(c.get("label") or "")
    if kind == "location":
        return ", ".join(str(x) for x in (c.get("name"), c.get("address")) if x)
    if kind == "contact_card":
        return str(c.get("name") or "")
    return ""
