// The smallest Flow Messaging agent: answers every message with what it said.
// Run: node --env-file=.env agent.mjs   (FLOW_MESSAGING_KEY in .env)
import { FlowMessaging, contentText } from "@flow-engineer/messaging";

const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY

// Where to join: each sandbox sender's link, and its join message (join_code) to send as is.
for await (const s of flow.senders.list()) {
  if (s.kind === "shared") console.log(`${s.channel}: ${s.address.link ?? s.address.handle ?? s.address.phone ?? s.id}` + (s.join_code ? ` (or send "${s.join_code}")` : ""));
}
console.log("Echo agent ready. From your phone, open the sandbox link and tap Start, or send the join message.");

for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const content = event.data.message.content;
  const said = contentText(content) || `a ${content.kind}`;
  console.log(`[${event.conversation.channel}] ${event.conversation.id}: ${said}`);
  await event.conversation.reply(`You said: ${said}`);
}
