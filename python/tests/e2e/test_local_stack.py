"""End to end against a local Flow Messaging service (the service checkout's
scripts/local-stack.sh), with simulated conversations: no phone, no real channel.

Skipped unless FLOW_BASE_URL points at a running stack (the variables its env file
exports). scripts/check-python.sh --e2e starts one and runs these:

    eval "$(<service>/scripts/local-stack.sh --background)"
    .venv/bin/pytest tests/e2e
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pytest

from flow_messaging import (
    AsyncFlow,
    AuthenticationError,
    Flow,
    NotFoundError,
    NotImplementedYetError,
    UnsupportedContentError,
    construct_event,
    content_text,
)
from flow_messaging.types import (
    ConversationStartedEvent,
    Event,
    MessageReceivedEvent,
    MessageSentEvent,
)

BASE_URL = os.environ.get("FLOW_BASE_URL", "")
WAIT = 20.0  # seconds any one expectation may take


def _stack_up() -> bool:
    if not BASE_URL:
        return False
    try:
        return httpx.get(BASE_URL + "/readyz", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _stack_up(), reason="no local Flow Messaging stack (set FLOW_BASE_URL)")


@pytest.fixture
def flow() -> Iterator[Flow]:
    """A client for a new sandbox app, minted without a key."""
    with Flow(base_url=BASE_URL) as anon:
        key = anon.sandbox.create_key(name="python e2e").key
    with Flow(key, base_url=BASE_URL) as client:
        yield client


class Collector:
    """Reads a sync event stream on a thread; the test waits on its queue."""

    def __init__(self, flow: Flow, **params: Any) -> None:
        self.events: queue.Queue[Event | BaseException] = queue.Queue()
        self.opened = threading.Event()
        self.stream = flow.events.stream(on_status=self._status, **params)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        assert self.opened.wait(WAIT), "the stream did not open"

    def _status(self, status: str, detail: str | None) -> None:
        if status == "open":
            self.opened.set()

    def _run(self) -> None:
        try:
            for event in self.stream:
                self.events.put(event)
        except BaseException as e:  # handed to the test
            self.events.put(e)
            self.opened.set()

    def next(self, kind: type[Any]) -> Any:
        while True:
            item = self.events.get(timeout=WAIT)
            if isinstance(item, BaseException):
                raise item
            if isinstance(item, kind):
                return item

    def close(self) -> None:
        self.stream.close()
        self.thread.join(WAIT)


def test_sandbox_key_and_senders() -> None:
    with Flow(base_url=BASE_URL) as anon:
        sandbox = anon.sandbox.create_key(name="python e2e")
    assert sandbox.key.startswith("fk_test_")
    assert sandbox.claim_token
    flow = Flow(sandbox.key, base_url=BASE_URL)
    ctx = flow.app.retrieve()
    assert ctx.app.id == sandbox.app.id and ctx.livemode is False
    telegram = [s for s in flow.senders.list(channel="telegram") if s.kind == "shared"]
    assert telegram, "no shared Telegram sandbox sender"
    assert telegram[0].join_code == f"Hi {ctx.app.name} (ref {ctx.app.sandbox_join_code})"
    assert telegram[0].address.link


def test_simulated_conversation_round_trip(flow: Flow) -> None:
    events = Collector(flow, types=["message.received", "message.sent", "conversation.started"])
    try:
        conv = flow.test.create_conversation("telegram", name="Asha")
        assert conv.simulated is True
        flow.test.inbound(conv.id, "Do you deliver on Sundays?")

        started = events.next(ConversationStartedEvent)
        assert started.conversation is not None and started.conversation.id == conv.id
        received = events.next(MessageReceivedEvent)
        assert content_text(received.data.message.content) == "Do you deliver on Sundays?"

        handle = flow.conversation(received)
        assert handle.id == conv.id and handle.channel == "telegram"
        handle.typing()
        # Telegram takes no read receipts: exact or 422, nothing sent.
        with pytest.raises(UnsupportedContentError) as refused:
            handle.read()
        assert refused.value.param == "kind" and refused.value.hint
        reply = handle.send(f"You said: {content_text(received.data.message.content)}")
        sent = events.next(MessageSentEvent)
        assert sent.data.message.id == reply.id
    finally:
        events.close()

    transcript = flow.test.transcript(conv.id).to_list()
    assert [(e.direction, content_text(e.content)) for e in transcript] == [
        ("in", "Do you deliver on Sundays?"),
        ("out", "You said: Do you deliver on Sundays?"),
    ]
    assert transcript[1].status == "sent"

    # Telegram can edit and unsend.
    edited = flow.messages.edit(reply.id, "Yes, we do.")
    assert content_text(edited.content) == "Yes, we do."
    assert flow.messages.unsend(reply.id).id == reply.id

    # The log, read by page: oldest first, one per page.
    log = flow.events.list(conversation=conv.id, limit=1)
    assert len(log.data) == 1 and log.has_more
    every = log.to_list()
    assert len(every) >= 3
    assert flow.events.retrieve(every[0].id).id == every[0].id


def test_async_stream_and_reply(flow: Flow) -> None:
    key = flow.api_key

    async def run() -> None:
        async with AsyncFlow(key, base_url=BASE_URL) as aflow:
            opened = asyncio.Event()
            stream = aflow.events.stream(
                types=["message.received"], on_status=lambda s, _d: opened.set() if s == "open" else None
            )
            received: asyncio.Queue[MessageReceivedEvent] = asyncio.Queue()

            async def read() -> None:
                async for event in stream:
                    assert isinstance(event, MessageReceivedEvent)
                    await received.put(event)

            reader = asyncio.create_task(read())
            await asyncio.wait_for(opened.wait(), WAIT)
            conv = await aflow.test.create_conversation("telegram")
            await aflow.test.inbound(conv.id, "hello async")
            event = await asyncio.wait_for(received.get(), WAIT)
            msg = await aflow.conversation(event).send("hi from AsyncFlow")
            assert msg.status in ("queued", "sent")
            await stream.aclose()
            await asyncio.wait_for(reader, WAIT)
            page = await aflow.conversations.list(limit=10)
            assert conv.id in [c.id for c in page.data]

    asyncio.run(run())


def test_stream_resumes_after(flow: Flow) -> None:
    conv = flow.test.create_conversation("telegram")
    flow.test.inbound(conv.id, "one")
    first = Collector(flow, types=["message.received"], after=None)
    try:
        flow.test.inbound(conv.id, "two")
        two = first.next(MessageReceivedEvent)
        assert content_text(two.data.message.content) == "two"
    finally:
        first.close()
    flow.test.inbound(conv.id, "three")
    # Resuming after "two" replays "three" (sent while no stream was open).
    again = Collector(flow, types=["message.received"], after=two.id)
    try:
        three = again.next(MessageReceivedEvent)
        assert content_text(three.data.message.content) == "three"
    finally:
        again.close()


def test_files_upload_and_download(flow: Flow) -> None:
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    file = flow.files.upload(png, filename="dot.png", channel="telegram")
    assert file.id.startswith("file_") and file.mime_type == "image/png"
    assert flow.files.download(file.id) == png
    assert flow.files.download(file.url) == png
    conv = flow.test.create_conversation("telegram")
    flow.test.inbound(conv.id, {"kind": "basic", "text": "a dot", "media": {"type": "image", "file_id": file.id}})


def test_contacts_and_delete(flow: Flow) -> None:
    conv = flow.test.create_conversation("telegram", name="Ravi")
    flow.test.inbound(conv.id, "hi")
    contact = flow.contacts.retrieve(conv.contact)
    assert contact.simulated is True
    assert conv.contact in [c.id for c in flow.contacts.list(channel="telegram")]
    flow.contacts.delete(conv.contact)
    flow.contacts.delete(conv.contact)  # safe to retry
    with pytest.raises(NotFoundError):
        flow.conversations.retrieve(conv.id)


class _Receiver(BaseHTTPRequestHandler):
    deliveries: queue.Queue[tuple[bytes, str | None]] = queue.Queue()

    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        type(self).deliveries.put((raw, self.headers.get("Flow-Signature")))
        body = json.dumps({"reply": "Answered from the webhook"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


def test_webhook_endpoint_signature_and_reply(flow: Flow) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Receiver)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/flow"
        endpoint = flow.webhook_endpoints.create(url=url, events=["message.received"], description="e2e")
        assert endpoint.secret and endpoint.secret.startswith("whsec_")
        assert endpoint.id in [e.id for e in flow.webhook_endpoints.list()]

        conv = flow.test.create_conversation("telegram")
        flow.test.inbound(conv.id, "ping")
        raw, signature = _Receiver.deliveries.get(timeout=WAIT)
        event = construct_event(raw, signature, endpoint.secret)
        assert isinstance(event, MessageReceivedEvent)
        assert content_text(event.data.message.content) == "ping"
        assert not flow.webhooks.verify(raw, signature, "whsec_wrong")

        updated = flow.webhook_endpoints.update(endpoint.id, enabled=False)
        assert updated.enabled is False
        rotated = flow.webhook_endpoints.rotate_secret(endpoint.id, overlap_seconds=0)
        assert rotated.secret and rotated.secret != endpoint.secret
        assert flow.webhook_endpoints.delete(endpoint.id).deleted is True
    finally:
        server.shutdown()


def test_typed_errors() -> None:
    with pytest.raises(AuthenticationError) as info:
        Flow("fk_test_not_a_key", base_url=BASE_URL).app.retrieve()
    err = info.value
    assert err.status == 401 and err.hint and err.request_id
    assert err.doc_url and err.doc_url.endswith("/errors/authentication")


def test_device_sign_in_starts(flow: Flow) -> None:
    try:
        auth = flow.device.authorize(client_name="python e2e")
    except NotImplementedYetError as e:  # a stack without any sign-in configured
        pytest.skip(f"sign-in is not configured on this stack: {e.message}")
    assert auth.user_code and auth.verification_uri_complete
    assert flow.device.poll(auth.device_code).status == "pending"


SIM = os.environ.get("TELEGRAMSIM_URL", "")


def _sim_headers() -> dict[str, str]:
    with open(os.environ["TELEGRAMSIM_ADMIN_TOKEN_FILE"]) as f:
        return {"Authorization": "Bearer " + f.read().strip()}


def _readme_quickstart() -> str:
    readme = Path(__file__).resolve().parents[2] / "README.md"
    text = readme.read_text()
    start = text.index("## Quickstart")
    block = text.index("```python\n", start) + len("```python\n")
    return text[block : text.index("```", block)]


@pytest.mark.skipif(not SIM, reason="no Telegram simulator (set TELEGRAMSIM_URL)")
def test_readme_quickstart() -> None:
    """Runs the README's quickstart as written, playing the person on Telegram."""
    with open(os.environ["TELEGRAMSIM_SANDBOX_TOKEN_FILE"]) as f:
        bot_token = f.read().strip()
    user = 7700 + os.getpid() % 1000
    sim = httpx.Client(base_url=SIM, headers=_sim_headers(), timeout=WAIT + 10)

    def say(text: str, n: int) -> None:
        update = {
            "update_id": 0,
            "message": {
                "message_id": n,
                "from": {"id": user, "is_bot": False, "first_name": "Asha"},
                "chat": {"id": user, "type": "private"},
                "date": int(time.time()),
                "text": text,
            },
        }
        res = sim.post("/_sim/deliver", json={"token": bot_token, "update": update})
        assert res.status_code == 200 and res.json().get("status") == 200, res.text

    def latest() -> int:
        return max((c["seq"] for c in sim.get("/_sim/calls").json()["calls"]), default=0)

    import flow_messaging

    package_root = str(Path(flow_messaging.__file__).resolve().parents[1])
    env = {**os.environ, "FLOW_MESSAGING_BASE_URL": BASE_URL, "PYTHONUNBUFFERED": "1", "PYTHONPATH": package_root}
    env.pop("FLOW_MESSAGING_KEY", None)
    proc = subprocess.Popen(
        [sys.executable, "-c", _readme_quickstart()],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline()
        m = re.search(r"open https://t\.me/\w+\?start=([\w-]+) and tap Start \(or send: Hi .+ \(ref ([\w-]+)\)\)", line)
        assert m, f"unexpected output: {line!r}"
        after = latest()
        say(f"/start {m.group(1)}", 1)  # the person taps the link
        # The script answers the join with its greeting.
        texts: list[str] = []
        deadline = time.monotonic() + WAIT
        while "Hi! Write me something." not in texts and time.monotonic() < deadline:
            q = {
                "token": bot_token,
                "method": "sendMessage",
                "chat_id": user,
                "after": after,
                "min": 1,
                "wait_ms": int(WAIT * 1000),
            }
            calls = sim.get("/_sim/calls", params=q).json()["calls"]
            texts += [c["params"]["text"] for c in calls]
            after = max((c["seq"] for c in calls), default=after)
        assert "Hi! Write me something." in texts, texts
        say("hello from the README", 2)
        out, _ = proc.communicate(timeout=WAIT)
        assert "They said: hello from the README" in out, out
        assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
