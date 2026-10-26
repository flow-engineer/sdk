# Generated from src/flow_messaging/_async/stream.py by python/scripts/generate.py. Do not edit.
"""The live event stream: GET /v0/stream over a WebSocket, resumed with ``after`` on
every reconnect so no event is lost, de-duplicated, with polling of GET /v0/events as
the other transport. The sync client is generated from this file."""

from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Iterator, Callable, Sequence
from time import monotonic
from typing import Any, Literal

from websockets.sync.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed, InvalidStatus, WebSocketException

from .._base import STREAM_HEALTHY_AFTER, Options, stream_backoff
from ..errors import (
    AuthenticationError,
    FlowError,
    InvalidRequestError,
    PermissionDeniedError,
    error_from_body,
)
from ..types import Event, EventType, parse_event
from .http import HTTPClient
from .resources import EventLog

#: Close codes of a refused stream that reconnecting does not fix, and their error types.
REFUSED = {4400: "invalid_request", 4401: "authentication", 4403: "permission"}
_FATAL = (AuthenticationError, PermissionDeniedError, InvalidRequestError)
#: Event IDs remembered to drop repeats (delivery is at least once).
SEEN_MAX = 2000
#: Largest frame accepted, in bytes.
MAX_FRAME = 32 * 1024 * 1024

Status = Literal["open", "reconnecting", "polling"]
OnStatus = Callable[[Status, "str | None"], Any]


class EventStream:
    """A live, resumable stream of events. Iterate it; ``break`` or ``close()`` stops it.
    Use it as a context manager to connect before you announce that you are ready, so no
    event in between is missed. ``last_event_id`` is the last event handed to you: pass it
    as ``after`` next time to resume across restarts."""

    def __init__(
        self,
        http: HTTPClient,
        log: EventLog,
        *,
        types: Sequence[EventType] | None = None,
        after: str | None = None,
        transport: Literal["websocket", "poll"] = "websocket",
        poll_interval: float = 1.0,
        on_status: OnStatus | None = None,
    ) -> None:
        self._http = http
        self._log = log
        self._types = list(types) if types else None
        self._transport = transport
        self._poll_interval = poll_interval
        self._on_status = on_status
        self.last_event_id: str | None = after
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._closed = False
        self._ws: Any = None
        self._pending: Any = None
        #: When the last socket opened (time.monotonic), to tell a healthy connection.
        self._opened_at = 0.0

    @property
    def _options(self) -> Options:
        return self._http.options

    def _status(self, status: Status, detail: str | None = None) -> None:
        if self._on_status is not None:
            self._on_status(status, detail)

    def _fresh(self, event: Event) -> bool:
        if event.id in self._seen:
            return False
        self._seen[event.id] = None
        if len(self._seen) > SEEN_MAX:
            self._seen.popitem(last=False)
        self.last_event_id = event.id
        return True

    def close(self) -> None:
        """Stops the stream; the loop over it ends."""
        self._closed = True
        for ws in (self._ws, self._pending):
            if ws is not None:
                ws.close()
        self._pending = None

    def __enter__(self) -> EventStream:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def open(self) -> None:
        """Connects now instead of on the first iteration, so events that happen after this
        returns are not missed (``with`` / ``async with`` does this). A refused key raises
        here; a network failure is left to the iteration, which reconnects."""
        self._options.require_key()
        if self._transport == "poll" or self._pending is not None or self._closed:
            return
        try:
            self._pending = self._connect()
        except _FATAL:
            raise
        except (OSError, TimeoutError, WebSocketException, FlowError):
            self._pending = None

    def _connect(self) -> Any:
        url = self._options.ws_url("/v0/stream", {"after": self.last_event_id, "type": self._types})
        headers = self._options.headers()
        user_agent = headers.pop("User-Agent")
        try:
            connecting = ws_connect(
                url,
                additional_headers=headers,
                user_agent_header=user_agent,
                open_timeout=self._options.timeout,
                max_size=MAX_FRAME,
            )
            # Entered by hand: the stream owns the socket across iterations and closes it itself.
            ws = connecting.__enter__()
        except InvalidStatus as e:
            raise _handshake_error(e.response.status_code, bytes(e.response.body or b"")) from e
        self._opened_at = monotonic()
        self._status("open", None)
        return ws

    def __iter__(self) -> Iterator[Event]:
        return self._events()

    def _events(self) -> Iterator[Event]:
        self._options.require_key()
        if self._transport == "poll":
            self._status("polling", None)
            for event in self._poll():
                yield event
            return
        # Closes in a row since the last healthy connection. A socket that opens is not yet
        # healthy: a refused stream opens, sends an error frame and closes.
        attempt = 0
        while not self._closed:
            opened = False
            healthy = False
            immediate = False
            code: int | None = None
            retry_after: float | None = None
            reason: str | None = None
            ws: Any = None
            try:
                ws, self._pending = self._pending, None
                if ws is None:
                    ws = self._connect()
                self._ws = ws
                opened = True
                for raw in ws:
                    try:
                        frame = json.loads(raw)
                    except ValueError:
                        continue
                    kind = frame.get("type")
                    if kind == "event" and isinstance(frame.get("event"), dict):
                        healthy = True
                        event = parse_event(frame["event"])
                        if self._fresh(event):
                            yield event
                    elif kind == "reconnect":
                        # The server is draining or the connection reached its lifetime.
                        immediate = True
                        if frame.get("after") and not self.last_event_id:
                            self.last_event_id = frame["after"]
                        break
                    elif kind == "error" and isinstance(frame.get("error"), dict):
                        err = error_from_body(0, frame["error"])
                        if isinstance(err, _FATAL):
                            raise err
                        retry_after = err.retry_after
                if not immediate:  # the server closed it normally (1000 or 1001)
                    code = ws.close_code
                    reason = f"closed {code}" if code else "closed"
            except ConnectionClosed as e:
                code = e.rcvd.code if e.rcvd is not None else None
                if code is not None and code in REFUSED:
                    why = e.rcvd.reason if e.rcvd is not None else ""
                    raise error_from_body(
                        code - 4000,
                        {"type": REFUSED[code], "message": why or f"The stream was refused (close {code})."},
                    ) from e
                reason = f"closed {code}" if code else str(e)
            except _FATAL:
                raise
            except FlowError as e:  # a handshake answered with a status that may clear (429, 5xx)
                reason = f"handshake answered {e.status}"
                retry_after = e.retry_after
            except (OSError, TimeoutError, WebSocketException) as e:
                reason = str(e) or type(e).__name__
            finally:
                self._ws = None
                if ws is not None:
                    ws.close()
            if opened and monotonic() - self._opened_at >= STREAM_HEALTHY_AFTER:
                healthy = True
            if self._closed:
                return
            if not opened:
                # A socket refused before opening may be a bad key: ask over HTTP for the typed error.
                try:
                    self._log.list(limit=1, after=self.last_event_id, type=self._types)
                except _FATAL:
                    raise
                except FlowError as e:
                    if retry_after is None:
                        retry_after = e.retry_after
            if healthy:
                attempt = 0
            if immediate:
                self._status("reconnecting", f"{reason or 'reconnect frame'}; reconnecting now")
                continue
            wait = stream_backoff(attempt, code, retry_after)
            attempt += 1
            self._status("reconnecting", f"{reason}; reconnecting in {wait:.1f} s")
            self._http._sleep(wait)

    def _poll(self) -> Iterator[Event]:
        after = self.last_event_id
        if after is None:
            # Start live, like the socket: skip what is already in the log.
            for event in self._log.list(limit=100, type=self._types):
                after = event.id
        while not self._closed:
            try:
                page = self._log.list(after=after, limit=100, type=self._types)
            except _FATAL:
                raise
            except FlowError as e:
                self._status("reconnecting", str(e))
                self._http._sleep(self._poll_interval)
                continue
            for event in page.data:
                after = event.id
                if self._fresh(event):
                    yield event
                if self._closed:
                    return
            if not page.has_more:
                self._http._sleep(self._poll_interval)


def _handshake_error(status: int, raw: bytes) -> FlowError:
    err_body: Any = None
    try:
        parsed = json.loads(raw or b"{}")
        if isinstance(parsed, dict):
            err_body = parsed.get("error")
    except ValueError:
        err_body = None
    return error_from_body(status, err_body if isinstance(err_body, dict) else None)
