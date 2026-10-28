// Send, wait for the reply, continue: a short sign-up chat, written top to bottom.
// No polling loop and no event cursors: the SDK waits for the join, each answer and
// each send's outcome. Run: node --env-file=.env agent.ts   (Node 22.18+; FLOW_MESSAGING_KEY in .env)
import { FlowMessaging, WaitTimeoutError, contentText } from "@flow-engineer/messaging";

const flow = new FlowMessaging(); // reads FLOW_MESSAGING_KEY

// Take the time before showing the link: someone who joins quickly still counts.
const since = new Date();
for await (const s of flow.senders.list()) {
  if (s.address.link) console.log(`Join: ${s.address.link}` + (s.join_code ? ` (or send "${s.join_code}")` : ""));
}
console.log("Waiting for someone to join or write...");

// The next contact who joins the sandbox or writes first (or did since `since`).
const conv = await flow.conversations.waitForNew({ since, timeoutMs: 10 * 60_000 });
console.log(`[${conv.id}] joined on ${conv.channel}`);
// Their first message comes next: the join itself ("/start" from the sandbox link,
// "Join <app>" from the join message) or what they wrote first. Take it, so it is not
// read as the answer to the first question.
await conv.waitForReply({ timeoutMs: 60_000 });

try {
  // ask() sends the question and resolves with the contact's next message after it.
  const name = contentText((await conv.ask("Hi! What's your name?", { timeoutMs: 5 * 60_000 })).content);
  console.log(`[${conv.id}] name: ${name}`);

  const city = contentText((await conv.ask(`Nice to meet you, ${name}. Which city are you in?`, { timeoutMs: 5 * 60_000 })).content);
  console.log(`[${conv.id}] city: ${city}`);

  // sendAndWait() resolves once the channel accepted the message, and throws the
  // message's typed error (ChannelError, PermissionError, ...) if it fails.
  const done = await conv.sendAndWait(`Thanks, ${name}! You're signed up in ${city}.`);
  console.log(`[${conv.id}] ${done.status} ${done.id}`);
} catch (err) {
  if (!(err instanceof WaitTimeoutError)) throw err;
  console.log(`[${conv.id}] no answer in time`);
  await conv.send("No rush: write again whenever you're ready.");
}
