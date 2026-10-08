// The smallest Flow Messaging agent: answers every message with what it said.
// Run: node --env-file=.env agent.mjs   (FLOW_MESSAGING_KEY in .env)
import { FlowMessaging, contentText } from "@flow-engineer/messaging";

const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY

const { app } = await flow.app.retrieve();
console.log(`Echo agent ready. From your phone, message a sandbox sender: join ${app.sandbox_join_code}`);

for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const content = event.data.message.content;
  const said = contentText(content) || `a ${content.type}`;
  console.log(`[${event.conversation.channel}] ${event.conversation.id}: ${said}`);
  await event.conversation.reply(`You said: ${said}`);
}
