---
name: flow-messaging-migrate
description: Use when a project's Flow Messaging code still uses the old /v1 shape and must move to Messaging V0 (/v0, one endpoint per message kind). Signs of old code - POST /v1/conversations/{id}/messages, a "content" object with "type" (text, media, buttons, carousel, ...), "fallback" (auto or a content object), "channel_options", "delivered_as", format markdown, GET /v1/capabilities, typing with "state" on/off, "shown" in test transcripts, any https://api.flow.engineer/v1/ URL, or @flow-engineer/messaging before 0.4.0 / flow-messaging before 0.2.0. Covers plain HTTP, the TypeScript and Python SDKs, webhooks, the stream, the test API and Flow Framework users.
---

# Move to Flow Messaging V0 (one endpoint per message kind)

Flow Messaging's API is now **V0**, at `/v0`. Two things changed:

1. **Every route moves from `/v1/...` to `/v0/...`**: sends, starts, typing, read, edit,
   unsend, and also senders, contacts, files, templates, webhook endpoints, events, the
   stream, the test API, sandbox keys and the device sign-in. `/v1` is kept for the
   stable 1.0 release. The `Flow-Version` date stays `2026-11-01`.
2. **One endpoint per message kind, exact or 422.** `POST /v1/conversations/{id}/messages`
   with `content`/`fallback`/`channel_options` is gone. Each kind has its own endpoint
   (`POST /v0/conversations/{id}/basic`, `/buttons`, `/list`, ...) whose body is the kind
   object itself. Flow never converts anything any more: no `fallback`, no
   `delivered_as`, no markdown rendering, no numbered-button text, no capabilities call.
   What the channel does not take answers `422 unsupported_content`, and nothing is sent.
   Your code now chooses, per channel, what to send instead.

Webhooks, the stream and `Message.content` use the same kind objects: `{"kind": "basic",
"text": "Hi"}` replaces `{"type": "text", "text": "Hi"}`.

## Which path are you on?

- **Flow Framework (`@flow-engineer/flow`) only:** upgrade the framework to the release
  whose CHANGELOG says it moves to Flow Messaging V0, and run your tests. Your agent code
  does not change: the framework picks the substitute per channel (a carousel on Telegram,
  buttons on iMessage, markdown into each channel's style). If the project also calls
  Flow Messaging directly (HTTP or the SDKs) beside the framework, move those calls with
  the rest of this skill.
- **TypeScript SDK:** upgrade to `@flow-engineer/messaging@0.4.3` and follow "SDK names" and the
  per-channel rules below.
- **Python SDK:** upgrade to `flow-messaging>=0.2.0` and do the same.
- **Plain HTTP (any language):** follow every section below.

Do the whole move in one change: old and new shapes are not mixed on one route, and an
app on V0 gets its webhook events in the new shape.

## 1. Find the old code

Search the project (code, tests, fixtures, prompts, docs) for each of these and fix every hit:

| Search for | What it was |
|---|---|
| `/v1/` | every Flow Messaging URL (change all of them to `/v0/`) |
| `/messages` after a conversation id, with POST | the old send (the GET that lists a conversation's messages stays, at `/v0/conversations/{id}/messages`) |
| `"content"` / `content:` holding `type` | the old content union, in sends, starts, edits, webhook replies, stream frames and test inbound turns |
| `fallback` | old fallbacks (not `Sender.imessage.fallback`, the SMS/RCS fallback flag, which is unchanged) |
| `channel_options` | the old escape hatch |
| `delivered_as`, `.shown` | what Flow converted; gone |
| `format: "markdown"`, `"format": "markdown"`, `markdown(` | markdown rendering by Flow; gone |
| `capabilities` | `GET /v1/capabilities`, `flow.capabilities.retrieve`; gone |
| `state: "on"`, `"off"`, `typing("on")`, `typing("off")` | typing with a state |
| `markRead`, `mark_read` | renamed `read` in the SDKs |
| `.type ===`, `["type"] ==`, `case "text"`, `case "media"` on message content | inbound parsing |
| `subject` | the old cross-channel subject line |

## 2. What maps to what

Endpoints are `POST /v0/conversations/{conversation_id}/<kind>`; the body is the kind's
fields (a `kind` key is optional there and must match). Fields that only one channel
has sit in a block named after it (`telegram`, `imessage`); a block for another channel,
or a field the channel does not take, answers `422`; an unknown field `400`.

| Old `content.type` | New endpoint and body | Channels |
|---|---|---|
| `text` `{text}` | `/basic` `{text}` | all |
| `text` with `format: "markdown"` | `/basic` with the text in the channel's own terms (see 4) | all |
| `text` with `subject` | iMessage: `/basic` `{text, imessage: {subject}}`; elsewhere write the line into `text` yourself (Telegram `<b>Subject</b>\n...` with `telegram: {parse_mode: "HTML"}`, WhatsApp `*Subject*\n...`, SMS a plain first line) | |
| `media` `{kind, url or file_id, caption, filename}` | `/basic` `{media: {type, url or file_id, filename}, text: caption}` (`media.kind` is now `media.type`; the caption is `text`). `filename` only on a `document` (on Telegram only with `file_id`: Telegram names a document sent by `url` itself). WhatsApp shows no caption on audio: send the audio, then the text as its own `basic` | all; SMS only images, audio, video, from numbers with MMS |
| `voice` | `/voice` `{url or file_id}` | Telegram, WhatsApp, iMessage |
| `buttons` (1 to 3 on WhatsApp, up to 10 on Telegram) | `/buttons` `{text, buttons, header}` | Telegram, WhatsApp |
| `buttons` with more than 3 reply buttons on WhatsApp (Flow used to send a list) | `/list` `{text, button: "<menu label>", sections: [{rows: [{id, title, description}]}]}` (at most 10 rows) | WhatsApp |
| `carousel` | `/carousel` `{text, cards}` | WhatsApp |
| `template` | `/template` `{template_id, language, params, reply_to}` | WhatsApp |
| `location` | `/location` `{lat, lng, name, address}` (Telegram: `name` and `address` together, or neither) | Telegram, WhatsApp |
| `contact_card` | `/contact-card` `{name, phones, emails}` (Telegram needs a phone, and puts every phone and email on a card of at most 2048 bytes) | Telegram, WhatsApp |
| `effect` | `/effect` `{text, effect}` | iMessage |
| `reaction` | `/reaction` `{message_id, emoji}` (`null` removes) | Telegram (its emoji list only), WhatsApp, iMessage (not groups) |
| `typing` `{state: "on"}` | `POST /v0/conversations/{id}/typing` with `{}` or no body | Telegram, WhatsApp, iMessage (not groups) |
| `typing` `{state: "off"}` | delete the call: no channel clears typing on request; it clears when your next message goes | |
| `read` `{up_to}` | `POST /v0/conversations/{id}/read` `{up_to}` (WhatsApp), `{}` (iMessage: whole conversation, `up_to` is refused) | WhatsApp, iMessage (not groups) |
| `edit` / `PATCH /v1/messages/{id}` `{content: {type: "text", text}}` | `PATCH /v0/messages/{id}` `{text}` (plus `telegram: {parse_mode}` or `imessage: {styles}`) | Telegram, iMessage |
| `unsend` / `DELETE /v1/messages/{id}` | `DELETE /v0/messages/{id}` | Telegram, iMessage |

Fields that used to sit beside `content`:

| Old field | New place |
|---|---|
| `reply_to` (top level) | inside the kind: `basic`, `voice`, `buttons`, `list`, `contact_card`, `location`, `effect`, `template`. `carousel` takes none: send it without it. SMS refuses it: leave it out there. |
| `metadata` (top level) | inside the kind (every message kind but `reaction`, `typing`, `read` and edits) |
| `link_preview` (default `true`) | `basic.link_preview`; leave it out for the channel's default (previews on). Send only `false` when you want plain links: `true` on SMS, or with `media` on any channel, answers `422`. |
| `fallback` | gone: choose the substitute yourself (section 3) |
| `delivered_as` | gone: what you send is what the contact gets |

Old `channel_options` keys:

| Channel | Old key | New place |
|---|---|---|
| Telegram | `parse_mode` | `telegram.parse_mode` (`HTML` or `MarkdownV2`) on `basic`, `buttons` and edits |
| Telegram | `disable_notification`, `protect_content` | `telegram.*` on `basic` and `buttons` |
| Telegram | `show_caption_above_media`, `has_spoiler` | `telegram.*` on `basic` with `media` |
| Telegram | `is_big` | `telegram.is_big` on `/reaction` |
| Telegram | `link_preview_options`, `disable_web_page_preview` | `link_preview` (`false` to turn previews off) |
| Telegram | `entities`, `caption_entities` | gone: style with `telegram.parse_mode` instead |
| Telegram | `allow_paid_broadcast`, `message_effect_id`, `supports_streaming`, `duration`, `width`, `height`, `performer`, `horizontal_accuracy`, `foursquare_id`, `foursquare_type`, `google_place_id`, `google_place_type`, `vcard` | gone: remove them |
| iMessage | `subject` | `imessage.subject` on `/basic` |
| iMessage | `effect` | the `/effect` endpoint |
| iMessage | `preview` | `link_preview` |
| iMessage | `reply_to_id` | `reply_to` |
| iMessage | `typing` (seconds, on typing) | `imessage.duration_seconds` on `/typing` (1 to 60) |
| iMessage | `contact_file` | gone |
| WhatsApp | `preview_url` | `link_preview` |

Starts (`POST /v0/messages`) are flat: where to send it plus a `basic` or `template`
kind object, with `kind` required:

```json
// before: POST /v1/messages
{"sender": "snd_...", "to": {"phone": "+15555550123"}, "content": {"type": "text", "text": "Your table is ready."}, "fallback": "auto"}
// after: POST /v0/messages
{"sender": "snd_...", "to": {"phone": "+15555550123"}, "kind": "basic", "text": "Your table is ready."}
```

Only `basic` and `template` start a conversation (any other kind answers `422`, `param`
`kind`); send other kinds into it after. `consent` goes only on SMS starts (elsewhere `422`,
`param` `consent`).

## 3. Replace each fallback with explicit per-channel sends

Decide before you send, from the conversation's channel: `event.conversation.channel`
(and `event.conversation.type`, `direct` or `group`) on every event, or
`GET /v0/conversations/{id}`. There is no capabilities call; the facts it held are on each
endpoint's page (its table of channels opens the page). On SMS, whether a number has MMS
is `Sender.sms.mms` (`GET /v0/senders/{sender_id}`). WhatsApp's window is
`conversation.window_open_until`.

| You meant to send | Telegram | WhatsApp | iMessage | SMS |
|---|---|---|---|---|
| carousel | `basic` with the text, then one `buttons` per card: `{header: card.header, text: card.text, buttons: card.buttons}` (a card without text needs one, such as its title) | `carousel` | `basic` with the text, then one `basic` per card: `{media: {type: card.header.type, url}, text: <card text and its choices>}` | as iMessage, from a number with MMS; else text only |
| buttons | `buttons` (up to 10) | `buttons` (1 to 3), a `list` for 4 to 10 reply choices, `buttons` with exactly one URL button for a link | `basic` whose text lists the choices ("Reply 1, 2 or 3"); match the answer yourself (below) | as iMessage |
| buttons with a media header | `buttons` with `header` (text at most 1024) | `buttons` with `header` (not with a list) | `basic` with the `media` and the numbered choices as its text | as iMessage (no documents) |
| list | `buttons` with one reply button per row | `list` | numbered `basic` | numbered `basic` |
| template | `basic` | `template` (the only kind outside the 24-hour window) | `basic` | `basic` |
| location | `location` | `location` | `basic` with a maps link (`https://maps.google.com/?q=<lat>,<lng>`) and the name and address | as iMessage |
| contact card | `contact_card` (with a phone) | `contact_card` | `basic` with the name, numbers and emails | as iMessage |
| effect | `basic` | `basic` | `effect` | `basic` |
| voice note | `voice` | `voice` | `voice` | `basic` with `media: {type: "audio", ...}` (MMS) |
| reaction | `reaction` with one of Telegram's reaction emoji (listed on `/reaction`), else skip it | `reaction` | `reaction`; skip it in groups | skip it (or a `basic` if it carries meaning) |
| typing | `typing` | `typing` | `typing`; skip it in groups | skip it |
| read receipt | skip it | `read` | `read` without `up_to`; skip it in groups | skip it |
| edit / unsend | `PATCH` / `DELETE` | a new `basic` with the correction | `PATCH` / `DELETE` (time limits; not for a message whose `network` is `sms` or `rcs`) | a new `basic` with the correction |
| markdown text | see section 4 | | | |

**Numbered choices are now your code's job.** Flow used to turn buttons into numbered text
on iMessage and SMS and match the contact's "2" back to a `button_reply`. Now the contact's
answer arrives as a plain `basic` message: keep the choices you listed for that conversation
and match the reply's `text` yourself (by number, or by a label only one choice has), then
handle it as you handle a `button_reply`.

**Order and keys.** Sends to one conversation go out in the order Flow accepted them, one at
a time, across every endpoint, webhook replies and the stream, so send the pieces one after
the other (await each). Give every call its own `Idempotency-Key`, derived from what you are
answering, such as `evt_123:text`, `evt_123:card:1`, `evt_123:card:2`. A retry with the same key
never sends twice.

**Substitute sends after a 422.** A `422` answer is kept under its key like any other answer,
so repeating the refused key returns the same `422`. The message you send instead is a new
request with a **new key: the refused key plus what it is**, such as `evt_123:card:2:basic`
after `evt_123:card:2` came back `422`. On the stream, `ref` is the key: give the substitute
frame a new `ref` the same way.

## 4. Markdown and styles

`text` is now sent exactly as written on every channel: `**bold**` shows with its stars.
Pick one per channel:

- **Simplest:** tell your model to answer in plain text (no markdown) and send it as written.
- **WhatsApp:** its app reads its own marks: turn `**x**` into `*x*`, `*x*` and `_x_` into
  `_x_`, `~~x~~` into `~x~`.
- **Telegram:** turn markdown into Telegram HTML and send `telegram: {parse_mode: "HTML"}`.
  Escape `&`, `<` and `>` in the text first; then `**x**` → `<b>x</b>`, `*x*` or `_x_` →
  `<i>x</i>`, `~~x~~` → `<s>x</s>`, `` `x` `` → `<code>x</code>`, `[t](https://u)` → `<a href="https://u">t</a>`.
  Text Telegram cannot parse fails as `message.failed` (`channel_error`). Telegram's length
  limits (4096, a caption 1024) count the text after its tags are parsed, so the HTML may be longer.
- **iMessage:** remove the marks and send their places as `imessage.styles`
  (`[{start, length, style}]`, counted in UTF-16 code units, which is how JavaScript string
  indexes count; in Python `len(s.encode("utf-16-le")) // 2`). Styles: `bold`, `italic`,
  `underline`, `strikethrough`, `big`, `small`, and the animations `shake`, `nod`,
  `explode`, `ripple`, `bloom`, `jitter` (Flow's old `<u>`, `<big>`, `<shake>`, ... tags).
- **SMS:** remove the marks.

```ts
// iMessage: **bold** and *italic* into styles (a sketch; extend for other marks).
function imessageStyles(md: string) {
  const styles: { start: number; length: number; style: "bold" | "italic" }[] = [];
  let text = "";
  const re = /\*\*(.+?)\*\*|\*(.+?)\*/g;
  let at = 0;
  for (const m of md.matchAll(re)) {
    text += md.slice(at, m.index);
    const inner = m[1] ?? m[2]!;
    styles.push({ start: text.length, length: inner.length, style: m[1] ? "bold" : "italic" });
    text += inner;
    at = m.index! + m[0].length;
  }
  text += md.slice(at);
  return { text, imessage: styles.length ? { styles } : undefined };
}
```

The same goes for edits: `PATCH /v0/messages/{id}` sends `text` as written, styled with
`telegram.parse_mode` or `imessage.styles`.

## 5. Handle the new 422s

`422 unsupported_content` means the conversation's channel does not take that kind, field,
block or value, and nothing was sent. Do not retry the same request. The error carries:

- `param`: what was refused: `kind` (the endpoint), a field or block (`reply_to`,
  `link_preview`, `text`, `telegram`, `telegram.is_big`, `consent`, `up_to`), or a value's field
  (`emoji`, `buttons`, `phones`, `name`, `address`, `media`, `media.type`, `media.filename`);
- `channel`: the conversation's channel;
- `channel_code` for cases that depend on the conversation or message: `group_unsupported`
  (reaction, typing or read in an iMessage group: leave it out), `not_on_sms` (edit or
  unsend of an iMessage message that went by SMS or RCS: send a correction), `no_mms`
  (media to an SMS number without MMS: send text), `edit_window_closed`,
  `unsend_window_closed`, `first_message_not_editable`;
- `hint`: what to send instead over plain HTTP, written for developers and coding agents
  (do not parse it).

Choosing per channel up front (section 3) avoids most of them. Where a 422 still comes back,
send the substitute with a new key (section 3) or skip a courtesy (typing, read, reactions).
Typing and read receipts on a channel without them now answer `422` instead of a skipped `2xx`.

## 6. Read inbound messages and events by `kind`

`event.data.message.content` (and `Message.content` everywhere, message lists and test
transcripts included) is a kind object with `kind`:

| Old | New |
|---|---|
| `{type: "text", text}` | `{kind: "basic", text}` |
| `{type: "media", kind: "image", url, file_id, caption, mime_type, size_bytes}` | `{kind: "basic", media: {type: "image", url, file_id, mime_type, size_bytes}, text}` (the caption is `text`) |
| `{type: "voice", url, file_id, transcript, duration_seconds}` | `{kind: "voice", ...}` (same fields) |
| `{type: "button_reply", button_id, label, message_id}` | `{kind: "button_reply", ...}`; a tap on a WhatsApp list row arrives the same way, with the row's `id` and title |
| `{type: "location" / "contact_card" / "reaction", ...}` | `{kind: ..., ...}` (same fields) |
| `{type: "file_blocked", kind: "document", reason, ...}` | `{kind: "file_blocked", media_type: "document", reason, ...}` |

`metadata` is kept once, at the message's own `metadata`, and is not repeated inside
`content`. To send a received piece on (a photo, a voice note), copy only what a send takes
(`media.type` with its `file_id` or `url`, `text`): fields Flow fills on received messages,
such as `media.mime_type`, `media.size_bytes` or a voice note's `transcript`, answer
`400 invalid_request` on a send.

Other changes: `delivered_as` is gone from messages and from typing/read answers
(`ConversationAction` keeps `conversation` and `action`); iMessage messages and their events
carry `network` (`imessage`, `sms` or `rcs`); test transcripts have no `shown` (read `content`,
which is what the contact saw). Webhook signatures, event types and the event envelope are
unchanged. Deliveries are at least once: keep deduplicating on `event.id`.

## 7. Webhook replies, the stream and the test API

- **Webhook answers:** `{"reply": ...}` takes one kind object, a string (short for
  `{"kind": "basic", "text": ...}`), or a list of 1 to 11 of those. `fallback` is gone. A piece
  the channel refuses is reported as a `message.failed` event, so pick the pieces per channel
  (`event.conversation.channel`) before you answer: a carousel to Telegram becomes a basic
  piece plus one buttons piece per card, which fits in the 11.

  ```json
  {"reply": [{"kind": "basic", "text": "Three picks for you"},
             {"kind": "buttons", "header": {"type": "image", "url": "https://example.com/a.jpg"}, "text": "Linen shirt", "buttons": [{"id": "buy_a", "label": "Buy"}]}]}
  ```
- **Stream** (`/v0/stream`): a `send` frame is `{"type": "send", "ref": "...", "conversation":
  "conv_...", "message": <kind object with kind>}`; a `start` frame's `message` is the flat
  start body. The frame's own `type` (`send`, `start`) is unchanged; `ref` is the
  idempotency key.
- **Test API:** `POST /v0/test/conversations/{id}/inbound` takes `{"content": {"kind":
  "basic", "text": "..."}}` (media: `{"kind": "basic", "media": {"type": "image", "file_id":
  "file_..."}}`; a tap: `{"kind": "button_reply", "message_id": "msg_...", "button_id":
  "..."}`, also for a list row). A simulated contact on iMessage or SMS answers numbered
  choices as text.

## 8. SDK names

TypeScript, `@flow-engineer/messaging` 0.3 → 0.4.0:

| Before | After |
|---|---|
| `flow.messages.send(conv, { content, fallback, channel_options })` | `flow.messages.send(conv, kindObject)` (routes by `kind`), or the kind's own method: `flow.messages.basic(conv, { text })`, `.voice`, `.buttons`, `.list`, `.carousel`, `.template`, `.contactCard`, `.location`, `.effect`, `.reaction` |
| `text("Hi")`, `markdown("**Hi**")` | `basic("Hi")` (or the string itself); markdown: section 4 |
| `image(src, { caption })` and other media builders | `image(src, caption)`, `video`, `audio`, `document`, `media(type, src, { caption, filename })`, all `basic` kind objects |
| `buttons(...)`, `voice`, `location`, `contactCard`, `effect`, `reaction`, `template` | same names, now returning kind objects; new `list(text, button, rows)` and `carousel(text, cards)` |
| `flow.messages.start({ sender, to, content })` | `flow.messages.start({ sender, to, kind: "basic", text })` |
| `flow.messages.edit(id, "text" or TextContent)` | `flow.messages.edit(id, "text" or { text, telegram, imessage })` |
| `flow.conversations.typing(conv, "on")`, `conversation.typing("on")` | `flow.conversations.typing(conv)`, `conversation.typing()`; `"off"` calls: delete them |
| `flow.conversations.markRead(conv, upTo)`, `conversation.markRead(upTo)` | `flow.conversations.read(conv, { up_to })`, `conversation.read({ up_to })` |
| `flow.capabilities.retrieve(conv)` | gone: use `event.conversation.channel` and section 3 |
| `conversation.reply(x, { format, fallback, channel_options })` | `conversation.reply(x)`: a string, a kind object, a list, or an LLM stream; the text bubbles go as written (section 4) |
| `webhookReply(x)`, handler return values | the same, with kind objects (at most 11 pieces) |
| `flow.test.inbound(conv, { type: "text", text })` | `flow.test.inbound(conv, { kind: "basic", text })` or a string |
| `m.shown ?? m.content` in transcripts | `m.content` |
| types `Content`, `TextContent`, `SendMessageRequest`, `Fallback`, `ChannelOptions`, `DeliveredAs`, `Capabilities` | `OutboundKind`, `MessageContent`, `BasicMessage`, `ButtonsMessage`, ... (`BasicKind`, `ButtonsKind`, ... with `kind` required) |

`UnsupportedContentError` carries `param`, `channel`, `channelCode` and `hint`. Pass your own
key per call with `{ idempotencyKey }`:

```ts
import { FlowMessaging, UnsupportedContentError } from "@flow-engineer/messaging";
const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY

const key = `${event.id}:sizes`;
try {
  await flow.messages.buttons(event.conversation.id, { text: "Which size?", buttons: [{ id: "s", label: "Small" }, { id: "m", label: "Medium" }] }, { idempotencyKey: key });
} catch (e) {
  if (!(e instanceof UnsupportedContentError) || e.param !== "kind") throw e;
  await flow.messages.basic(event.conversation.id, { text: "Which size? Reply 1 for Small or 2 for Medium." }, { idempotencyKey: `${key}:basic` });
}
```

Python, `flow-messaging` 0.1 → 0.2.0 (the same names on `Flow` and `AsyncFlow`):

| Before | After |
|---|---|
| `flow.messages.send(conv, content, reply_to=..., fallback=..., channel_options=...)` | `flow.messages.send(conv, {"kind": "basic", "text": "Hi", "reply_to": "msg_..."})`, or the kind's method with keyword fields: `flow.messages.basic(conv, text="Hi")`, `.voice`, `.buttons`, `.list`, `.carousel`, `.template`, `.contact_card`, `.location`, `.effect`, `.reaction` |
| `content.text("Hi")`, `content.markdown("**Hi**")` | `content.basic("Hi")` (or the string itself); markdown: section 4 |
| `content.image(src, caption=...)` and the other media builders | the same names (`image`, `video`, `audio`, `document`, `media`), now `basic` kind dicts; `caption` may also go second |
| `content.buttons`, `voice`, `location`, `contact_card`, `effect`, `reaction`, `template` | same names, now returning kind dicts; new `content.list_message(text, button, rows)` and `content.carousel(text, cards)` |
| `flow.messages.start(sender=..., to=..., content=...)` | `flow.messages.start(sender=..., to=..., message={"kind": "basic", "text": "Hi"})` (`consent=` on SMS) |
| `flow.messages.edit(id, content)` | `flow.messages.edit(id, text="New")` (with `telegram=` or `imessage=` blocks) |
| `flow.conversations.typing(conv, "on")`, `flow.conversation(conv).typing("on")` | `flow.conversations.typing(conv)`, `flow.conversation(conv).typing()` (`imessage={"duration_seconds": 10}` on iMessage); `"off"` calls: delete them |
| `flow.conversations.mark_read(conv, up_to)`, `flow.conversation(conv).mark_read(up_to)` | `flow.conversations.read(conv, up_to="msg_...")`, `flow.conversation(conv).read(...)` (`up_to` on WhatsApp only) |
| `flow.test.inbound(conv, "Hi")` with old content dicts | `flow.test.inbound(conv, {"kind": "basic", "text": "Hi"})` or a string |
| `flow.capabilities.retrieve(conv)` | gone |
| `webhook_reply(reply, fallback=...)` | `webhook_reply(reply)` with kind dicts |

Plain dicts with `kind` work with every method. Every send takes `idempotency_key=`.
`UnsupportedContentError` carries `param`, `channel_code` and `hint`.

## 9. Plain HTTP

```bash
# before
curl https://api.flow.engineer/v1/conversations/$CONV/messages \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -d '{"content": {"type": "buttons", "text": "Which size?", "buttons": [{"id": "s", "label": "Small"}]}, "fallback": "auto"}'

# after: the kind's endpoint, its fields as the body, a key per call
curl https://api.flow.engineer/v0/conversations/$CONV/buttons \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: evt_123:sizes" \
  -d '{"text": "Which size?", "buttons": [{"id": "s", "label": "Small"}]}'

# typing: no state
curl -X POST https://api.flow.engineer/v0/conversations/$CONV/typing \
  -H "Authorization: Bearer $FLOW_MESSAGING_KEY"
```

Typing takes `Idempotency-Key` like every `POST`: a repeat with the same key within 24 hours
does not show the indicator again, so a loop that keeps typing on sends a new key (or none)
each time. Typing and read receipts are a courtesy: ignore their `409 outside_window`,
`422` and `502` and never hold a reply back for them.

## 10. Check the move

1. No `/v1/` Flow Messaging URL, `content.type`, `fallback`, `channel_options`,
   `delivered_as`, `capabilities`, `format: "markdown"` or typing `state` is left (section 1).
2. With a test key (`fk_test_...`), make a simulated conversation per channel the project
   uses (`POST /v0/test/conversations` with `channel` `telegram`, `whatsapp`, `imessage`,
   `sms`), write a turn as the contact, and read `GET /v0/test/conversations/{id}/transcript`:
   every piece arrived, in order, as the contact should see it, and no send answered `422`.
3. Webhook handlers and stream readers parse `kind`, and webhook answers hold only kind
   objects or strings (an invalid answer sends nothing and is recorded on the delivery as
   an `invalid_request` error).
4. Tests and fixtures that hold old payloads are updated to the kind shape.

## MCP

MCP is not a runtime dependency: the app you build talks to Flow through the REST API (or the TypeScript or Python SDK, which wrap it) for everything it does at runtime. Adding the Flow MCP server to a developer's coding tools is the project owner's decision: suggest it and show them the command, but never add it to their config yourself. The MCP server's `capabilities` tool is gone, and its
send tools (`send_message`, `reply`, `send_test_message`) take a `message` that is a kind
object, as in a webhook reply.

More: the API reference and every endpoint's channel table are in the spec,
https://github.com/flow-engineer/sdk/blob/main/openapi/openapi.yaml, and the error page is
https://api.flow.engineer/docs/errors/unsupported_content.
