"""Drift guards: the SDK's versions, closed lists, unions and environment names match
the spec (openapi/openapi.yaml) and agents/facts.json."""

from __future__ import annotations

import json
import typing
from functools import cache
from typing import Any

import pytest
import yaml
from conftest import FACTS, SPEC

import flow_messaging
from flow_messaging import _constants, errors, types


@cache
def spec() -> dict[str, Any]:
    return yaml.safe_load(SPEC.read_text())


@cache
def facts() -> dict[str, Any]:
    return json.loads(FACTS.read_text())


def schema(name: str) -> dict[str, Any]:
    return spec()["components"]["schemas"][name]


def test_files_found() -> None:
    assert SPEC.is_file(), SPEC
    assert FACTS.is_file(), FACTS


def test_api_version_matches_spec() -> None:
    assert flow_messaging.API_VERSION == spec()["info"]["version"]


@pytest.mark.parametrize(
    ("name", "literal"),
    [
        ("Channel", types.Channel),
        ("Mode", types.Mode),
        ("SenderKind", types.SenderKind),
        ("SenderStatus", types.SenderStatus),
        ("MessageDirection", types.MessageDirection),
        ("MessageStatus", types.MessageStatus),
        ("MessageKind", types.MessageKind),
        ("MessageNetwork", types.MessageNetwork),
        ("ConversationType", types.ConversationType),
        ("EventType", types.EventType),
        ("ErrorType", errors.ErrorType),
    ],
)
def test_closed_lists_match_spec_enums(name: str, literal: Any) -> None:
    assert list(typing.get_args(literal)) == schema(name)["enum"]


def union_members(annotated: Any) -> list[str]:
    union = typing.get_args(annotated)[0]
    return [m.__name__ for m in typing.get_args(union)]


def one_of(name: str) -> list[str]:
    return [ref["$ref"].rsplit("/", 1)[-1] for ref in schema(name)["oneOf"]]


#: The spec's unions and the SDK's: the members are the spec's schemas, by name.
UNIONS = [
    ("Event", types.Event),
    ("OutboundKind", types.OutboundKind),
    ("StartConversationRequest", types.StartConversationRequest),
    ("SimulatedInboundContent", types.SimulatedInboundContent),
]


@pytest.mark.parametrize(("name", "union"), UNIONS)
def test_unions_match_spec_one_of(name: str, union: Any) -> None:
    assert union_members(union) == one_of(name)


def tag(member: Any, field: str) -> str:
    return str(typing.get_args(member.model_fields[field].annotation)[0])


@pytest.mark.parametrize(("name", "union"), UNIONS)
def test_union_discriminators_match_spec_mapping(name: str, union: Any) -> None:
    field = schema(name)["discriminator"]["propertyName"]
    mapping = schema(name)["discriminator"]["mapping"]
    members = typing.get_args(typing.get_args(union)[0])
    by_tag = {tag(m, field): m.__name__ for m in members}
    assert by_tag == {t: ref.rsplit("/", 1)[-1] for t, ref in mapping.items()}


def test_message_content_matches_spec() -> None:
    """A message's content: the generator names its members MessageContent1..16, each a
    subclass of the schema the spec maps its kind to."""
    mapping = schema("MessageContent")["discriminator"]["mapping"]
    members = typing.get_args(typing.get_args(types.MessageContent)[0])
    by_tag = {tag(m, "kind"): m for m in members}
    assert list(by_tag) == list(mapping) == list(typing.get_args(types.MessageKind))
    for kind, ref in mapping.items():
        assert ref.rsplit("/", 1)[-1] in [c.__name__ for c in by_tag[kind].__mro__], kind


def test_kind_paths_match_spec() -> None:
    """Every POST /v0/conversations/{conversation_id}/<path> has its kind in KIND_PATHS."""
    from flow_messaging._base import KIND_PATHS

    prefix = "/v0/conversations/{conversation_id}/"
    posts = {
        p.removeprefix(prefix)
        for p, ops in spec()["paths"].items()
        if p.startswith(prefix) and "post" in ops and "/" not in p.removeprefix(prefix)
    }
    assert set(KIND_PATHS.values()) == posts
    for kind, path in KIND_PATHS.items():
        assert path == kind.replace("_", "-")
    assert "/v0/capabilities" not in spec()["paths"]


def test_error_classes_cover_every_error_type() -> None:
    assert set(errors._BY_TYPE) == set(typing.get_args(errors.ErrorType))
    for cls in errors._BY_TYPE.values():
        assert issubclass(cls, errors.FlowError)
    # One class per type: no two types share a class.
    assert len(set(errors._BY_TYPE.values())) == len(errors._BY_TYPE)


def test_every_error_class_is_exported() -> None:
    for cls in errors._BY_TYPE.values():
        assert getattr(flow_messaging, cls.__name__) is cls


def test_default_base_url_matches_facts() -> None:
    assert _constants.DEFAULT_BASE_URL == facts()["base_url"]
    assert flow_messaging.DEFAULT_BASE_URL == facts()["base_url"]


@pytest.mark.parametrize(
    ("constant", "fact"),
    [
        ("ENV_API_KEY", "api_key"),
        ("ENV_BASE_URL", "base_url"),
        ("ENV_WEBHOOK_SECRET", "webhook_secret"),
        ("ENV_CLAIM_TOKEN", "claim_token"),
    ],
)
def test_env_names_match_facts(constant: str, fact: str) -> None:
    assert getattr(_constants, constant) == facts()["env"][fact]


def test_no_key_help_names_the_sandbox_endpoint() -> None:
    assert facts()["base_url"] + "/v0/sandbox/keys" in _constants.NO_KEY_HELP


def test_sdk_version_matches_package() -> None:
    assert flow_messaging.__version__ == _constants.SDK_VERSION
    pyproject = SPEC.parents[1] / "python" / "pyproject.toml"
    assert f'version = "{_constants.SDK_VERSION}"' in pyproject.read_text()
