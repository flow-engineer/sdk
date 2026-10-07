// A Claude Agent SDK agent. query() streams SDK messages; reply() reads their text
// and sends it as chat bubbles. Each conversation resumes its own Claude session.
// Run: npm start   (FLOW_MESSAGING_KEY and ANTHROPIC_API_KEY in .env)
import { query, type SDKMessage } from "@anthropic-ai/claude-agent-sdk";
import { FlowMessaging, contentText } from "@flow-engineer/messaging";

const flow = new FlowMessaging();
const sessions = new Map<string, string>(); // conversation id -> Claude session id

/** Passes the messages through and remembers the session to resume next time. */
async function* remember(conversationId: string, messages: AsyncIterable<SDKMessage>) {
  for await (const m of messages) {
    if (m.session_id) sessions.set(conversationId, m.session_id);
    yield m;
  }
}

console.log("Agent ready. Message a sandbox sender from your phone.");
for await (const event of flow.events.stream({ types: ["message.received"] })) {
  const conv = event.conversation;
  const messages = query({
    prompt: contentText(event.data.message.content),
    options: {
      systemPrompt: `You are a helpful assistant chatting with a person on ${conv.channel}. Answer in a few short sentences.`,
      maxTurns: 1,
      allowedTools: [],
      resume: sessions.get(conv.id),
    },
  });
  await conv.reply(remember(conv.id, messages));
}
