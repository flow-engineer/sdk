"""Content builders and content_text."""

from __future__ import annotations

from typing import Any

import pytest

from flow_messaging import content_text
from flow_messaging.content import (
    audio,
    buttons,
    contact_card,
    document,
    effect,
    image,
    location,
    markdown,
    media,
    reaction,
    template,
    text,
    video,
    voice,
)
from flow_messaging.types import (
    ButtonsContent,
    MediaContent,
    ReactionContent,
    TextContent,
    parse_content,
)

FILE = "file_01JB8ZD4M6P8R0T2V4X6Z80001"
MSG = "msg_01JB8ZD4M6P8R0T2V4X6Z80001"
TPL = "tpl_01JB8ZD4M6P8R0T2V4X6Z80001"

BUILT: list[tuple[dict[str, Any], dict[str, Any]]] = [
    (text("hi"), {"type": "text", "text": "hi"}),
    (markdown("*hi*"), {"type": "text", "text": "*hi*", "format": "markdown"}),
    (media("image", FILE), {"type": "media", "kind": "image", "file_id": FILE}),
    (
        media("document", "https://example.test/a.pdf", caption="c", filename="a.pdf"),
        {"type": "media", "kind": "document", "url": "https://example.test/a.pdf", "caption": "c", "filename": "a.pdf"},
    ),
    (image(FILE, caption="cat"), {"type": "media", "kind": "image", "file_id": FILE, "caption": "cat"}),
    (video("https://example.test/v.mp4"), {"type": "media", "kind": "video", "url": "https://example.test/v.mp4"}),
    (
        document(FILE, filename="r.pdf", caption="report"),
        {"type": "media", "kind": "document", "file_id": FILE, "caption": "report", "filename": "r.pdf"},
    ),
    (
        audio({"url": "https://example.test/a.mp3"}),
        {"type": "media", "kind": "audio", "url": "https://example.test/a.mp3"},
    ),
    (voice(FILE), {"type": "voice", "file_id": FILE}),
    (voice("https://example.test/v.ogg"), {"type": "voice", "url": "https://example.test/v.ogg"}),
    (
        buttons("Size?", ["S", {"id": "m", "label": "Medium"}]),
        {"type": "buttons", "text": "Size?", "buttons": [{"id": "S", "label": "S"}, {"id": "m", "label": "Medium"}]},
    ),
    (reaction(MSG, "👍"), {"type": "reaction", "message_id": MSG, "emoji": "👍"}),
    (reaction(MSG, None), {"type": "reaction", "message_id": MSG, "emoji": None}),
    (template(TPL, "en"), {"type": "template", "template_id": TPL, "language": "en"}),
    (
        template(TPL, "en", {"body": ["42"]}),
        {"type": "template", "template_id": TPL, "language": "en", "params": {"body": ["42"]}},
    ),
    (location(52.52, 13.405), {"type": "location", "lat": 52.52, "lng": 13.405}),
    (
        location(52.52, 13.405, name="Office", address="Main St 1"),
        {"type": "location", "lat": 52.52, "lng": 13.405, "name": "Office", "address": "Main St 1"},
    ),
    (contact_card("Ada"), {"type": "contact_card", "name": "Ada"}),
    (
        contact_card("Ada", phones=("+15555550100",), emails=["ada@example.test"]),
        {"type": "contact_card", "name": "Ada", "phones": ["+15555550100"], "emails": ["ada@example.test"]},
    ),
    (effect("Party!", "confetti"), {"type": "effect", "text": "Party!", "effect": "confetti"}),
]


@pytest.mark.parametrize(("built", "expected"), BUILT)
def test_builders(built: dict[str, Any], expected: dict[str, Any]) -> None:
    assert built == expected


@pytest.mark.parametrize(("built", "expected"), BUILT)
def test_builders_validate_against_the_models(built: dict[str, Any], expected: dict[str, Any]) -> None:
    parsed = parse_content(built)
    assert parsed.type == built["type"]


def test_parsed_models() -> None:
    assert isinstance(parse_content(text("hi")), TextContent)
    m = parse_content(image(FILE))
    assert isinstance(m, MediaContent) and m.file_id == FILE
    b = parse_content(buttons("x", ["a"]))
    assert isinstance(b, ButtonsContent)
    r = parse_content(reaction(MSG, None))
    assert isinstance(r, ReactionContent) and r.emoji is None


CONTENT_TEXT: list[tuple[dict[str, Any], str]] = [
    ({"type": "text", "text": "hello"}, "hello"),
    ({"type": "effect", "text": "boom", "effect": "slam"}, "boom"),
    ({"type": "buttons", "text": "Pick", "buttons": [{"id": "a", "label": "A"}]}, "Pick"),
    ({"type": "media", "kind": "image", "url": "https://example.test/x.png", "caption": "a cat"}, "a cat"),
    ({"type": "media", "kind": "image", "url": "https://example.test/x.png"}, ""),
    ({"type": "file_blocked", "reason": "malware", "caption": "see this"}, "see this"),
    ({"type": "voice", "url": "https://example.test/v.ogg", "transcript": "call me"}, "call me"),
    ({"type": "voice", "url": "https://example.test/v.ogg"}, ""),
    ({"type": "button_reply", "button_id": "s", "label": "Small"}, "Small"),
    (
        {
            "type": "carousel",
            "text": "Picks",
            "cards": [
                {
                    "header": {"type": "image", "url": "https://example.test/a.jpg"},
                    "buttons": [{"id": "a", "label": "A"}],
                },
                {
                    "header": {"type": "image", "url": "https://example.test/b.jpg"},
                    "buttons": [{"id": "b", "label": "B"}],
                },
            ],
        },
        "Picks",
    ),
    ({"type": "location", "lat": 1.0, "lng": 2.0, "name": "Office", "address": "Main St 1"}, "Office, Main St 1"),
    ({"type": "location", "lat": 1.0, "lng": 2.0, "address": "Main St 1"}, "Main St 1"),
    ({"type": "location", "lat": 1.0, "lng": 2.0}, ""),
    ({"type": "contact_card", "name": "Ada"}, "Ada"),
    ({"type": "reaction", "message_id": MSG, "emoji": "👍"}, ""),
    ({"type": "template", "template_id": TPL, "language": "en"}, ""),
    ({"type": "typing", "state": "on"}, ""),
    ({"type": "read"}, ""),
    ({"type": "unsend", "message_id": MSG}, ""),
    ({"type": "edit", "message_id": MSG, "content": {"type": "text", "text": "x"}}, ""),
]


def test_content_text_cases_cover_every_content_type() -> None:
    from typing import get_args

    from flow_messaging.types import ContentType

    assert {c["type"] for c, _ in CONTENT_TEXT} == set(get_args(ContentType))


@pytest.mark.parametrize(("content", "expected"), CONTENT_TEXT)
def test_content_text_from_dict(content: dict[str, Any], expected: str) -> None:
    assert content_text(content) == expected


@pytest.mark.parametrize(("content", "expected"), CONTENT_TEXT)
def test_content_text_from_model(content: dict[str, Any], expected: str) -> None:
    assert content_text(parse_content(content)) == expected


def test_content_text_none_and_unknown() -> None:
    assert content_text(None) == ""
    assert content_text({"type": "hologram", "text": "x"}) == ""
    assert content_text({}) == ""
