// A Mastra agent. agent.stream()'s result has a textStream, which reply() reads.
// Run: npm start   (FLOW_MESSAGING_KEY and OPENAI_API_KEY in .env)
import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import { FlowMessaging, contentText } from "@flow-engineer/messaging";

const agent = new Agent({
  id: "concierge",
  name: "concierge",
  instructions: "You are a hotel concierge chatting with guests. Keep replies short and warm.",
  model: openai("gpt-4o-mini"),
});

const flow = new FlowMessaging();

console.log("Agent ready. Message a sandbox sender from your phone.");
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const result = await agent.stream(contentText(event.data.message.content));
  await event.conversation.reply(result);
}
