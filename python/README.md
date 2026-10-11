# flow-messaging

Let an AI agent talk with people on **WhatsApp, Telegram and iMessage** (and US SMS,
in pilot) through one API. The Python SDK for Flow Messaging (`api.flow.engineer`):
typed sync and async clients, the live event stream, and webhook verification.

```sh
pip install flow-messaging
```

## Quickstart

No key, no account and no public URL needed. Run this, then open the link it prints on
your phone:

```python
from flow_messaging import Flow, content_text

sandbox = Flow().sandbox.create_key()  # a test key, no account; save sandbox.key as FLOW_MESSAGING_KEY
flow = Flow(sandbox.key)
bot = next(s for s in flow.senders.list(channel="telegram") if s.kind == "shared")
with flow.events.stream(types=["conversation.started", "message.received"]) as events:
    print(f"On your phone, open {bot.address.link} and tap Start (or send: {bot.join_code})")
    for event in events:
        if event.type == "conversation.started":  # you joined the sandbox
            flow.messages.send(event.conversation.id, "Hi! Write me something.")
        else:
            print("They said:", content_text(event.data.message.content))
            break
```

Next time, reuse the key: `Flow()` reads `FLOW_MESSAGING_KEY`. Check for a key before
minting a new one.

## The client

```python
from flow_messaging import Flow, AsyncFlow

flow = Flow()                         # FLOW_MESSAGING_KEY, FLOW_MESSAGING_BASE_URL
flow = Flow("fk_test_...", timeout=30, max_retries=2)

async with AsyncFlow() as aflow:      # the same API, with await
    me = await aflow.app.retrieve()
```

- `api_key`: defaults to `FLOW_MESSAGING_KEY`. Without one, only the keyless calls work
  (`sandbox.create_key`, the device sign-in); everything else raises
  `AuthenticationError` before sending.
- `base_url`: defaults to `FLOW_MESSAGING_BASE_URL`, else `https://api.flow.engineer`.
- `flow_version`: the `Flow-Version` sent with every request. The default is the API
  version this SDK was generated from (`flow_messaging.API_VERSION`), so answers always
  match its models.
- Every POST carries an `Idempotency-Key` (generated, or yours with
  `idempotency_key=`), reused across retries. Connection errors, timeouts, `429
  rate_limited` and 5xx answers are retried (`max_retries`, default 2), waiting for
  `retry_after` when the API gives one.
- `flow.with_options(timeout=..., max_retries=...)` returns a copy that shares the
  connection pool.

## Sending

```python
from flow_messaging.content import buttons, image, markdown

flow.messages.send("conv_...", "Your order shipped.")
flow.messages.send("conv_...", buttons("Size?", ["S", "M", "L"]), fallback="auto")
flow.messages.send("conv_...", markdown("**Done.**"), reply_to="msg_...")
file = flow.files.upload("photo.jpg")
flow.messages.send("conv_...", image(file.id, caption="Your order"))

flow.messages.start(sender="snd_...", to="ct_...", content="Your table is ready.")
flow.messages.edit("msg_...", "Fixed typo")      # Telegram
flow.messages.unsend("msg_...")                  # Telegram, within 48 hours
flow.conversations.typing("conv_...", "on")
flow.conversations.mark_read("conv_...")
```

Content is a string (text), a dict in the API's shape, a model from
`flow_messaging.types`, or a builder from `flow_messaging.content`. `content_text()`
gives the text a person would read in any piece of content. A handle bundles the calls
for one conversation: `flow.conversation(event).send("Hi")`, `.typing()`,
`.mark_read()`, `.react(message_id, "👍")`.

## Events

```python
for event in flow.events.stream(types=["message.received"]):
    print(event.conversation.id, content_text(event.data.message.content))
```

The stream is a WebSocket (`GET /v1/stream`) that reconnects by itself and resumes with
`after`, so no event is lost and none is handed out twice. `stream.last_event_id` is the
last event you got: pass it as `after=` to resume across restarts. Use it as a context
manager (`with flow.events.stream(...) as events:`) to connect before you say you are
ready. A refused key ends it with `AuthenticationError` or `PermissionDeniedError`
instead of reconnecting forever. `transport="poll"` reads the event log instead, for
networks that block WebSockets.

The log itself: `flow.events.list(after="evt_...", type=[...])` (oldest first) and
`flow.events.retrieve("evt_...")`. Events are Pydantic models, a discriminated union on
`type` (`flow_messaging.types.Event`): check `event.type` or
`isinstance(event, MessageReceivedEvent)`.

## Webhooks

```python
from flow_messaging import WebhookSignatureError, construct_event, webhook_reply

@app.post("/flow")                       # FastAPI; Flask and Django work the same way
async def flow_webhook(request: Request):
    raw = await request.body()           # the raw body, before parsing
    try:
        event = construct_event(raw, request.headers.get("Flow-Signature"), secret)
    except WebhookSignatureError:
        return Response(status_code=400)
    if event.type == "message.received":
        return webhook_reply("Got it!")  # replies at once from the answer
    return {}
```

`secret` defaults to `FLOW_MESSAGING_WEBHOOK_SECRET`; pass a list of secrets while
rotating. `verify_signature` checks without parsing, and `sign_payload` builds a header
for your own tests.

## Errors

Every API error raises a subclass of `FlowError` chosen by the error's `type`, with
`message`, `hint` (what to change), `doc_url`, `request_id` (quote it when asking for
help), `param`, `retry_after` and `code` (the channel's or Flow's code).

```python
from flow_messaging import OutsideWindowError, PermissionDeniedError
from flow_messaging.content import template

try:
    flow.messages.send(conv_id, "Are you still there?")
except OutsideWindowError:
    flow.messages.send(conv_id, template("tpl_...", "en"))
except PermissionDeniedError as e:
    if e.code == "sandbox_allowance_used":
        ...  # sign in to lift the sandbox allowance
```

## Lists

Every `list` method pages with a cursor. The page has `data` and `has_more`; iterating
it walks every item across pages.

```python
page = flow.conversations.list(limit=20)
for conversation in flow.conversations.list(channel="telegram"):
    ...
async for conversation in aflow.conversations.list():   # async
    ...
```

## Testing with simulated contacts

Test keys can play the end user, with no phone and no real channel. Each turn reaches
your agent as a real `message.received`; your replies pass the real send gate.

```python
conv = flow.test.create_conversation("telegram")
flow.test.inbound(conv.id, "Do you deliver on Sundays?")
for entry in flow.test.transcript(conv.id):
    print(entry.direction, content_text(entry.content))
```

## Signing in from an agent

A sandbox key expires after 7 days. A person keeps the app by signing in with a Flow account (flow.engineer):

```python
token = flow.device.sign_in(
    lambda a: print(f"Open {a.verification_uri_complete} and check the code {a.user_code}"),
    claim_token=os.environ.get("FLOW_CLAIM_TOKEN"),
)
# save token.key as FLOW_MESSAGING_KEY
```

## Compared with the TypeScript SDK

The same API surface, in Python's idioms. Not here yet: splitting replies into chat
bubbles from an LLM stream (`reply`), the CLI and the MCP bridge. Use the REST API
through this SDK for everything your app does at runtime.

## Development

The models in `src/flow_messaging/_models.py` are generated from
`../openapi/openapi.yaml`, and the sync client in `src/flow_messaging/_sync/` from the
async one in `src/flow_messaging/_async/`; never edit either by hand. From `python/`:

```sh
uv venv .venv && uv pip install --python .venv/bin/python -e . --group dev
.venv/bin/python scripts/generate.py      # after a spec change or an edit in _async/
../scripts/check-python.sh                # generated code, ruff, mypy, unit tests, build
```
