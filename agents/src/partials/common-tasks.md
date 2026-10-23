### Many Telegram bots (one per customer, brand or language)

- A person creates each bot in Telegram's @BotFather (`/newbot`, a name, a username ending in `bot`); an agent cannot. Ask them: "Create the bot in @BotFather and put its token in `.env` (or your secret store) as `TELEGRAM_BOT_TOKEN_<NAME>`; don't paste it here." Never ask for the token in chat.
- With a live key, `POST /v1/senders {"channel":"telegram","telegram_bot_token":"..."}` once per bot (`Idempotency-Key` per bot). One bot is one sender; connecting it again updates that sender; connecting it to another of your apps moves it there. There is no limit on bots per app.
- Send from a bot with `"sender": "snd_..."` on `POST /v1/messages`; replies go into the conversation and leave from its bot. Every event names its `conversation.sender`, so route by sender.

### Serverless (Vercel, Workers, Lambda): webhooks only

- Register `https://<your-app>/api/flow` once with `POST /v1/webhook_endpoints` and store the `whsec_...` secret as `{{env.webhook_secret}}`. Verify `Flow-Signature` on the raw body (in TypeScript `flow.webhooks.handler(...)` does it), dedupe on `event.id`, answer within {{webhook_timeout_seconds}} seconds.
- Fast answer: return `{"reply": ...}` in the webhook answer. Slow agent: answer `200 {}` at once, then reply with `POST /v1/conversations/{conversation_id}/messages` (on Vercel inside `waitUntil`). Keep conversation state in your database, keyed by `conversation.id`.
- Missed deliveries are retried for 3 days; to catch up, read `GET /v1/events?after=evt_...` from a cron job.
- Previews and local runs: Flow calls only public HTTPS URLs. Locally, no tunnel needed: `npx {{package}} listen --forward-to http://localhost:3000/api/flow` reads the stream and `POST`s each event to your handler, signed like a real delivery with `{{env.webhook_secret}}`.

### Add Flow to the IDE (MCP)

The hosted MCP server is an optional development tool. Adding it is the project owner's decision: show them the command (section 12 of the quickstart, or `docs/mcp`), never add it yourself. The app itself always uses the REST API.

### Send a PDF, receive a voice note

- Uploads (`POST /v1/files`, multipart, up to 100 MB) take images, audio, video, plain text and documents (PDF, Office files, zip and other archives). Documents are malware-scanned before Flow stores them: one that fails answers `422 file_blocked` and is not stored; if the scan cannot run just then, the upload answers a retryable `500 api_error` with `Retry-After` (retry with the same `Idempotency-Key`). Then send `{"type":"media","kind":"document","file_id":"file_...","filename":"receipt.pdf"}` (Telegram takes documents up to 50 MB; SMS takes none). A PDF you already host can go by `url` instead of `file_id`; the channel fetches it (Telegram: PDF and ZIP, up to 20 MB).
- A voice note arrives as `message.received` with `{"type":"voice","file_id":"file_...","url":"...","duration_seconds":4}`. Download it with `GET /v1/files/{file_id}` (your API key; it answers `302` to a short-lived signed URL, so follow redirects). Send one with `{"type":"voice","file_id":"file_..."}` (OGG/Opus on Telegram).

### WhatsApp: a reminder the next day

Flow has no scheduled sends: schedule in your own app (cron, queue) and send then. Next day is usually outside WhatsApp's 24-hour window, so only an approved `template` goes (`POST /v1/templates` on your WhatsApp sender with a live key; else `409 outside_window`). Test it now on a simulated WhatsApp conversation: templates on the simulated sender are approved at once. Connect your own WhatsApp number with `POST /v1/senders` (quickstart section 11).

### Move a live polling bot to Flow

Connect its token with a live key (`POST /v1/senders`). Flow sets the bot's webhook, which ends `getUpdates` polling: stop the old poller first (Telegram answers its next `getUpdates` with `409 Conflict`). Updates Telegram still holds are delivered to Flow, not dropped. Conversations start fresh in Flow (it has no history from before); people do not need to press Start again. To go back, `DELETE /v1/senders/{sender_id}` removes the webhook.

### Broadcast to many people

- There is no bulk endpoint: one `POST /v1/messages` per person, each with its own `Idempotency-Key` (for example `campaign-7-ct_...`), from a queue of your own.
- Telegram: a bot can message only people who started it, so a broadcast goes to people who wrote to your bot. Each bot sends about {{sending.messages_per_second}} messages a second (burst {{sending.burst}}); faster answers `429 rate_limited` with `Retry-After`. The per-key request limit is 600 a minute on the free plan (`RateLimit-*` headers), so 5,000 messages take about 9 minutes.
- New conversations per sender are budgeted: the sender's `limits` (`new_contacts_per_day`, `new_contacts_per_hour`) show today's numbers; past them a start answers `429 new_contact_limit` with `retry_after`: queue it, do not loop. iMessage lines start no cold conversations; WhatsApp needs a template and Meta's tier caps new contacts a day; SMS needs consent.
- The same first message to {{sending.abuse.same_text_contacts}} new contacts within an hour throttles a dedicated sender for {{sending.abuse.throttle_hours}} hours (`429 sender_throttled` on starts; replies still go). Personalise first messages; templates and media without a caption do not count. Limits and signals: quickstart section 10.
- Every send still ends `message.sent` or `message.failed`: count those, not the `202`s.

### Delete a person's data (GDPR)

`DELETE /v1/contacts/{contact_id}` (`204`, repeat-safe) erases the contact's name and address, all their message content and files, their events' payloads, pending deliveries and queued sends at once, and emits `contact.deleted`. IDs and timestamps stay. Find the contact ID on their events (`conversation.contact`) or `GET /v1/contacts`; there is no lookup by phone number or username. Content is otherwise kept 30 days.

Erasure removes Flow's copy only: messages already delivered stay on the person's phone. To remove those too, unsend them first (`DELETE /v1/messages/{message_id}`: Telegram within 48 hours, iMessage within 2 minutes; WhatsApp and SMS cannot), wait until each shows `status` `unsent`, then erase. After erasure nothing can be unsent.

### A leaked API key

1. Make a new key: dashboard ({{dashboard_url}}/keys, `?mode=live` for live keys) > **Create live key** (or test). Put it where the old one was and deploy.
2. Revoke the old one: Keys > **Revoke** on the key ending in its last four characters. It stops working at once; open streams close within a minute (`4401`).
3. Read `GET /v1/events` for sends you did not make. A leaked webhook secret: `POST /v1/webhook_endpoints/{webhook_endpoint_id}/rotate_secret`. A leaked bot token: revoke it in @BotFather and connect the new one (`POST /v1/senders`, same sender).

An app made without an account has no dashboard: get a new sandbox key, or sign in first.

### Prototype to production

1. Sign in to keep the app (`npx {{package}} login`): the app, its data and webhooks stay.
2. Dashboard > Live > **Create live key**; keep it apart from the test key (`{{env.live_key}}`).
3. Connect your own Telegram bot (`POST /v1/senders`, quickstart section 7) or your own WhatsApp number (`POST /v1/senders`, quickstart section 11); dedicated iMessage lines and SMS numbers are connected by the Flow team. Flow's shared iMessage line needs no live key: it comes with the free trial a sign-in starts ({{trial.people_per_channel}} people per channel).
4. Register the webhook again with the live key (endpoints belong to one mode). Nothing else in the code changes.

### Multi-tenant SaaS: one bot per customer

One app holds many senders: connect each customer's bot with your live key (`POST /v1/senders`) and keep the mapping customer to `snd_...` in your database. Events name the sender (`conversation.sender`) and the conversation, so route by those; replies leave from the conversation's own bot. Apps cannot be created through the API or the dashboard today (each sign-in has one app; up to {{allowance.claims_per_person}} sandbox apps can be claimed), so per-customer apps are not self-serve. A key belongs to one app and one mode.

### Delivery guarantees

- Inbound: every message becomes an event, stored before Flow answers the channel, delivered at least once and in order per conversation (dedupe on `event.id`). Webhooks retry for 3 days (5 s up to 12 h apart); the event log keeps everything for 30 days.
- Order per person: kept per conversation (one person on one sender; the same person on two channels or senders is two conversations, unordered between them). Inbound follows the channel's order (Telegram's update order; WhatsApp's timestamp, after a short hold for late webhooks). On iMessage the channel gives no order, so inbound goes in the order Flow receives it: two messages sent within about a second can arrive swapped. A webhook retry never reorders a conversation: its next event waits until the one before is delivered or marked failed.
- Outbound: a `202` means stored and queued; every send then ends `message.sent` or `message.failed`, never silently. One conversation sends one message at a time, in order. Retryable channel errors are retried by Flow in place, and later sends to that person wait; a failed send holds nothing back. When a send's outcome is unknown (the channel took it but never answered), Flow resends it once, so a rare duplicate is possible on Telegram; if that is unknown too, the message fails with `channel_timeout_unknown_outcome` (it may have arrived: check before sending again).
- Requests: `Idempotency-Key` on every POST makes your own retries safe for 24 hours; it cannot undo the channel-side resend above.

### Sent but not received: a checklist

1. **Did the send end?** `GET /v1/messages/{message_id}`, or `GET /v1/events?conversation=conv_...&type=message.sent&type=message.failed`. `queued`: still waiting (an earlier message in the conversation, the sender's pace, or a bot whose token Telegram rejected: reconnect it). `sent`: the channel took it (Telegram reports nothing after that). `failed`: read `error.type`, `error.channel_code` and `error.hint`.
2. **Common `message.failed` codes**: `permission` with `sandbox_contact_left` (the person joined another app on the shared sandbox bot while the message waited: they send your app's `join_code` message again); `channel_error` with `channel_code` `403` on Telegram (the person blocked the bot, or never started it); `outside_window` (iMessage: they have not written recently; WhatsApp: `window_closed`, send a template; `queued_too_long`); `channel_timeout_unknown_outcome` (may have arrived).
3. **Sandbox (test key)**: the person joined *your* app: opened the sandbox bot's `address.link` and tapped Start, or sent the sender's `join_code` message. The join is also the conversation's first `message.received` (`/start`, or the join message without its code), right after `conversation.started`. One person belongs to one app per sandbox bot, so joining another app moves them (sends answer `403 permission`). A key made without an account expires after {{allowance.anonymous.key_ttl_days}} days and its contact is removed. Allowance refusals are `403 permission` (`sandbox_allowance_used`, `sandbox_contact_limit`).
4. **Your own bot (live key)**: the person pressed Start on that bot (a Telegram bot cannot write first), and you send with the live key: sandbox conversations belong to the test key and answer `404 not_found` with a live one.
5. **On the phone**: the chat with the right bot (the sandbox bot and your own bot are different chats) on the Telegram account that joined.
6. **Still stuck?** Write to the Flow team at {{team_contacts|or}} with the message ID (`msg_...`), conversation ID (`conv_...`), the call's `request_id`, test or live, and the time. Never your API key.

### Tests in CI, without a phone

Use a test key and simulated conversations: `POST /v1/test/conversations`, post the contact's turns to `.../inbound`, assert on your agent's replies with `.../transcript`. Free, no phone, parallel-safe; at most 500 simulated conversations per app (reuse them) and 120 requests a minute to `/v1/test/`. Keep the key in your CI's secret store. In tests, wait for events (stream or `GET /v1/events`), never fixed sleeps.

### Give a cofounder access

Not built yet: an account has one member (whoever signed in), and there are no invitations. Today a cofounder can sign in to get their own account, or you can hand them an API key from your Keys page (it acts as the app, not as them; revoke it when no longer needed).
