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
        ("ContentType", types.ContentType),
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


@pytest.mark.parametrize(("name", "union"), [("Event", types.Event), ("Content", types.Content)])
def test_unions_match_spec_one_of(name: str, union: Any) -> None:
    assert union_members(union) == one_of(name)


@pytest.mark.parametrize(("name", "union"), [("Event", types.Event), ("Content", types.Content)])
def test_union_discriminators_match_spec_mapping(name: str, union: Any) -> None:
    mapping = schema(name)["discriminator"]["mapping"]
    members = typing.get_args(typing.get_args(union)[0])
    by_tag = {typing.get_args(m.model_fields["type"].annotation)[0]: m.__name__ for m in members}
    assert by_tag == {tag: ref.rsplit("/", 1)[-1] for tag, ref in mapping.items()}


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
    assert facts()["base_url"] + "/v1/sandbox/keys" in _constants.NO_KEY_HELP


def test_sdk_version_matches_package() -> None:
    assert flow_messaging.__version__ == _constants.SDK_VERSION
    pyproject = SPEC.parents[1] / "python" / "pyproject.toml"
    assert f'version = "{_constants.SDK_VERSION}"' in pyproject.read_text()
