// A support agent on the Vercel AI SDK: streamText's result goes straight to
// reply(), which keeps typing on and sends the answer as chat bubbles.
// Run: npm start   (FLOW_MESSAGING_KEY and OPENAI_API_KEY in .env)
import { openai } from "@ai-sdk/openai";
import { FlowMessaging, contentText } from "@flow-engineer/messaging";
import { streamText, type ModelMessage } from "ai";

const flow = new FlowMessaging();
const history = new Map<string, ModelMessage[]>(); // per conversation: one person on one channel

console.log("Agent ready. Message a sandbox sender from your phone (npx @flow-engineer/messaging init shows how).");
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const conv = event.conversation;
  const messages = history.get(conv.id) ?? [];
  messages.push({ role: "user", content: contentText(event.data.message.content) || "(sent an attachment)" });

  const result = streamText({
    model: openai("gpt-4o-mini"),
    system: `You are a friendly shop assistant chatting on ${conv.channel}. Keep answers short.`,
    messages,
  });
  await conv.reply(result);
  messages.push({ role: "assistant", content: await result.text });
  history.set(conv.id, messages.slice(-20));
}
