// Telegram echo agent: answers every message with what it said.
// It reads events from the WebSocket stream (GET /v1/stream), so no public URL is
// needed, and replies with `send` frames on the same socket.
// Run: FLOW_MESSAGING_KEY=fk_test_... node main.ts   (Node 22.18 or later, no dependencies)

const KEY = process.env.FLOW_MESSAGING_KEY;
const BASE = (process.env.FLOW_MESSAGING_BASE_URL ?? "https://api.flow.engineer").replace(/\/+$/, "");
if (!KEY) {
  console.error("Set FLOW_MESSAGING_KEY. No key yet? curl -X POST https://api.flow.engineer/v1/sandbox/keys");
  process.exit(1);
}

// Show where to write: the sandbox bot's link (it joins your app when tapped).
const res = await fetch(`${BASE}/v1/senders?channel=telegram`, { headers: { Authorization: `Bearer ${KEY}` } });
const senders = await res.json();
if (!res.ok) throw new Error(`${senders.error.type}: ${senders.error.message} (${senders.error.hint})`);
for (const s of senders.data) {
  console.log(`Write to ${s.address.link ?? "@" + s.address.username}` + (s.join_code ? ` (or send "${s.join_code}")` : ""));
}

let lastEventId: string | undefined; // resume point after a reconnect
const seen = new Set<string>(); // delivery is at least once: dedupe on event.id

function connect() {
  const url = new URL(`${BASE.replace(/^http/, "ws")}/v1/stream`);
  url.searchParams.append("type", "message.received");
  if (lastEventId) url.searchParams.set("after", lastEventId);
  // Node's WebSocket cannot set headers, so the key goes in the subprotocol, never the URL.
  const ws = new WebSocket(url, ["flow", `flow.key.${KEY}`]);

  ws.onopen = () => console.log("Echo agent ready.");
  ws.onmessage = (msg) => {
    const frame = JSON.parse(String(msg.data));
    if (frame.type === "event") {
      const event = frame.event;
      lastEventId = event.id;
      if (seen.has(event.id)) return;
      seen.add(event.id);
      const message = event.data.message;
      const said = message.content.type === "text" ? message.content.text : `a ${message.content.type}`;
      console.log(`[${event.conversation.id}] ${said}`);
      // `ref` is the idempotency key: derived from the inbound message, so a replay never sends twice.
      ws.send(JSON.stringify({
        type: "send",
        ref: `echo-${message.id}`,
        conversation: event.conversation.id,
        message: { content: { type: "text", text: `You said: ${said}` } },
      }));
    } else if (frame.type === "ack") {
      console.log(`  -> sent ${frame.message.id}`);
    } else if (frame.type === "error") {
      console.error(`  -> ${frame.error.type}: ${frame.error.message} (${frame.error.hint})`);
    } else if (frame.type === "reconnect") {
      if (frame.after) lastEventId = frame.after;
      ws.close();
    }
  };
  ws.onclose = () => {
    console.log("Stream closed; reconnecting.");
    setTimeout(connect, 1000); // resumes from lastEventId
  };
}

connect();
