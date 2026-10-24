"""What the sync and async clients share: options, headers, retry policy, encoding."""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from ._constants import (
    API_VERSION,
    DEFAULT_BASE_URL,
    ENV_API_KEY,
    ENV_BASE_URL,
    NO_KEY_HELP,
    SDK_VERSION,
)
from .errors import AuthenticationError, FlowError, error_from_body

M = TypeVar("M", bound=BaseModel)

#: Sentinel for "send no Flow-Version header".
NOT_GIVEN: Any = object()

Query = Mapping[str, Any]


def read_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


class Options:
    """The settings of one client. ``with_options`` copies them with changes."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        flow_version: str | Any | None,
        timeout: float,
        max_retries: int,
        default_headers: Mapping[str, str] | None,
    ) -> None:
        self.api_key = api_key or read_env(ENV_API_KEY)
        self.base_url = (base_url or read_env(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.flow_version: str | None = API_VERSION if flow_version is NOT_GIVEN else flow_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = dict(default_headers or {})

    @property
    def test_mode(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("fk_test_"))

    def require_key(self) -> str:
        if self.api_key:
            return self.api_key
        raise AuthenticationError(
            f"No API key. Pass Flow(api_key=...) or set {ENV_API_KEY}. {NO_KEY_HELP}",
            type="authentication",
        )

    def headers(
        self, extra: Mapping[str, str] | None = None, *, auth: bool = True, sdk: str = "python"
    ) -> dict[str, str]:
        h: dict[str, str] = {}
        if auth:
            h["Authorization"] = f"Bearer {self.require_key()}"
        h["Accept"] = "application/json"
        h["User-Agent"] = f"flow-messaging-{sdk}/{SDK_VERSION}"
        h.update(self.default_headers)
        if self.flow_version:
            h["Flow-Version"] = self.flow_version
        if extra:
            h.update(extra)
        return h

    def url(self, path: str) -> str:
        return self.base_url + path

    def ws_url(self, path: str, query: Query | None = None) -> str:
        url = httpx.URL(self.base_url + path, params=encode_query(query))
        scheme = "wss" if url.scheme == "https" else "ws"
        return str(url.copy_with(scheme=scheme))


def encode_query(query: Query | None) -> list[tuple[str, str | int | float | bool | None]]:
    """Query parameters as pairs: None dropped, sequences repeated, booleans lower case."""
    out: list[tuple[str, str | int | float | bool | None]] = []
    for k, v in (query or {}).items():
        if v is None:
            continue
        items = v if isinstance(v, (list, tuple)) else [v]
        for item in items:
            if item is None:
                continue
            out.append((k, ("true" if item else "false") if isinstance(item, bool) else str(item)))
    return out


def idempotency_key() -> str:
    return str(uuid.uuid4())


def jsonable(value: Any) -> Any:
    """A request value as JSON: models dumped without the fields left unset, mappings and
    lists walked. An explicit None stays (a reaction's ``emoji: None`` removes it)."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_unset=True, by_alias=True)
    if isinstance(value, Mapping):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def body(**fields: Any) -> dict[str, Any]:
    """A JSON body from keyword arguments, leaving out the ones that are None."""
    return {k: jsonable(v) for k, v in fields.items() if v is not None}


def fields(value: Any, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """A request body from a model or mapping (or None) and keyword fields, as given: the
    fields are laid over it, nothing is converted, and an explicit None stays. A model
    keeps its ``kind`` even when it was left at its default."""
    if value is None:
        out: dict[str, Any] = {}
    elif isinstance(value, BaseModel):
        out = jsonable(value)
        if "kind" in type(value).model_fields and "kind" not in out:
            out["kind"] = value.kind
    elif isinstance(value, Mapping):
        out = jsonable(value)
    else:
        raise TypeError(f"Expected a dict or a model, not {type(value).__name__}.")
    out.update(jsonable(dict(extra or {})))
    return out


def kind_object(value: Any) -> dict[str, Any]:
    """A kind object from a string (short for ``{"kind": "basic", "text": ...}``, the only
    shorthand), a model or a mapping. The object is otherwise sent as given."""
    if isinstance(value, str):
        return {"kind": "basic", "text": value}
    return fields(value)


def error_from_response(response: httpx.Response) -> FlowError:
    err_body: Mapping[str, Any] | None = None
    try:
        parsed = response.json()
        if isinstance(parsed, Mapping) and isinstance(parsed.get("error"), Mapping):
            err_body = parsed["error"]
    except (ValueError, json.JSONDecodeError):
        err_body = None
    return error_from_body(response.status_code, err_body, response.headers)


def retryable(status: int, err: FlowError) -> bool:
    if status in (408, 500, 502, 503, 504):
        # A channel's refusal is an answer, not a transient failure.
        return err.type != "channel_error"
    # The first request with this idempotency key is still running: the same request
    # again, after retry_after, gets its answer. The other idempotency conflicts are bugs.
    if status == 409:
        return err.type == "idempotency_conflict" and err.channel_code == "in_progress"
    # Only the per-key rate limit clears in seconds; send-gate budgets clear in hours.
    return status == 429 and err.type == "rate_limited"


def backoff(attempt: int) -> float:
    """Seconds before retry number ``attempt + 1``: exponential with jitter, at most 8 s."""
    base: float = min(0.5 * 2**attempt, 8.0)
    return base / 2 + random.random() * (base / 2)


def stream_backoff(attempt: int) -> float:
    return float(min(0.5 * 2**attempt, 10.0) * (0.5 + random.random() / 2))


def parse(model: type[M], data: Any) -> M:
    return model.model_validate(data)


def parser(model: type[M]) -> Callable[[Any], M]:
    return model.model_validate


def file_id(file_id_or_url: str) -> str:
    """A file ID from an ID or from a file URL (``.../v1/files/file_...``)."""
    return file_id_or_url.rstrip("/").rsplit("/", 1)[-1] if "/" in file_id_or_url else file_id_or_url


def recipient(to: Any) -> Any:
    """``to`` of a start: a contact ID (``ct_...``), a phone number (``+1...``), a model or a mapping."""
    if isinstance(to, str):
        if to.startswith("ct_"):
            return {"contact": to}
        if to.startswith("+"):
            return {"phone": to}
        raise ValueError(
            "`to` as a string must be a contact ID (ct_...) or an E.164 phone number (+1...); "
            'otherwise pass a mapping such as {"telegram_user_id": "..."} or {"handle": "..."}.'
        )
    return jsonable(to)


def file_part(file: Any, filename: str | None) -> tuple[str, Any]:
    """The multipart ``file`` part: bytes, a binary file object, or a path."""
    if isinstance(file, (str, os.PathLike)):
        path = os.fspath(file)
        with open(path, "rb") as f:
            data = f.read()
        return filename or os.path.basename(path), data
    if isinstance(file, (bytes, bytearray, memoryview)):
        return filename or "file", bytes(file)
    if hasattr(file, "read"):
        name = filename or os.path.basename(getattr(file, "name", "") or "") or "file"
        return name, file.read()
    raise TypeError("file must be bytes, a binary file object, or a path")


Seq = Sequence[str]


async def async_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


def sync_sleep(seconds: float) -> None:
    time.sleep(seconds)
