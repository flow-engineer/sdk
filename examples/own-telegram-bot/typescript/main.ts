// Go live on Telegram with your own bot: connect the token BotFather gave you to Flow
// (POST /v1/senders), and disconnect it again (DELETE /v1/senders/{id}).
// Run: node main.ts connect                 (FLOW_MESSAGING_KEY=fk_live_..., TELEGRAM_BOT_TOKEN)
//      node main.ts disconnect snd_...      (FLOW_MESSAGING_KEY=fk_live_...)
// Node 22.18 or later, no dependencies.

const KEY = process.env.FLOW_MESSAGING_KEY;
const BASE = (process.env.FLOW_MESSAGING_BASE_URL ?? "https://api.flow.engineer").replace(/\/+$/, "");
const [command, senderId] = process.argv.slice(2);
if (!KEY) {
  console.error("Set FLOW_MESSAGING_KEY to your live key (fk_live_...). Signed in, create one at https://api.flow.engineer/admin/keys?mode=live (Create live key).");
  process.exit(1);
}

async function flow(method: string, path: string, body?: unknown) {
  const headers: Record<string, string> = { Authorization: `Bearer ${KEY}` };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  // Connecting is idempotent by nature (the same bot updates in place), so a fresh key per
  // run is right: a new token for the same bot must not replay yesterday's answer.
  if (method === "POST") headers["Idempotency-Key"] = crypto.randomUUID();
  const res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await res.json();
  if (!res.ok) {
    console.error(`${data.error.type}: ${data.error.message}\nhint: ${data.error.hint}`);
    process.exit(1);
  }
  return data;
}

if (command === "connect") {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) {
    console.error("Set TELEGRAM_BOT_TOKEN to the token @BotFather gave you.");
    process.exit(1);
  }
  // Flow checks the token, stores it encrypted, points the bot's webhook at Flow and
  // answers with the sender, active. The token is never returned.
  const sender = await flow("POST", "/v1/senders", { channel: "telegram", telegram_bot_token: token });
  console.log(`Connected @${sender.address.username} as ${sender.id} (status ${sender.status}).`);
  console.log(`Chat with it: ${sender.address.link}`);
  console.log(`Its messages now reach this live key, like the sandbox's reach a test key.`);
  console.log(`To disconnect: node main.ts disconnect ${sender.id}`);
} else if (command === "disconnect" && senderId) {
  // Removes the bot's webhook, deletes the stored token and retires the sender. Its
  // conversations and messages stay readable. Repeating the call is safe.
  const sender = await flow("DELETE", `/v1/senders/${encodeURIComponent(senderId)}`);
  console.log(`Disconnected ${sender.id} (status ${sender.status}).`);
} else {
  console.error("Usage: node main.ts connect | node main.ts disconnect snd_...");
  process.exit(1);
}
