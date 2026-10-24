"""Builders for kind objects. Each returns a plain dict with ``kind`` set, ready for
``flow.messages.send``, a webhook reply or the kind's own method
(``flow.messages.buttons(conversation_id, buttons(...))``). They only build dicts:
nothing is converted, so what you build is what the API gets.

.. code-block:: python

    from flow_messaging.content import basic, buttons, image

    flow.messages.send(conversation_id, buttons("Which size?", ["S", "M", "L"]))
    flow.messages.send(conversation_id, image("https://example.com/menu.png", "Today's menu"))
    flow.messages.send(conversation_id, basic("See https://example.com", link_preview=False))
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel

from ._base import jsonable

MediaType = Literal["image", "video", "document", "audio"]
#: A file by HTTPS URL (a string), by ``file_id`` (a string starting ``file_``, from
#: ``files.upload``), or as ``{"url": ...}`` / ``{"file_id": ...}``.
Source = str | Mapping[str, str]


def _source(source: Source) -> dict[str, str]:
    if isinstance(source, str):
        return {"file_id": source} if source.startswith("file_") else {"url": source}
    return dict(source)


def _kind(kind: str, fields: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"kind": kind}
    out.update({k: jsonable(v) for k, v in fields.items() if v is not None})
    return out


def basic(text: str | None = None, **fields: Any) -> dict[str, Any]:
    """A ``basic`` message: text, sent exactly as written, and/or the other fields of a
    basic message (``media``, ``reply_to``, ``link_preview``, ``metadata``, a
    ``telegram`` or ``imessage`` block).

    .. code-block:: python

        basic("Your order shipped.")
        basic("See https://example.com", link_preview=False)
    """
    return _kind("basic", {"text": text, **fields})


def media(
    type: MediaType, source: Source, caption: str | None = None, *, filename: str | None = None, **fields: Any
) -> dict[str, Any]:
    """A ``basic`` message with one file, by HTTPS URL or ``file_id``. ``caption`` is the
    message's ``text``; ``fields`` are the basic message's other fields (``reply_to``, ...)."""
    m: dict[str, Any] = {"type": type, **_source(source)}
    if filename is not None:
        m["filename"] = filename
    return _kind("basic", {"text": caption, "media": m, **fields})


def image(source: Source, caption: str | None = None, **fields: Any) -> dict[str, Any]:
    """A ``basic`` message with an image, by URL or ``file_id``, and an optional caption."""
    return media("image", source, caption, **fields)


def video(source: Source, caption: str | None = None, **fields: Any) -> dict[str, Any]:
    """A ``basic`` message with a video, by URL or ``file_id``, and an optional caption."""
    return media("video", source, caption, **fields)


def audio(source: Source, caption: str | None = None, **fields: Any) -> dict[str, Any]:
    """A ``basic`` message with an audio file, by URL or ``file_id``. For a voice note use ``voice``."""
    return media("audio", source, caption, **fields)


def document(
    source: Source, caption: str | None = None, *, filename: str | None = None, **fields: Any
) -> dict[str, Any]:
    """A ``basic`` message with a document, by URL or ``file_id``, an optional caption and file name."""
    return media("document", source, caption, filename=filename, **fields)


def voice(source: Source, **fields: Any) -> dict[str, Any]:
    """A ``voice`` note, by HTTPS URL or ``file_id`` (``reply_to`` and ``metadata`` optional)."""
    return _kind("voice", {**_source(source), **fields})


def _button(b: str | Mapping[str, Any] | BaseModel) -> Any:
    return {"id": b, "label": b} if isinstance(b, str) else jsonable(b)


def buttons(text: str, items: Sequence[str | Mapping[str, Any] | BaseModel], **fields: Any) -> dict[str, Any]:
    """A ``buttons`` message: text with reply buttons, or with one URL button. A string
    becomes a reply button whose id and label are that string. A tap arrives as
    ``message.received`` with ``button_reply`` content carrying the button's ``id``.
    ``fields`` are the other fields (``header``, ``reply_to``, ``telegram``, ``metadata``)."""
    return _kind("buttons", {"text": text, "buttons": [_button(b) for b in items], **fields})


def list_message(
    text: str, button: str, rows: Sequence[Mapping[str, Any] | BaseModel], **fields: Any
) -> dict[str, Any]:
    """A WhatsApp ``list`` message: ``text``, the menu button's label and its rows, given
    as sections (each with ``rows``) or, for one section without a title, as rows. A tap
    arrives as ``button_reply`` with the row's ``id``.

    .. code-block:: python

        list_message("Which size?", "Sizes", [{"id": "s", "title": "Small"}, {"id": "m", "title": "Medium"}])
    """
    items = [jsonable(r) for r in rows]
    sections = items if items and "rows" in items[0] else [{"rows": items}]
    return _kind("list", {"text": text, "button": button, "sections": sections, **fields})


def carousel(text: str, cards: Sequence[Mapping[str, Any] | BaseModel], **fields: Any) -> dict[str, Any]:
    """A WhatsApp ``carousel``: text and 2 to 10 cards, each with an image or video
    ``header`` and ``buttons``."""
    return _kind("carousel", {"text": text, "cards": [jsonable(c) for c in cards], **fields})


def template(
    template_id: str, language: str, params: Mapping[str, Any] | BaseModel | None = None, **fields: Any
) -> dict[str, Any]:
    """A WhatsApp ``template`` (to start a conversation, or to write after the 24-hour window)."""
    return _kind("template", {"template_id": template_id, "language": language, "params": params, **fields})


def location(
    lat: float, lng: float, *, name: str | None = None, address: str | None = None, **fields: Any
) -> dict[str, Any]:
    """A ``location``: a point, with an optional place name and address."""
    return _kind("location", {"lat": lat, "lng": lng, "name": name, "address": address, **fields})


def contact_card(
    name: str, *, phones: Sequence[str] | None = None, emails: Sequence[str] | None = None, **fields: Any
) -> dict[str, Any]:
    """A ``contact_card``. Telegram needs at least one phone."""
    return _kind(
        "contact_card",
        {
            "name": name,
            "phones": None if phones is None else [*phones],
            "emails": None if emails is None else [*emails],
            **fields,
        },
    )


def effect(text: str, name: str, **fields: Any) -> dict[str, Any]:
    """An iMessage ``effect``: text sent with a screen or bubble effect (``"confetti"``,
    ``"slam"``, ...). iMessage only."""
    return _kind("effect", {"text": text, "effect": name, **fields})


def reaction(message_id: str, emoji: str | None, **fields: Any) -> dict[str, Any]:
    """A ``reaction`` to a message: one emoji, or None to remove yours."""
    out = _kind("reaction", {"message_id": message_id, **fields})
    out["emoji"] = emoji
    return out


def content_text(content: Any) -> str:
    """The text a person would read in a message's content (a model or a dict): its text
    (a media caption included), a voice note's transcript, a tapped button's label, a
    place's name. ``""`` when there is none.

    .. code-block:: python

        said = content_text(event.data.message.content)
    """
    if content is None:
        return ""
    c = content.model_dump() if isinstance(content, BaseModel) else dict(content)
    kind = c.get("kind")
    if kind in ("basic", "buttons", "list", "carousel", "effect", "edit"):
        return str(c.get("text") or "")
    if kind == "voice":
        return str(c.get("transcript") or "")
    if kind == "button_reply":
        return str(c.get("label") or "")
    if kind == "location":
        return ", ".join(str(x) for x in (c.get("name"), c.get("address")) if x)
    if kind == "contact_card":
        return str(c.get("name") or "")
    if kind == "file_blocked":
        return str(c.get("caption") or "")
    return ""


__all__ = [
    "MediaType",
    "Source",
    "audio",
    "basic",
    "buttons",
    "carousel",
    "contact_card",
    "content_text",
    "document",
    "effect",
    "image",
    "list_message",
    "location",
    "media",
    "reaction",
    "template",
    "video",
    "voice",
]
