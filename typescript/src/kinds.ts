// Which endpoint each kind is sent to, for `flow.messages.send` and `reply`.
import type { ConversationAction, Message, OutboundKind, ReadKind, TypingKind } from "./types.js";

/** What `send` takes: a kind object (`{ kind: "buttons", ... }`), or a string, short for `{ kind: "basic", text }`. */
export type SendInput = string | OutboundKind;
/** A `SendInput` that makes a message (every kind but `typing` and `read`): what `sendAndWait`, `ask` and `reply` take. */
export type MessageInput = string | Exclude<OutboundKind, TypingKind | ReadKind>;
/** What `send` resolves with: a `ConversationAction` for `typing` and `read`, else the `Message`. */
export type SendResult<I> = I extends TypingKind | ReadKind ? ConversationAction : Message;

/** Each kind sent with `POST /v0/conversations/{conversation_id}/<path>`. */
export const KIND_PATHS: Readonly<Record<string, string>> = {
  basic: "basic",
  voice: "voice",
  buttons: "buttons",
  list: "list",
  carousel: "carousel",
  template: "template",
  contact_card: "contact-card",
  location: "location",
  effect: "effect",
  reaction: "reaction",
  typing: "typing",
  read: "read",
};
const SENDABLE = [...Object.keys(KIND_PATHS), "edit", "unsend"];

/** The kind object a `SendInput` stands for, or a `TypeError` when it names no kind that can be sent. */
export function toKind(input: SendInput): OutboundKind {
  if (typeof input === "string") return { kind: "basic", text: input };
  const kind = (input as { kind?: unknown } | null)?.kind;
  if (typeof kind !== "string" || !SENDABLE.includes(kind)) {
    throw new TypeError(
      `Cannot send ${kind === undefined ? "an object without a kind" : `kind ${JSON.stringify(kind)}`}: give one of ${SENDABLE.join(", ")}, or a string for basic text.`,
    );
  }
  return input;
}

