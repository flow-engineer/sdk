"""Telegram echo agent: answers every message with what it said.

It reads events from the WebSocket stream (GET /v1/stream), so no public URL is
needed, and replies with `send` frames on the same socket.
Run: FLOW_MESSAGING_KEY=fk_test_... python main.py   (Python 3.10+, pip install -r requirements.txt)
"""

import asyncio
import json
import os
import sys
import urllib.parse
import urllib.request

import websockets

KEY = os.environ.get("FLOW_MESSAGING_KEY")
BASE = os.environ.get("FLOW_MESSAGING_BASE_URL", "https://api.flow.engineer").rstrip("/")
if not KEY:
    sys.exit("Set FLOW_MESSAGING_KEY. No key yet? curl -X POST https://api.flow.engineer/v1/sandbox/keys")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def show_senders() -> None:
    """Prints where to write: the sandbox bot's link (it joins your app when tapped)."""
    req = urllib.request.Request(f"{BASE}/v1/senders?channel=telegram", headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as res:
            senders = json.load(res)["data"]
    except urllib.error.HTTPError as e:
        err = json.load(e)["error"]
        sys.exit(f"{err['type']}: {err['message']} ({err['hint']})")
    for s in senders:
        where = s["address"].get("link") or "@" + s["address"].get("username", "")
        join = f' (or send "{s["join_code"]}")' if s.get("join_code") else ""
        print(f"Write to {where}{join}", flush=True)


async def main() -> None:
    show_senders()
    last_event_id = None  # resume point after a reconnect
    seen = set()  # delivery is at least once: dedupe on event.id
    while True:
        query = [("type", "message.received")] + ([("after", last_event_id)] if last_event_id else [])
        url = BASE.replace("http", "ws", 1) + "/v1/stream?" + urllib.parse.urlencode(query)
        try:
            async with websockets.connect(url, additional_headers=HEADERS) as ws:
                print("Echo agent ready.", flush=True)
                async for raw in ws:
                    frame = json.loads(raw)
                    if frame["type"] == "event":
                        event = frame["event"]
                        last_event_id = event["id"]
                        if event["id"] in seen:
                            continue
                        seen.add(event["id"])
                        message = event["data"]["message"]
                        content = message["content"]
                        said = content["text"] if content["type"] == "text" else f"a {content['type']}"
                        print(f"[{event['conversation']['id']}] {said}", flush=True)
                        # `ref` is the idempotency key: derived from the inbound message,
                        # so a replay never sends twice.
                        await ws.send(json.dumps({
                            "type": "send",
                            "ref": f"echo-{message['id']}",
                            "conversation": event["conversation"]["id"],
                            "message": {"content": {"type": "text", "text": f"You said: {said}"}},
                        }))
                    elif frame["type"] == "ack":
                        print(f"  -> sent {frame['message']['id']}", flush=True)
                    elif frame["type"] == "error":
                        err = frame["error"]
                        print(f"  -> {err['type']}: {err['message']} ({err['hint']})", flush=True)
                    elif frame["type"] == "reconnect":
                        last_event_id = frame.get("after") or last_event_id
                        break
        except websockets.ConnectionClosed as e:
            # A refused stream (bad, revoked or expired key; a bad request) sends an
            # error frame, then closes with 4401, 4403 or 4400: reconnecting will not help.
            if e.rcvd is not None and e.rcvd.code in (4400, 4401, 4403):
                sys.exit(f"Stream refused ({e.rcvd.code}): {e.rcvd.reason}")
            print(f"Stream closed ({e}); reconnecting.", flush=True)
        except websockets.InvalidStatus as e:
            if 400 <= e.response.status_code < 500:  # a bad or expired key: retrying will not help
                sys.exit(f"Stream refused: {e.response.body.decode(errors='replace')}")
            print(f"Stream refused ({e}); reconnecting.", flush=True)
        except (OSError, websockets.WebSocketException) as e:
            print(f"Stream closed ({e}); reconnecting.", flush=True)
        await asyncio.sleep(1)  # then resume from last_event_id


if __name__ == "__main__":
    asyncio.run(main())
