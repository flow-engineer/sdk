"""Content builders and content_text."""

from __future__ import annotations

from typing import Any, get_args

import pytest

import flow_messaging.content as content_module
from flow_messaging import content_text
from flow_messaging.content import (
    audio,
    basic,
    buttons,
    carousel,
    contact_card,
    document,
    effect,
    image,
    list_message,
    location,
    media,
    reaction,
    template,
    video,
    voice,
)
from flow_messaging.types import (
    BasicMessage,
    ButtonReplyMessage,
    ButtonsMessage,
    ListMessage,
    MessageKind,
    ReactionMessage,
    VoiceMessage,
    parse_content,
    parse_outbound,
)

FILE = "file_01JB8ZD4M6P8R0T2V4X6Z80001"
MSG = "msg_01JB8ZD4M6P8R0T2V4X6Z80001"
TPL = "tpl_01JB8ZD4M6P8R0T2V4X6Z80001"
CARDS = [
    {"header": {"type": "image", "url": "https://example.test/a.jpg"}, "buttons": [{"id": "a", "label": "A"}]},
    {"header": {"type": "image", "url": "https://example.test/b.jpg"}, "buttons": [{"id": "b", "label": "B"}]},
]

BUILT: list[tuple[dict[str, Any], dict[str, Any]]] = [
    (basic("hi"), {"kind": "basic", "text": "hi"}),
    (
        basic("See https://example.test", link_preview=False, reply_to=MSG),
        {"kind": "basic", "text": "See https://example.test", "link_preview": False, "reply_to": MSG},
    ),
    (media("image", FILE), {"kind": "basic", "media": {"type": "image", "file_id": FILE}}),
    (
        media("document", "https://example.test/a.pdf", "c", filename="a.pdf"),
        {
            "kind": "basic",
            "text": "c",
            "media": {"type": "document", "url": "https://example.test/a.pdf", "filename": "a.pdf"},
        },
    ),
    (image(FILE, "cat"), {"kind": "basic", "text": "cat", "media": {"type": "image", "file_id": FILE}}),
    (
        video("https://example.test/v.mp4"),
        {"kind": "basic", "media": {"type": "video", "url": "https://example.test/v.mp4"}},
    ),
    (
        document(FILE, "report", filename="r.pdf"),
        {"kind": "basic", "text": "report", "media": {"type": "document", "file_id": FILE, "filename": "r.pdf"}},
    ),
    (
        audio({"url": "https://example.test/a.mp3"}),
        {"kind": "basic", "media": {"type": "audio", "url": "https://example.test/a.mp3"}},
    ),
    (voice(FILE), {"kind": "voice", "file_id": FILE}),
    (
        voice("https://example.test/v.ogg", reply_to=MSG),
        {"kind": "voice", "url": "https://example.test/v.ogg", "reply_to": MSG},
    ),
    (
        buttons("Size?", ["S", {"id": "m", "label": "Medium"}]),
        {"kind": "buttons", "text": "Size?", "buttons": [{"id": "S", "label": "S"}, {"id": "m", "label": "Medium"}]},
    ),
    (
        buttons("Track it", [{"url": "https://example.test/t", "label": "Track"}]),
        {"kind": "buttons", "text": "Track it", "buttons": [{"url": "https://example.test/t", "label": "Track"}]},
    ),
    (
        list_message("Which size?", "Sizes", [{"id": "s", "title": "Small"}, {"id": "m", "title": "Medium"}]),
        {
            "kind": "list",
            "text": "Which size?",
            "button": "Sizes",
            "sections": [{"rows": [{"id": "s", "title": "Small"}, {"id": "m", "title": "Medium"}]}],
        },
    ),
    (
        list_message("Pick", "Menu", [{"title": "Drinks", "rows": [{"id": "t", "title": "Tea"}]}]),
        {
            "kind": "list",
            "text": "Pick",
            "button": "Menu",
            "sections": [{"title": "Drinks", "rows": [{"id": "t", "title": "Tea"}]}],
        },
    ),
    (carousel("Picks", CARDS), {"kind": "carousel", "text": "Picks", "cards": CARDS}),
    (reaction(MSG, "👍"), {"kind": "reaction", "message_id": MSG, "emoji": "👍"}),
    (reaction(MSG, None), {"kind": "reaction", "message_id": MSG, "emoji": None}),
    (template(TPL, "en"), {"kind": "template", "template_id": TPL, "language": "en"}),
    (
        template(TPL, "en", {"body": ["42"]}),
        {"kind": "template", "template_id": TPL, "language": "en", "params": {"body": ["42"]}},
    ),
    (location(52.52, 13.405), {"kind": "location", "lat": 52.52, "lng": 13.405}),
    (
        location(52.52, 13.405, name="Office", address="Main St 1"),
        {"kind": "location", "lat": 52.52, "lng": 13.405, "name": "Office", "address": "Main St 1"},
    ),
    (contact_card("Ada"), {"kind": "contact_card", "name": "Ada"}),
    (
        contact_card("Ada", phones=("+15555550100",), emails=["ada@example.test"]),
        {"kind": "contact_card", "name": "Ada", "phones": ["+15555550100"], "emails": ["ada@example.test"]},
    ),
    (effect("Party!", "confetti"), {"kind": "effect", "text": "Party!", "effect": "confetti"}),
]


@pytest.mark.parametrize(("built", "expected"), BUILT)
def test_builders(built: dict[str, Any], expected: dict[str, Any]) -> None:
    assert built == expected


@pytest.mark.parametrize(("built", "expected"), BUILT)
def test_builders_validate_against_the_models(built: dict[str, Any], expected: dict[str, Any]) -> None:
    assert parse_outbound(built).kind == built["kind"]
    assert parse_content(built).kind == built["kind"]


def test_no_text_or_markdown_builders() -> None:
    assert not hasattr(content_module, "text")
    assert not hasattr(content_module, "markdown")


def test_parsed_models_are_the_kinds_models() -> None:
    assert isinstance(parse_content(basic("hi")), BasicMessage)
    m = parse_content(image(FILE))
    assert isinstance(m, BasicMessage) and m.media is not None and m.media.file_id == FILE
    assert isinstance(parse_content(voice(FILE)), VoiceMessage)
    assert isinstance(parse_content(buttons("x", ["a"])), ButtonsMessage)
    assert isinstance(parse_content(list_message("x", "y", [{"id": "a", "title": "A"}])), ListMessage)
    r = parse_content(reaction(MSG, None))
    assert isinstance(r, ReactionMessage) and r.emoji is None
    tap = parse_content({"kind": "button_reply", "button_id": "s", "label": "Small"})
    assert isinstance(tap, ButtonReplyMessage)


CONTENT_TEXT: list[tuple[dict[str, Any], str]] = [
    ({"kind": "basic", "text": "hello"}, "hello"),
    ({"kind": "basic", "text": "a cat", "media": {"type": "image", "url": "https://example.test/x.png"}}, "a cat"),
    ({"kind": "basic", "media": {"type": "image", "url": "https://example.test/x.png"}}, ""),
    ({"kind": "effect", "text": "boom", "effect": "slam"}, "boom"),
    ({"kind": "buttons", "text": "Pick", "buttons": [{"id": "a", "label": "A"}]}, "Pick"),
    (
        {"kind": "list", "text": "Sizes?", "button": "Sizes", "sections": [{"rows": [{"id": "s", "title": "S"}]}]},
        "Sizes?",
    ),
    ({"kind": "carousel", "text": "Picks", "cards": CARDS}, "Picks"),
    ({"kind": "file_blocked", "reason": "malware", "caption": "see this"}, "see this"),
    ({"kind": "voice", "url": "https://example.test/v.ogg", "transcript": "call me"}, "call me"),
    ({"kind": "voice", "url": "https://example.test/v.ogg"}, ""),
    ({"kind": "button_reply", "button_id": "s", "label": "Small"}, "Small"),
    ({"kind": "location", "lat": 1.0, "lng": 2.0, "name": "Office", "address": "Main St 1"}, "Office, Main St 1"),
    ({"kind": "location", "lat": 1.0, "lng": 2.0, "address": "Main St 1"}, "Main St 1"),
    ({"kind": "location", "lat": 1.0, "lng": 2.0}, ""),
    ({"kind": "contact_card", "name": "Ada"}, "Ada"),
    ({"kind": "reaction", "message_id": MSG, "emoji": "👍"}, ""),
    ({"kind": "template", "template_id": TPL, "language": "en"}, ""),
    ({"kind": "typing"}, ""),
    ({"kind": "read"}, ""),
    ({"kind": "unsend", "message_id": MSG}, ""),
    ({"kind": "edit", "message_id": MSG, "text": "fixed"}, "fixed"),
]


def test_content_text_cases_cover_every_kind() -> None:
    assert {c["kind"] for c, _ in CONTENT_TEXT} == set(get_args(MessageKind))


@pytest.mark.parametrize(("content", "expected"), CONTENT_TEXT)
def test_content_text_from_dict(content: dict[str, Any], expected: str) -> None:
    assert content_text(content) == expected


@pytest.mark.parametrize(("content", "expected"), CONTENT_TEXT)
def test_content_text_from_model(content: dict[str, Any], expected: str) -> None:
    assert content_text(parse_content(content)) == expected


def test_content_text_none_and_unknown() -> None:
    assert content_text(None) == ""
    assert content_text({"kind": "hologram", "text": "x"}) == ""
    assert content_text({"type": "text", "text": "old shape"}) == ""
    assert content_text({}) == ""
