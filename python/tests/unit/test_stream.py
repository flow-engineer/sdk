"""The live event stream: a real local WebSocket server (sync server in a thread, so it
serves both clients), and transport="poll" against a mocked event log. Each WebSocket
case runs for the sync client (Flow) and the async one (AsyncFlow)."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import respx
from conftest import KEY, event_received, evt, page, url
from websockets.exceptions import ConnectionClosed
from websockets.sync.server import Server, ServerConnection, serve

from flow_messaging import (
    API_VERSION,
    AsyncFlow,
    AuthenticationError,
    Flow,
    FlowError,
    InvalidRequestError,
    PermissionDeniedError,
)
from flow_messaging.types import MessageReceivedEvent

#: Upper bound for any wait on a gate, so a failing test cannot hang the suite.
GATE = 5.0

Script = Callable[[ServerConnection], None]


class WSServer:
    """A local WebSocket server. Connection number i runs ``scripts[i]``; any further
    connection is refused with close 4400 so a runaway reconnect fails the test."""

    def __init__(self, scripts: tuple[Script, ...], process_request: Any = None) -> None:
        self.scripts = list(scripts)
        self.paths: list[str] = []
        self.headers: list[Any] = []
        #: Set when a connection that was holding saw the client close it.
        self.closed = threading.Event()
        #: Set when the first connection reached its handler.
        self.connected = threading.Event()
        self._lock = threading.Lock()
        self.server: Server = serve(self._handle, "127.0.0.1", 0, process_request=process_request)
        self.port = self.server.socket.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def _handle(self, ws: ServerConnection) -> None:
        with self._lock:
            i = len(self.paths)
            self.paths.append(ws.request.path)
            self.headers.append(ws.request.headers)
        self.connected.set()
        script = self.scripts[i] if i < len(self.scripts) else close(4400, "unexpected connection")
        script(ws)

    def query(self, i: int) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.paths[i]).query)

    def shutdown(self) -> None:
        self.server.shutdown()
        self._thread.join(GATE)


def frame(event: dict[str, Any]) -> str:
    return json.dumps({"type": "event", "event": event})


def send(*frames: str | dict[str, Any], then: Script | None = None) -> Script:
    """Sends frames, then runs ``then`` (default: return, which closes normally, 1000)."""

    def script(ws: ServerConnection) -> None:
        for f in frames:
            ws.send(f if isinstance(f, str) else json.dumps(f))
        if then is not None:
            then(ws)

    return script


def hold(server_ref: list[WSServer]) -> Script:
    """Keeps the connection open until the client closes it, then sets ``closed``."""

    def script(ws: ServerConnection) -> None:
        try:
            while True:
                ws.recv(timeout=GATE)
        except ConnectionClosed:
            server_ref[0].closed.set()
        except TimeoutError:
            return

    return script


def close(code: int, reason: str = "") -> Script:
    def script(ws: ServerConnection) -> None:
        ws.close(code, reason)

    return script


@pytest.fixture
def servers() -> Iterator[Callable[..., WSServer]]:
    started: list[WSServer] = []

    def start(*scripts: Script, process_request: Any = None) -> WSServer:
        s = WSServer(scripts, process_request)
        started.append(s)
        return s

    yield start
    for s in started:
        s.shutdown()


@dataclass
class Run:
    events: list[Any] = field(default_factory=list)
    error: FlowError | None = None
    sleeps: list[float] = field(default_factory=list)
    statuses: list[tuple[str, str | None]] = field(default_factory=list)
    stream: Any = None


def run(
    mode: str,
    server: WSServer,
    *,
    take: int | None = None,
    wait_closed: bool = False,
    key: str | None = KEY,
    **stream_kw: Any,
) -> Run:
    """Iterates a stream from a client of ``server`` until ``take`` events (then breaks
    out of the loop) or a FlowError. With ``wait_closed`` it then waits for the server to
    see the socket closed."""
    r = Run()

    def on_status(status: str, detail: str | None) -> None:
        r.statuses.append((status, detail))

    if mode == "sync":
        flow = Flow(key, base_url=server.base_url, timeout=GATE)
        flow._http._sleep = r.sleeps.append
        r.stream = flow.events.stream(on_status=on_status, **stream_kw)
        try:
            for event in r.stream:
                r.events.append(event)
                if take is not None and len(r.events) >= take:
                    break
        except FlowError as e:
            r.error = e
        if wait_closed:
            assert server.closed.wait(GATE), "the socket was not closed"
        flow.close()
        return r

    async def main() -> None:
        aflow = AsyncFlow(key, base_url=server.base_url, timeout=GATE)

        async def fake_sleep(seconds: float) -> None:
            r.sleeps.append(seconds)

        aflow._http._sleep = fake_sleep
        r.stream = aflow.events.stream(on_status=on_status, **stream_kw)
        try:
            async for event in r.stream:
                r.events.append(event)
                if take is not None and len(r.events) >= take:
                    break
        except FlowError as e:
            r.error = e
        if wait_closed:
            assert await asyncio.to_thread(server.closed.wait, GATE), "the socket was not closed"
        await aflow.aclose()

    asyncio.run(main())
    return r


MODES = pytest.mark.parametrize("mode", ["sync", "async"])


# WebSocket ----------------------------------------------------------------------


@MODES
def test_request_carries_headers_and_types_not_the_key(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(send(frame(event_received(evt(1))), then=hold(ref)))
    ref.append(server)
    r = run(mode, server, take=1, types=["message.received", "message.sent"])
    assert r.error is None
    headers = server.headers[0]
    assert headers["Authorization"] == f"Bearer {KEY}"
    assert headers["Flow-Version"] == API_VERSION
    assert headers["User-Agent"].startswith("flow-messaging-python/")
    path = server.paths[0]
    assert urlsplit(path).path == "/v0/stream"
    assert server.query(0) == {"type": ["message.received", "message.sent"]}
    assert "fk_" not in path and "key" not in path


@MODES
def test_yields_typed_events_and_tracks_last_event_id(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(send(frame(event_received(evt(1), "one")), frame(event_received(evt(2), "two")), then=hold(ref)))
    ref.append(server)
    r = run(mode, server, take=2)
    assert r.error is None
    assert all(isinstance(e, MessageReceivedEvent) for e in r.events)
    assert [e.data.message.content.text for e in r.events] == ["one", "two"]
    assert r.events[0].conversation is not None
    assert r.stream.last_event_id == evt(2)
    assert ("open", None) in r.statuses


@MODES
def test_after_is_sent_on_the_first_connection(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(send(frame(event_received(evt(8))), then=hold(ref)))
    ref.append(server)
    r = run(mode, server, take=1, after=evt(7))
    assert server.query(0)["after"] == [evt(7)]
    assert r.stream.last_event_id == evt(8)


@MODES
def test_drops_repeated_event_ids_and_ignores_junk_frames(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(
        send(
            frame(event_received(evt(1))),
            "not json",
            frame(event_received(evt(1))),
            {"type": "ack", "id": "x"},
            frame(event_received(evt(2))),
            then=hold(ref),
        )
    )
    ref.append(server)
    r = run(mode, server, take=2)
    assert [e.id for e in r.events] == [evt(1), evt(2)]


@MODES
def test_normal_close_reconnects_with_after_the_last_event(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(
        send(frame(event_received(evt(1))), frame(event_received(evt(2)))),  # then closes 1000
        send(frame(event_received(evt(2))), frame(event_received(evt(3))), then=hold(ref)),
    )
    ref.append(server)
    r = run(mode, server, take=3, types=["message.received"])
    assert r.error is None
    assert [e.id for e in r.events] == [evt(1), evt(2), evt(3)]  # evt 2 again is dropped
    assert len(server.paths) == 2
    assert server.query(1) == {"after": [evt(2)], "type": ["message.received"]}
    # One backoff wait, through the client's _sleep.
    assert len(r.sleeps) == 1 and 0 < r.sleeps[0] <= 10
    assert [s for s, _ in r.statuses] == ["open", "reconnecting", "open"]
    assert r.stream.last_event_id == evt(3)


@MODES
def test_reconnect_frame_reconnects_at_once(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(
        send(frame(event_received(evt(1))), {"type": "reconnect"}, then=hold(ref)),
        send(frame(event_received(evt(2))), then=hold(ref)),
    )
    ref.append(server)
    r = run(mode, server, take=2)
    assert [e.id for e in r.events] == [evt(1), evt(2)]
    assert server.query(1)["after"] == [evt(1)]
    assert r.sleeps == []


@MODES
def test_reconnect_frame_after_is_used_when_nothing_was_yielded(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(
        send({"type": "reconnect", "after": evt(5)}, then=hold(ref)),
        send(frame(event_received(evt(6))), then=hold(ref)),
    )
    ref.append(server)
    r = run(mode, server, take=1)
    assert [e.id for e in r.events] == [evt(6)]
    assert "after" not in server.query(0)
    assert server.query(1)["after"] == [evt(5)]


@MODES
@pytest.mark.parametrize(
    ("code", "cls", "status"),
    [
        (4401, AuthenticationError, 401),
        (4403, PermissionDeniedError, 403),
        (4400, InvalidRequestError, 400),
    ],
)
def test_refused_close_codes_raise_without_reconnecting(
    mode: str, code: int, cls: type[FlowError], status: int, servers: Callable[..., WSServer]
) -> None:
    server = servers(close(code, "refused here"))
    r = run(mode, server)
    assert type(r.error) is cls
    assert r.error.status == status
    assert r.error.message == "refused here"
    assert len(server.paths) == 1
    assert r.sleeps == []


@MODES
def test_refused_close_after_events_still_raises(mode: str, servers: Callable[..., WSServer]) -> None:
    server = servers(send(frame(event_received(evt(1))), then=close(4403)))
    r = run(mode, server)
    assert [e.id for e in r.events] == [evt(1)]
    assert isinstance(r.error, PermissionDeniedError)
    assert "4403" in r.error.message
    assert len(server.paths) == 1


@MODES
def test_error_frame_raises_the_typed_error(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    error_frame = {"type": "error", "error": {"type": "authentication", "message": "The key was revoked."}}
    server = servers(send(error_frame, then=hold(ref)))
    ref.append(server)
    r = run(mode, server)
    assert isinstance(r.error, AuthenticationError)
    assert r.error.message == "The key was revoked."
    assert len(server.paths) == 1
    # The client closed its socket on the way out.
    assert server.closed.wait(GATE)


@MODES
def test_non_fatal_error_frame_is_ignored(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    error_frame = {"type": "error", "error": {"type": "rate_limited", "message": "Slow down."}}
    server = servers(send(error_frame, frame(event_received(evt(1))), then=hold(ref)))
    ref.append(server)
    r = run(mode, server, take=1)
    assert r.error is None
    assert [e.id for e in r.events] == [evt(1)]


@MODES
def test_breaking_out_of_the_loop_closes_the_socket(mode: str, servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(send(frame(event_received(evt(1))), frame(event_received(evt(2))), then=hold(ref)))
    ref.append(server)
    r = run(mode, server, take=1, wait_closed=True)
    assert [e.id for e in r.events] == [evt(1)]
    assert r.stream.last_event_id == evt(1)
    assert len(server.paths) == 1


@MODES
def test_refused_handshake_raises_the_typed_error(mode: str, servers: Callable[..., WSServer]) -> None:
    body = json.dumps({"error": {"type": "authentication", "message": "Unknown key."}})

    def refuse(connection: ServerConnection, request: Any) -> Any:
        return connection.respond(401, body)

    server = servers(process_request=refuse)
    r = run(mode, server)
    assert isinstance(r.error, AuthenticationError)
    assert r.error.message == "Unknown key."
    assert r.sleeps == []


@MODES
def test_without_a_key_iteration_raises_before_connecting(mode: str, servers: Callable[..., WSServer]) -> None:
    server = servers()
    r = run(mode, server, key=None)
    assert isinstance(r.error, AuthenticationError)
    assert server.paths == []


# Connecting eagerly: open() and the context managers --------------------------------


def _sync_flow(server: WSServer, sleeps: list[float]) -> Flow:
    flow = Flow(KEY, base_url=server.base_url, timeout=GATE)
    flow._http._sleep = sleeps.append
    return flow


def _async_flow(server: WSServer, sleeps: list[float]) -> AsyncFlow:
    aflow = AsyncFlow(KEY, base_url=server.base_url, timeout=GATE)

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    aflow._http._sleep = fake_sleep
    return aflow


def _refuse_handshake(connection: ServerConnection, request: Any) -> Any:
    return connection.respond(401, json.dumps({"error": {"type": "authentication", "message": "Unknown key."}}))


def test_with_connects_before_the_first_next(servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(send(frame(event_received(evt(1))), then=hold(ref)))
    ref.append(server)
    sleeps: list[float] = []
    statuses: list[str] = []
    flow = _sync_flow(server, sleeps)
    with flow.events.stream(on_status=lambda s, d: statuses.append(s)) as stream:
        assert server.connected.wait(GATE)
        assert statuses == ["open"]
        it = iter(stream)
        assert next(it).id == evt(1)
        it.close()
    assert len(server.paths) == 1  # the iteration reused the pending connection
    assert statuses == ["open"]
    assert server.closed.wait(GATE)
    flow.close()


async def test_async_with_connects_before_the_first_anext(servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(send(frame(event_received(evt(1))), then=hold(ref)))
    ref.append(server)
    sleeps: list[float] = []
    statuses: list[str] = []
    aflow = _async_flow(server, sleeps)
    async with aflow.events.stream(on_status=lambda s, d: statuses.append(s)) as stream:
        assert await asyncio.to_thread(server.connected.wait, GATE)
        assert statuses == ["open"]
        it = aiter(stream)
        assert (await anext(it)).id == evt(1)
        await it.aclose()
    assert len(server.paths) == 1
    assert statuses == ["open"]
    assert await asyncio.to_thread(server.closed.wait, GATE)
    await aflow.aclose()


def test_with_raises_a_refused_handshake_on_enter(servers: Callable[..., WSServer]) -> None:
    server = servers(process_request=_refuse_handshake)
    flow = _sync_flow(server, [])
    with pytest.raises(AuthenticationError, match="Unknown key"):
        with flow.events.stream():
            pytest.fail("the body ran")
    flow.close()


async def test_async_with_raises_a_refused_handshake_on_enter(servers: Callable[..., WSServer]) -> None:
    server = servers(process_request=_refuse_handshake)
    aflow = _async_flow(server, [])
    with pytest.raises(AuthenticationError, match="Unknown key"):
        async with aflow.events.stream():
            pytest.fail("the body ran")
    await aflow.aclose()


def test_a_4401_close_after_open_raises_on_the_first_next(servers: Callable[..., WSServer]) -> None:
    server = servers(close(4401, "bad key"))
    flow = _sync_flow(server, [])
    with flow.events.stream() as stream:
        with pytest.raises(AuthenticationError, match="bad key"):
            next(iter(stream))
    assert len(server.paths) == 1
    flow.close()


def test_close_before_iterating_closes_the_pending_socket(servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(hold(ref))
    ref.append(server)
    flow = _sync_flow(server, [])
    stream = flow.events.stream()
    stream.open()
    assert server.connected.wait(GATE)
    stream.close()
    assert server.closed.wait(GATE)
    assert list(stream) == []  # a closed stream yields nothing and does not reconnect
    assert len(server.paths) == 1
    flow.close()


async def test_aclose_before_iterating_closes_the_pending_socket(servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(hold(ref))
    ref.append(server)
    aflow = _async_flow(server, [])
    stream = aflow.events.stream()
    await stream.open()
    assert await asyncio.to_thread(server.connected.wait, GATE)
    await stream.aclose()
    assert await asyncio.to_thread(server.closed.wait, GATE)
    assert [e async for e in stream] == []
    assert len(server.paths) == 1
    await aflow.aclose()


def test_with_exit_without_iterating_closes_the_socket(servers: Callable[..., WSServer]) -> None:
    ref: list[WSServer] = []
    server = servers(hold(ref))
    ref.append(server)
    flow = _sync_flow(server, [])
    with flow.events.stream():
        assert server.connected.wait(GATE)
    assert server.closed.wait(GATE)
    flow.close()


# Polling --------------------------------------------------------------------------


def _params(route: respx.Route, i: int) -> dict[str, list[str]]:
    return parse_qs(route.calls[i].request.url.query.decode())


def _poll_responses() -> list[httpx.Response]:
    return [
        httpx.Response(200, json=page([event_received(evt(2))], has_more=True)),
        httpx.Response(200, json=page([event_received(evt(3))])),
        httpx.Response(200, json=page([])),
        httpx.Response(200, json=page([event_received(evt(4))])),
    ]


def _assert_polled(route: respx.Route) -> None:
    assert route.call_count == 4
    afters = [_params(route, i)["after"] for i in range(4)]
    assert afters == [[evt(1)], [evt(2)], [evt(3)], [evt(3)]]
    for i in range(4):
        assert _params(route, i)["limit"] == ["100"]
        assert _params(route, i)["type"] == ["message.received", "message.sent"]
        assert route.calls[i].request.headers["Authorization"] == f"Bearer {KEY}"


def test_poll_pages_the_event_log_after_the_cursor(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v0/events")).mock(side_effect=_poll_responses())
    stream = flow.events.stream(
        transport="poll", after=evt(1), poll_interval=2.5, types=["message.received", "message.sent"]
    )
    slept: list[float] = []

    def fake_sleep(seconds: float) -> None:
        slept.append(seconds)
        if len(slept) == 3:
            stream.close()

    flow._http._sleep = fake_sleep
    statuses: list[str] = []
    stream._on_status = lambda s, d: statuses.append(s)
    got = [e.id for e in stream]
    assert got == [evt(2), evt(3), evt(4)]
    # No wait after a page with has_more; poll_interval after each last page.
    assert slept == [2.5, 2.5, 2.5]
    assert statuses == ["polling"]
    assert stream.last_event_id == evt(4)
    _assert_polled(route)


async def test_poll_pages_the_event_log_after_the_cursor_async(aflow: AsyncFlow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v0/events")).mock(side_effect=_poll_responses())
    stream = aflow.events.stream(
        transport="poll", after=evt(1), poll_interval=2.5, types=["message.received", "message.sent"]
    )
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)
        if len(slept) == 3:
            await stream.aclose()

    aflow._http._sleep = fake_sleep
    got = [e.id async for e in stream]
    assert got == [evt(2), evt(3), evt(4)]
    assert slept == [2.5, 2.5, 2.5]
    _assert_polled(route)


def _live_start_responses() -> list[httpx.Response]:
    return [
        httpx.Response(200, json=page([event_received(evt(1)), event_received(evt(2))], has_more=True)),
        httpx.Response(200, json=page([event_received(evt(3))])),
        httpx.Response(200, json=page([event_received(evt(4))])),
    ]


def _assert_live_start(route: respx.Route) -> None:
    assert "after" not in _params(route, 0)
    assert _params(route, 1)["after"] == [evt(2)]
    assert _params(route, 2)["after"] == [evt(3)]


def test_poll_without_after_skips_what_is_already_in_the_log(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v0/events")).mock(side_effect=_live_start_responses())
    stream = flow.events.stream(transport="poll")

    def fake_sleep(seconds: float) -> None:
        stream.close()

    flow._http._sleep = fake_sleep
    assert [e.id for e in stream] == [evt(4)]
    _assert_live_start(route)


async def test_poll_without_after_skips_what_is_already_in_the_log_async(
    aflow: AsyncFlow, mock: respx.MockRouter
) -> None:
    route = mock.get(url("/v0/events")).mock(side_effect=_live_start_responses())
    stream = aflow.events.stream(transport="poll")

    async def fake_sleep(seconds: float) -> None:
        await stream.aclose()

    aflow._http._sleep = fake_sleep
    assert [e.id async for e in stream] == [evt(4)]
    _assert_live_start(route)


def test_poll_waits_out_a_failed_page_and_raises_on_a_refused_key(flow: Flow, mock: respx.MockRouter) -> None:
    not_found = {"error": {"type": "not_found", "message": "No such event.", "hint": "h", "doc_url": "d"}}
    refused = {"error": {"type": "authentication", "message": "Key revoked.", "hint": "h", "doc_url": "d"}}
    mock.get(url("/v0/events")).mock(
        side_effect=[
            httpx.Response(404, json=not_found),
            httpx.Response(200, json=page([event_received(evt(2))])),
            httpx.Response(401, json=refused),
        ]
    )
    statuses: list[tuple[str, str | None]] = []
    stream = flow.events.stream(
        transport="poll", after=evt(1), poll_interval=3, on_status=lambda s, d: statuses.append((s, d))
    )
    slept: list[float] = []
    flow._http._sleep = slept.append
    got: list[str] = []
    with pytest.raises(AuthenticationError, match="Key revoked"):
        for e in stream:
            got.append(e.id)
    assert got == [evt(2)]
    assert slept == [3, 3]
    assert statuses[0] == ("polling", None)
    assert statuses[1][0] == "reconnecting" and "No such event" in (statuses[1][1] or "")


async def test_poll_without_a_key_raises_async(mock: respx.MockRouter) -> None:
    aflow = AsyncFlow(base_url="https://api.test")
    route = mock.get(url("/v0/events"))
    with pytest.raises(AuthenticationError):
        async for _ in aflow.events.stream(transport="poll"):
            pass
    assert not route.called
    await aflow.aclose()
