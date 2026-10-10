// An LLM support agent on Telegram. It keeps each conversation's history, answers
// with Claude (any LLM works: replace think()), and offers a "Talk to a human"
// button that hands the conversation to your team.
// Events come from the WebSocket stream, so no public URL is needed; replies go
// out with POST /v1/conversations/{id}/messages and an Idempotency-Key.
// Run: node main.ts             (FLOW_MESSAGING_KEY and ANTHROPIC_API_KEY set)
//      node main.ts --fake-llm  (no Anthropic key: a canned answer, for testing)
import Anthropic from "@anthropic-ai/sdk";

const KEY = process.env.FLOW_MESSAGING_KEY;
const BASE = (process.env.FLOW_MESSAGING_BASE_URL ?? "https://api.flow.engineer").replace(/\/+$/, "");
const FAKE_LLM = process.argv.includes("--fake-llm");
if (!KEY) {
  console.error("Set FLOW_MESSAGING_KEY. No key yet? curl -X POST https://api.flow.engineer/v1/sandbox/keys");
  process.exit(1);
}

const MODEL = "claude-sonnet-5-5";
const SYSTEM = `You are the support agent of Acme, chatting with a customer on Telegram.
Answer in at most three short sentences of plain text (no markdown).
If you cannot help, tell them to tap "Talk to a human".`;
const HUMAN = "talk_to_human"; // the button's id; a tap comes back as button_reply with this id

const anthropic = FAKE_LLM ? null : new Anthropic(); // reads ANTHROPIC_API_KEY
const history = new Map<string, Anthropic.MessageParam[]>(); // conversation id -> turns (use a database in production)
const withHuman = new Set<string>(); // conversations handed to a person: the agent stays quiet

/** Calls the Flow API. Retries 429 and 5xx with the same Idempotency-Key, so a retry never sends twice. */
async function flow(path: string, body: unknown, idempotencyKey: string) {
  for (let attempt = 1; ; attempt++) {
    const res = await fetch(BASE + path, {
      method: "POST",
      headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({ error: { type: "api_error", message: res.statusText, hint: "Retry later." } }));
    if (res.ok) return data;
    if ((res.status !== 429 && res.status < 500) || attempt === 5) {
      throw Object.assign(new Error(`${data.error.type}: ${data.error.message} (${data.error.hint})`), { error: data.error });
    }
    const wait = Number(res.headers.get("Retry-After") ?? 2 ** attempt);
    await new Promise((r) => setTimeout(r, wait * 1000));
  }
}

/** Asks the LLM for the next answer in a conversation and records both turns. */
async function think(conversationId: string, text: string): Promise<string> {
  const messages: Anthropic.MessageParam[] = [...(history.get(conversationId) ?? []), { role: "user", content: text }];
  let answer: string;
  if (anthropic) {
    const res = await anthropic.messages.create({ model: MODEL, max_tokens: 1024, system: SYSTEM, messages });
    answer = res.stop_reason === "refusal"
      ? `Sorry, I can't help with that here. Tap "Talk to a human".`
      : res.content.map((b) => (b.type === "text" ? b.text : "")).join("").trim();
  } else {
    answer = `(fake LLM) Answer ${Math.ceil(messages.length / 2)}: you said "${text}"`;
  }
  history.set(conversationId, [...messages, { role: "assistant" as const, content: answer }].slice(-20)); // even length: starts with a user turn
  return answer;
}

async function handle(event: any) {
  const conv = event.conversation.id;
  if (event.type === "message.failed") {
    const e = event.data.message.error;
    console.error(`[${conv}] send failed: ${e.type}: ${e.message} (${e.hint})`);
    return;
  }
  const message = event.data.message;
  const content = message.content;

  if (content.type === "button_reply" && content.button_id === HUMAN) {
    withHuman.add(conv);
    console.log(`[${conv}] handed to a human`); // notify your team here
    await flow(`/v1/conversations/${conv}/messages`,
      { content: { type: "text", text: "Thanks. A person from our team will answer here soon." } }, `reply-${message.id}`);
    return;
  }
  const text = content.type === "text" ? content.text : content.type === "button_reply" ? content.label : null;
  if (withHuman.has(conv)) {
    console.log(`[${conv}] (with a human) ${text ?? content.type}`);
    return;
  }
  console.log(`[${conv}] customer: ${text ?? content.type}`);
  if (text === null) {
    await flow(`/v1/conversations/${conv}/messages`,
      { content: { type: "text", text: "I can read text messages only." } }, `reply-${message.id}`);
    return;
  }

  // Optional: show "typing..." while the LLM thinks. It can fail; never let that stop the reply.
  flow(`/v1/conversations/${conv}/typing`, { state: "on" }, `typing-${message.id}`).catch(() => {});
  const answer = await think(conv, text);
  console.log(`[${conv}] agent: ${answer}`);
  try {
    // The key comes from the inbound message: one reply per message, however often this runs.
    await flow(`/v1/conversations/${conv}/messages`, {
      content: { type: "buttons", text: answer.slice(0, 1024), buttons: [{ id: HUMAN, label: "Talk to a human" }] },
      fallback: "auto", // channels without buttons get numbered text instead
    }, `reply-${message.id}`);
  } catch (err: any) {
    // An LLM answers differently each time: if this message was already answered (a
    // replayed event after a crash), the same key with a new body is refused. Keep the first.
    if (err.error?.type !== "idempotency_conflict") throw err;
    console.log(`[${conv}] already answered ${message.id}`);
  }
}

// One queue per conversation: messages are handled in order, conversations in parallel.
const queues = new Map<string, Promise<void>>();
const seen = new Set<string>(); // delivery is at least once: dedupe on event.id
let lastEventId: string | undefined;

function connect() {
  const url = new URL(`${BASE.replace(/^http/, "ws")}/v1/stream`);
  url.searchParams.append("type", "message.received");
  url.searchParams.append("type", "message.failed");
  if (lastEventId) url.searchParams.set("after", lastEventId);
  const ws = new WebSocket(url, ["flow", `flow.key.${KEY}`]); // the key as a subprotocol, never in the URL
  ws.onopen = () => console.log(`Support agent ready${FAKE_LLM ? " (fake LLM)" : ""}. Write to your sandbox bot.`);
  ws.onmessage = (msg) => {
    const frame = JSON.parse(String(msg.data));
    if (frame.type === "reconnect") {
      if (frame.after) lastEventId = frame.after;
      ws.close();
      return;
    }
    if (frame.type === "error") console.error(`${frame.error.type}: ${frame.error.message} (${frame.error.hint})`);
    if (frame.type !== "event") return;
    const event = frame.event;
    lastEventId = event.id;
    if (seen.has(event.id)) return;
    seen.add(event.id);
    const conv = event.conversation.id;
    const next = (queues.get(conv) ?? Promise.resolve())
      .then(() => handle(event))
      .catch((err) => console.error(`[${conv}] ${err.message}`));
    queues.set(conv, next);
  };
  ws.onclose = (ev) => {
    // A refused stream (bad, revoked or expired key; a bad request) sends an error
    // frame, then closes with 4401, 4403 or 4400: reconnecting will not help.
    if (ev.code === 4401 || ev.code === 4403 || ev.code === 4400) {
      console.error(`Stream refused (${ev.code}): ${ev.reason}`);
      process.exit(1);
    }
    console.log("Stream closed; reconnecting.");
    setTimeout(connect, 1000);
  };
}

connect();
