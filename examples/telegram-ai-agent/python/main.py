"""An LLM support agent on Telegram.

It keeps each conversation's history, answers with Claude (any LLM works: replace
think()), and offers a "Talk to a human" button that hands the conversation to
your team. Events come from the WebSocket stream, so no public URL is needed;
replies go out with POST /v1/conversations/{id}/messages and an Idempotency-Key.

Run: python main.py             (FLOW_MESSAGING_KEY and ANTHROPIC_API_KEY set)
     python main.py --fake-llm  (no Anthropic key: a canned answer, for testing)
"""

import asyncio
import json
import os
import sys
import urllib.parse

import anthropic
import httpx
import websockets

KEY = os.environ.get("FLOW_MESSAGING_KEY")
BASE = os.environ.get("FLOW_MESSAGING_BASE_URL", "https://api.flow.engineer").rstrip("/")
FAKE_LLM = "--fake-llm" in sys.argv
if not KEY:
    sys.exit("Set FLOW_MESSAGING_KEY. No key yet? curl -X POST https://api.flow.engineer/v1/sandbox/keys")

MODEL = "claude-sonnet-5-5"
SYSTEM = """You are the support agent of Acme, chatting with a customer on Telegram.
Answer in at most three short sentences of plain text (no markdown).
If you cannot help, tell them to tap "Talk to a human"."""
HUMAN = "talk_to_human"  # the button's id; a tap comes back as button_reply with this id

llm = None if FAKE_LLM else anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY
http = httpx.AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
history: dict[str, list[dict]] = {}  # conversation id -> turns (use a database in production)
with_human: set[str] = set()  # conversations handed to a person: the agent stays quiet


class FlowError(Exception):
    def __init__(self, error: dict):
        super().__init__(f"{error['type']}: {error['message']} ({error.get('hint', '')})")
        self.error = error


async def flow(path: str, body: dict, idempotency_key: str) -> dict:
    """Calls the Flow API. Retries 429 and 5xx with the same Idempotency-Key, so a retry never sends twice."""
    for attempt in range(1, 6):
        res = await http.post(path, json=body, headers={"Idempotency-Key": idempotency_key})
        try:
            data = res.json()
        except ValueError:
            data = {"error": {"type": "api_error", "message": res.reason_phrase, "hint": "Retry later."}}
        if res.is_success:
            return data
        if (res.status_code != 429 and res.status_code < 500) or attempt == 5:
            raise FlowError(data["error"])
        await asyncio.sleep(float(res.headers.get("Retry-After", 2**attempt)))
    raise AssertionError("unreachable")


async def think(conversation_id: str, text: str) -> str:
    """Asks the LLM for the next answer in a conversation and records both turns."""
    messages = history.get(conversation_id, []) + [{"role": "user", "content": text}]
    if llm:
        res = await llm.messages.create(model=MODEL, max_tokens=1024, system=SYSTEM, messages=messages)
        if res.stop_reason == "refusal":
            answer = 'Sorry, I can\'t help with that here. Tap "Talk to a human".'
        else:
            answer = "".join(b.text for b in res.content if b.type == "text").strip()
    else:
        answer = f'(fake LLM) Answer {(len(messages) + 1) // 2}: you said "{text}"'
    # Keep an even number of turns, so the history starts with a user turn.
    history[conversation_id] = (messages + [{"role": "assistant", "content": answer}])[-20:]
    return answer


async def handle(event: dict) -> None:
    conv = event["conversation"]["id"]
    if event["type"] == "message.failed":
        e = event["data"]["message"]["error"]
        print(f"[{conv}] send failed: {e['type']}: {e['message']} ({e.get('hint', '')})", flush=True)
        return
    message = event["data"]["message"]
    content = message["content"]
    send_path = f"/v1/conversations/{conv}/messages"

    if content["type"] == "button_reply" and content["button_id"] == HUMAN:
        with_human.add(conv)
        print(f"[{conv}] handed to a human", flush=True)  # notify your team here
        await flow(send_path, {"content": {"type": "text", "text": "Thanks. A person from our team will answer here soon."}},
                   f"reply-{message['id']}")
        return
    text = content.get("text") if content["type"] == "text" else content.get("label") if content["type"] == "button_reply" else None
    if conv in with_human:
        print(f"[{conv}] (with a human) {text or content['type']}", flush=True)
        return
    print(f"[{conv}] customer: {text or content['type']}", flush=True)
    if text is None:
        await flow(send_path, {"content": {"type": "text", "text": "I can read text messages only."}}, f"reply-{message['id']}")
        return

    # Optional: show "typing..." while the LLM thinks. It can fail; never let that stop the reply.
    try:
        await flow(f"/v1/conversations/{conv}/typing", {"state": "on"}, f"typing-{message['id']}")
    except (FlowError, httpx.HTTPError):
        pass
    answer = await think(conv, text)
    print(f"[{conv}] agent: {answer}", flush=True)
    try:
        # The key comes from the inbound message: one reply per message, however often this runs.
        await flow(send_path, {
            "content": {"type": "buttons", "text": answer[:1024], "buttons": [{"id": HUMAN, "label": "Talk to a human"}]},
            "fallback": "auto",  # channels without buttons get numbered text instead
        }, f"reply-{message['id']}")
    except FlowError as e:
        # An LLM answers differently each time: if this message was already answered (a
        # replayed event after a crash), the same key with a new body is refused. Keep the first.
        if e.error["type"] != "idempotency_conflict":
            raise
        print(f"[{conv}] already answered {message['id']}", flush=True)


locks: dict[str, asyncio.Lock] = {}  # one per conversation: in order within it, parallel across them
tasks: set[asyncio.Task] = set()


async def run(event: dict) -> None:
    conv = event["conversation"]["id"]
    async with locks.setdefault(conv, asyncio.Lock()):
        try:
            await handle(event)
        except Exception as e:  # keep serving the other conversations
            print(f"[{conv}] {e}", flush=True)


async def main() -> None:
    seen: set[str] = set()  # delivery is at least once: dedupe on event.id
    last_event_id = None
    while True:
        query = [("type", "message.received"), ("type", "message.failed")]
        if last_event_id:
            query.append(("after", last_event_id))
        url = BASE.replace("http", "ws", 1) + "/v1/stream?" + urllib.parse.urlencode(query)
        try:
            async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {KEY}"}) as ws:
                print(f"Support agent ready{' (fake LLM)' if FAKE_LLM else ''}. Write to your sandbox bot.", flush=True)
                async for raw in ws:
                    frame = json.loads(raw)
                    if frame["type"] == "reconnect":
                        last_event_id = frame.get("after") or last_event_id
                        break
                    if frame["type"] != "event":
                        continue
                    event = frame["event"]
                    last_event_id = event["id"]
                    if event["id"] in seen:
                        continue
                    seen.add(event["id"])
                    task = asyncio.create_task(run(event))
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)
        except websockets.InvalidStatus as e:
            if 400 <= e.response.status_code < 500:  # a bad or expired key: retrying will not help
                sys.exit(f"Stream refused: {e.response.body.decode(errors='replace')}")
            print(f"Stream refused ({e}); reconnecting.", flush=True)
        except (OSError, websockets.WebSocketException) as e:
            print(f"Stream closed ({e}); reconnecting.", flush=True)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
