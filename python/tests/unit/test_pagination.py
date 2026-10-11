"""Cursor pagination (sync): the first page eagerly, then ``after`` = the last ID,
keeping the other filters; and query encoding."""

from __future__ import annotations

import httpx
import respx
from conftest import CONV, conversation, event_received, evt, message, page, ulid, url

from flow_messaging import Flow, Page, Pager
from flow_messaging._base import encode_query
from flow_messaging.types import Conversation, MessageReceivedEvent

C = [ulid("conv", n) for n in range(1, 6)]


def paged(route: respx.Route, pages: dict[str | None, tuple[list[str], bool]]) -> None:
    """Answers by the request's ``after``: {after: (ids, has_more)}."""

    def answer(request: httpx.Request) -> httpx.Response:
        ids, more = pages[request.url.params.get("after")]
        return httpx.Response(200, json=page([conversation(i) for i in ids], more))

    route.side_effect = answer


def test_list_fetches_first_page_eagerly(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/conversations"))
    paged(route, {None: ([C[0], C[1]], True)})
    p = flow.conversations.list(limit=2)
    assert route.call_count == 1
    assert isinstance(p, Pager) and isinstance(p, Page)
    assert [c.id for c in p.data] == [C[0], C[1]]
    assert all(isinstance(c, Conversation) for c in p.data)
    assert p.has_more is True
    assert "2 items" in repr(p)


def test_iterating_walks_every_page_with_after_and_filters(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/conversations"))
    paged(route, {None: ([C[0], C[1]], True), C[1]: ([C[2], C[3]], True), C[3]: ([C[4]], False)})
    ids = [c.id for c in flow.conversations.list(channel="telegram", sender="snd_x", limit=2, before="conv_z")]
    assert ids == C
    assert route.call_count == 3
    params = [c.request.url.params for c in route.calls]
    assert [p.get("after") for p in params] == [None, C[1], C[3]]
    for p in params:
        assert p["channel"] == "telegram"
        assert p["sender"] == "snd_x"
        assert p["limit"] == "2"
        assert p["before"] == "conv_z"
        assert "contact" not in p


def test_list_starts_after_the_given_cursor(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/conversations"))
    paged(route, {C[0]: ([C[1], C[2]], True), C[2]: ([C[3]], False)})
    assert [c.id for c in flow.conversations.list(after=C[0])] == [C[1], C[2], C[3]]
    assert [c.request.url.params["after"] for c in route.calls] == [C[0], C[2]]


def test_next_page_and_iter_pages(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/conversations"))
    paged(route, {None: ([C[0]], True), C[0]: ([C[1]], False)})
    first = flow.conversations.list()
    second = first.next_page()
    assert second is not None
    assert [c.id for c in second.data] == [C[1]]
    assert second.has_more is False
    assert second.next_page() is None
    assert route.call_count == 2
    assert [len(p.data) for p in first.iter_pages()] == [1, 1]


def test_next_page_none_when_empty_even_if_has_more(flow: Flow, mock: respx.MockRouter) -> None:
    mock.get(url("/v1/conversations")).respond(json=page([], True))
    p = flow.conversations.list()
    assert p.next_page() is None
    assert list(p) == []


def test_to_list_with_limit_stops_fetching(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/conversations"))
    paged(route, {None: ([C[0], C[1]], True), C[1]: ([C[2], C[3]], True), C[3]: ([C[4]], False)})
    assert [c.id for c in flow.conversations.list().to_list(3)] == C[:3]
    assert route.call_count == 2
    route.reset()
    assert [c.id for c in flow.conversations.list().to_list()] == C
    assert route.call_count == 3


def test_events_list_repeats_type_values(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/events")).respond(json=page([event_received(evt(1))]))
    p = flow.events.list(type=["message.received", "message.failed"], conversation=CONV)
    assert isinstance(p.data[0], MessageReceivedEvent)
    q = route.calls.last.request.url.params
    assert q.get_list("type") == ["message.received", "message.failed"]
    assert q["conversation"] == CONV
    assert "limit" not in q and "after" not in q


def test_events_list_single_type(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/events")).respond(json=page([]))
    flow.events.list(type="message.received")
    assert route.calls.last.request.url.params.get_list("type") == ["message.received"]


def test_conversation_messages_pages(flow: Flow, mock: respx.MockRouter) -> None:
    m1, m2 = ulid("msg", 1), ulid("msg", 2)
    route = mock.get(url(f"/v1/conversations/{CONV}/messages"))
    route.side_effect = [
        httpx.Response(200, json=page([message(m1)], True)),
        httpx.Response(200, json=page([message(m2)], False)),
    ]
    assert [m.id for m in flow.conversations.messages(CONV, limit=1)] == [m1, m2]
    assert route.calls[1].request.url.params["after"] == m1
    assert route.calls[1].request.url.params["limit"] == "1"


def test_encode_query() -> None:
    assert encode_query({"a": None, "b": True, "c": False, "d": ["x", "y"], "e": 3, "f": ("p",)}) == [
        ("b", "true"),
        ("c", "false"),
        ("d", "x"),
        ("d", "y"),
        ("e", "3"),
        ("f", "p"),
    ]
    assert encode_query(None) == []


def test_boolean_query_lower_case(flow: Flow, mock: respx.MockRouter) -> None:
    route = mock.get(url("/v1/app")).respond(json={})
    flow._http.request("GET", "/v1/app", query={"flag": True, "off": False, "gone": None})
    assert str(route.calls.last.request.url).endswith("/v1/app?flag=true&off=false")
