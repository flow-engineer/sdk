// A LangChain.js chat model with per-conversation history. model.stream() goes
// straight to reply(); the sent bubbles are the assistant's turn in the history.
// Run: npm start   (FLOW_MESSAGING_KEY and OPENAI_API_KEY in .env)
import { AIMessage, HumanMessage, SystemMessage, type BaseMessage } from "@langchain/core/messages";
import { ChatOpenAI } from "@langchain/openai";
import { FlowMessaging, contentText } from "@flow-engineer/messaging";

const model = new ChatOpenAI({ model: "gpt-4o-mini" });
const flow = new FlowMessaging();
const system = new SystemMessage("You are a helpful assistant in a chat app. Be concise.");
const history = new Map<string, BaseMessage[]>(); // per conversation: one person on one channel

console.log("Agent ready. Message a sandbox sender from your phone.");
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const conv = event.conversation;
  const turns = history.get(conv.id) ?? [];
  turns.push(new HumanMessage(contentText(event.data.message.content)));

  const sent = await conv.reply(await model.stream([system, ...turns]));
  turns.push(new AIMessage(sent.map((m) => contentText(m.content)).join("\n\n")));
  history.set(conv.id, turns.slice(-20));
}
