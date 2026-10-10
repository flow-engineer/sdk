// A Flow Messaging webhook receiver with no dependencies (node:http).
// It verifies Flow-Signature on the raw body, dedupes on event.id, answers within
// 10 seconds, and replies to each message in the webhook answer: {"reply": ...}.
// Run: FLOW_MESSAGING_WEBHOOK_SECRET=whsec_... node main.ts   (Node 22.18 or later)
import { createHmac, timingSafeEqual } from "node:crypto";
import http from "node:http";

const SECRET = process.env.FLOW_MESSAGING_WEBHOOK_SECRET;
const PORT = Number(process.env.PORT ?? 3000);
if (!SECRET) {
  console.error("Set FLOW_MESSAGING_WEBHOOK_SECRET to the whsec_... secret from POST /v1/webhook_endpoints.");
  process.exit(1);
}

/**
 * Flow-Signature: t=<unix seconds>,v1=<hex>[,v1=<hex>]. Each v1 is the hex HMAC-SHA256,
 * keyed with the whole secret (whsec_ included), of "t." + t + "." + the raw body.
 * Two v1 values appear while a secret rotation overlaps: any one may match.
 */
function verify(header: string | undefined, rawBody: Buffer, secret: string, toleranceSec = 300): boolean {
  let t = "";
  const signatures: string[] = [];
  for (const part of (header ?? "").split(",")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    const k = part.slice(0, i).trim();
    const v = part.slice(i + 1).trim();
    if (k === "t") t = v;
    else if (k === "v1") signatures.push(v);
  }
  if (!/^\d+$/.test(t) || Math.abs(Date.now() / 1000 - Number(t)) > toleranceSec) return false;
  const want = createHmac("sha256", secret).update(`t.${t}.`).update(rawBody).digest();
  return signatures.some((s) => {
    const got = Buffer.from(s, "hex");
    return got.length === want.length && timingSafeEqual(got, want);
  });
}

const seen = new Set<string>(); // event IDs already handled (use your database in production)

http.createServer((req, res) => {
  const chunks: Buffer[] = [];
  req.on("data", (c: Buffer) => chunks.push(c));
  req.on("end", () => {
    const raw = Buffer.concat(chunks); // the raw bytes: verify before parsing
    if (req.method !== "POST" || req.url !== "/flow/webhook") return void res.writeHead(404).end();
    if (!verify(req.headers["flow-signature"] as string | undefined, raw, SECRET)) {
      console.log("rejected: bad Flow-Signature");
      return void res.writeHead(400).end();
    }
    const event = JSON.parse(raw.toString("utf8"));
    const answer = (body: unknown) => res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify(body));
    if (seen.has(event.id)) {
      console.log(`duplicate ${event.id}: skipped`); // delivery is at least once
      return answer({});
    }
    seen.add(event.id);

    if (event.type === "message.received") {
      const content = event.data.message.content;
      const said = content.type === "text" ? content.text : `a ${content.type}`;
      console.log(`${event.id} [${event.conversation.id}] ${said}`);
      // The reply goes into this conversation through the send gate, with the event ID as
      // its idempotency key. Keep it fast: slow agents answer {} and send through the API.
      return answer({ reply: { type: "text", text: `You said: ${said}` } });
    }
    if (event.type === "message.failed") {
      const e = event.data.message.error;
      console.log(`${event.id} send failed: ${e.type}: ${e.message} (${e.hint})`);
    }
    answer({}); // 2xx with no reply: delivered, nothing sent
  });
}).listen(PORT, () => console.log(`Listening on http://localhost:${PORT}/flow/webhook`));
