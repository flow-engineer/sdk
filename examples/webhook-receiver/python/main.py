"""A Flow Messaging webhook receiver (FastAPI).

It verifies Flow-Signature on the raw body, dedupes on event.id, answers within
10 seconds, and replies to each message in the webhook answer: {"reply": ...}.
Run: FLOW_MESSAGING_WEBHOOK_SECRET=whsec_... python main.py   (Python 3.10+)
"""

import hashlib
import hmac
import json
import os
import sys
import time

import uvicorn
from fastapi import FastAPI, Request, Response

SECRET = os.environ.get("FLOW_MESSAGING_WEBHOOK_SECRET")
PORT = int(os.environ.get("PORT", "3000"))
if not SECRET:
    sys.exit("Set FLOW_MESSAGING_WEBHOOK_SECRET to the whsec_... secret from POST /v1/webhook_endpoints.")


def verify(header: str | None, raw_body: bytes, secret: str, tolerance: int = 300) -> bool:
    """Flow-Signature: t=<unix seconds>,v1=<hex>[,v1=<hex>].

    Each v1 is the hex HMAC-SHA256, keyed with the whole secret (whsec_ included),
    of "t." + t + "." + the raw body. Two v1 values appear while a secret rotation
    overlaps: any one may match.
    """
    t, signatures = "", []
    for part in (header or "").split(","):
        k, _, v = part.strip().partition("=")
        if k == "t":
            t = v
        elif k == "v1":
            signatures.append(v)
    if not (t.isascii() and t.isdigit()) or abs(time.time() - int(t)) > tolerance:
        return False
    want = hmac.new(secret.encode(), b"t." + t.encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(want.encode(), s.encode()) for s in signatures)


app = FastAPI()
seen: set[str] = set()  # event IDs already handled (use your database in production)


@app.post("/flow/webhook")
async def flow_webhook(request: Request):
    raw = await request.body()  # the raw bytes: verify before parsing
    if not verify(request.headers.get("Flow-Signature"), raw, SECRET):
        print("rejected: bad Flow-Signature", flush=True)
        return Response(status_code=400)
    event = json.loads(raw)
    if event["id"] in seen:
        print(f"duplicate {event['id']}: skipped", flush=True)  # delivery is at least once
        return {}
    seen.add(event["id"])

    if event["type"] == "message.received":
        content = event["data"]["message"]["content"]
        said = content["text"] if content["type"] == "text" else f"a {content['type']}"
        print(f"{event['id']} [{event['conversation']['id']}] {said}", flush=True)
        # The reply goes into this conversation through the send gate, with the event ID as
        # its idempotency key. Keep it fast: slow agents answer {} and send through the API.
        return {"reply": {"type": "text", "text": f"You said: {said}"}}
    if event["type"] == "message.failed":
        e = event["data"]["message"]["error"]
        print(f"{event['id']} send failed: {e['type']}: {e['message']} ({e.get('hint', '')})", flush=True)
    return {}  # 2xx with no reply: delivered, nothing sent


if __name__ == "__main__":
    # Prints "Uvicorn running on http://0.0.0.0:3000" once it accepts requests.
    uvicorn.run(app, host="0.0.0.0", port=PORT)
