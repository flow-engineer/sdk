// An OpenAI Agents SDK agent with a tool. The streamed run goes straight to reply().
// Run: npm start   (FLOW_MESSAGING_KEY and OPENAI_API_KEY in .env)
import { Agent, run, tool } from "@openai/agents";
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
import { z } from "zod";

const orderStatus = tool({
  name: "order_status",
  description: "Look up an order's delivery status by its number.",
  parameters: z.object({ order: z.string() }),
  execute: async ({ order }) => `Order ${order} ships tomorrow and arrives in 2 days.`,
});

const agent = new Agent({
  name: "Support",
  instructions: "You answer customers in a chat app. Be brief. Use order_status for order questions.",
  model: "gpt-4o-mini",
  tools: [orderStatus],
});

const flow = new FlowMessaging();
const lastResponse = new Map<string, string>(); // conversation id -> previous response, for memory

console.log("Agent ready. Message a sandbox sender from your phone.");
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const conv = event.conversation;
  const result = await run(agent, contentText(event.data.message.content), {
    stream: true,
    previousResponseId: lastResponse.get(conv.id),
  });
  await conv.reply(result);
  await result.completed;
  if (result.lastResponseId) lastResponse.set(conv.id, result.lastResponseId);
}
