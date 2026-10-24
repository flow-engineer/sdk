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
with flow.events.stream(types=["message.received"]) as events:
    print(f"On your phone, open {bot.address.link} and tap Start (or send: {bot.join_code})")
    greeted = False
    for event in events:
        if not greeted:  # the join itself arrives as your first message ("/start")
            flow.messages.send(event.conversation.id, "Hi! Write me something.")
            greeted = True
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

Each kind of message has its own endpoint and its own method, and what you send is what
the contact gets: Flow never converts a message into another kind.

```python
from flow_messaging import content

flow.messages.basic("conv_...", text="Your order shipped.")
flow.messages.basic("conv_...", text="Yes, that one.", reply_to="msg_...")  # an inline reply
flow.messages.buttons("conv_...", content.buttons("Which size?", ["S", "M", "L"]))
flow.messages.list("conv_...", content.list_message("Which size?", "Sizes", [{"id": "s", "title": "Small"}]))
file = flow.files.upload("photo.jpg")
flow.messages.basic("conv_...", content.image(file.id, "Your order"))
flow.messages.reaction("conv_...", message_id="msg_...", emoji="👍")
```

| Method | Endpoint (`POST /v0/conversations/{conversation_id}/...`) | Builder |
| --- | --- | --- |
| `messages.basic` | `basic`: text and/or one file, every channel | `basic`, `media`, `image`, `video`, `audio`, `document` |
| `messages.voice` | `voice`: a voice note | `voice` |
| `messages.buttons` | `buttons`: reply buttons, or one URL button | `buttons` |
| `messages.list` | `list`: a WhatsApp list | `list_message` |
| `messages.carousel` | `carousel`: WhatsApp cards | `carousel` |
| `messages.template` | `template`: an approved WhatsApp template | `template` |
| `messages.contact_card` | `contact-card` | `contact_card` |
| `messages.location` | `location` | `location` |
| `messages.effect` | `effect`: iMessage screen and bubble effects | `effect` |
| `messages.reaction` | `reaction`: one emoji, or `emoji=None` to remove yours | `reaction` |
| `conversations.typing` | `typing`: shows the indicator | |
| `conversations.read` | `read`: a read receipt | |

Each method takes the message as a dict, a model from `flow_messaging.types` or a
builder from `flow_messaging.content`, with keyword fields laid over it; the builders
return plain dicts with `kind` set. Text is sent exactly as written: no markdown is
rendered or stripped (style it with the channel's own `telegram` or `imessage` block).

`messages.send` takes any kind object and sends it to its kind's endpoint, so code that
gets messages from elsewhere (an LLM's tool call, a queue) needs no switch. A string is
short for `{"kind": "basic", "text": ...}`. `typing` and `read` answer a
`ConversationAction`, and `edit` and `unsend` go to `PATCH` and `DELETE
/v0/messages/{message_id}`. An object without a `kind` that can be sent raises
`ValueError` before any request.

```python
flow.messages.send("conv_...", "Your order shipped.")
flow.messages.send("conv_...", content.buttons("Which size?", ["S", "M", "L"]))
flow.messages.send("conv_...", {"kind": "location", "lat": 52.52, "lng": 13.405, "name": "Our shop"})
```

Starting a conversation takes a `basic` or a `template` message (the only kind WhatsApp
delivers outside its 24-hour window), sent as one flat body with the sender and the
recipient:

```python
flow.messages.start(sender="snd_...", to="ct_...", message="Your table is ready.")
flow.messages.start(sender="snd_...", to="+15555550100", message=content.template("tpl_...", "en"))
```

Changing and acting:

```python
flow.messages.edit("msg_...", "Fixed typo")       # Telegram; iMessage within 15 minutes
flow.messages.unsend("msg_...")                   # Telegram within 48 hours, iMessage within 2 minutes
flow.conversations.typing("conv_...")             # clears itself; there is no "off"
flow.conversations.typing("conv_...", imessage={"duration_seconds": 10})
flow.conversations.read("conv_...")               # WhatsApp: up_to="msg_..." marks up to that message
```

A handle bundles the calls for one conversation: `flow.conversation(event)` gives
`.send(message)`, `.typing()`, `.read()`, `.react(message_id, "👍")` and `.messages()`.
`content_text()` gives the text a person would read in any message's content.

### When a channel cannot take a message

A kind or a field the conversation's channel does not take is refused with `422
unsupported_content`, raised as `UnsupportedContentError`: `param` names what was
refused (`kind`, a field, a channel block) and `hint` says what to send instead. Send
the replacement yourself. The `422` is kept under its `Idempotency-Key` like any answer,
so the replacement needs a new key: the refused one's plus what it is.

```python
from flow_messaging import UnsupportedContentError

try:
    flow.messages.carousel(conv_id, cards_message, idempotency_key=f"{event.id}:card")
except UnsupportedContentError as e:
    print(e.param, e.hint)
    flow.messages.basic(conv_id, text=summary, idempotency_key=f"{event.id}:card:basic")
```

## Events

```python
for event in flow.events.stream(types=["message.received"]):
    print(event.conversation.id, content_text(event.data.message.content))
```

The stream is a WebSocket (`GET /v0/stream`) that reconnects by itself and resumes with
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

`webhook_reply` builds the answer that replies at once: a kind object, a string (basic
text), or a list of up to 11 of them, sent in order exactly as given
(`webhook_reply(["Here is the menu:", content.image(url)])`); `None` sends nothing now.
A piece without a `kind` that can be sent, or more than 11 pieces, raises `ValueError`
in your handler. A piece the channel refuses is reported as `message.failed`.

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
flow.test.inbound(conv.id, {"kind": "button_reply", "message_id": "msg_...", "button_id": "s"})  # a tap
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
