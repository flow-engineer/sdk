// Builders for kind objects. Each returns a plain object with `kind` set, ready for
// `flow.messages.send`, `conversation.reply`, a webhook reply or the kind's own method
// (`flow.messages.buttons(id, buttons(...))`). They only build objects: nothing is
// converted, so what you build is what the API gets.
import type {
  BasicKind,
  BasicMessage,
  Button,
  ButtonsKind,
  ButtonsMessage,
  CarouselCard,
  CarouselKind,
  ContactCardKind,
  ContactCardMessage,
  EffectKind,
  EffectMessage,
  ListKind,
  ListMessage,
  ListRow,
  ListSection,
  LocationKind,
  LocationMessage,
  Media,
  MessageContent,
  OutboundKind,
  ReactionKind,
  TemplateKind,
  TemplateParams,
  VoiceKind,
} from "./types.js";

type MediaSource = { url: string; file_id?: never } | { file_id: string; url?: never };

function source(src: string | MediaSource): MediaSource {
  return typeof src === "string" ? (src.startsWith("file_") ? { file_id: src } : { url: src }) : src;
}

/**
 * A `basic` message: text (sent exactly as written), or the fields of a basic message
 * (`media`, `reply_to`, `link_preview`, a `telegram` or `imessage` block).
 *
 * ```ts
 * basic("Your order shipped.");
 * basic({ text: "See https://example.com", link_preview: false });
 * ```
 */
export function basic(input: string | Omit<BasicMessage, "kind">): BasicKind {
  return typeof input === "string" ? { kind: "basic", text: input } : { kind: "basic", ...input };
}

/**
 * A `basic` message with one file: by HTTPS `url`, or by `file_id` (`file_...`, from
 * `flow.files.upload`). `caption` is the message's `text`.
 */
export function media(type: Media["type"], src: string | MediaSource, extras: { caption?: string; filename?: string } = {}): BasicKind {
  const m: Media = { type, ...source(src) };
  if (extras.filename !== undefined) m.filename = extras.filename;
  return extras.caption === undefined ? { kind: "basic", media: m } : { kind: "basic", text: extras.caption, media: m };
}
/** A `basic` message with an image, by URL or `file_id`, and an optional caption. */
export const image = (src: string | MediaSource, caption?: string): BasicKind => media("image", src, { caption });
/** A `basic` message with a video, by URL or `file_id`, and an optional caption. */
export const video = (src: string | MediaSource, caption?: string): BasicKind => media("video", src, { caption });
/** A `basic` message with an audio file, by URL or `file_id`, and an optional caption. For a voice note use `voice`. */
export const audio = (src: string | MediaSource, caption?: string): BasicKind => media("audio", src, { caption });
/** A `basic` message with a document, by URL or `file_id`, and an optional caption. Name it with `media("document", src, { filename })`. */
export const document = (src: string | MediaSource, caption?: string): BasicKind => media("document", src, { caption });

/** A `voice` note, by HTTPS `url` or `file_id`. */
export function voice(src: string | MediaSource, extras: Pick<VoiceKind, "reply_to" | "metadata"> = {}): VoiceKind {
  return { kind: "voice", ...source(src), ...extras };
}

/**
 * A `buttons` message: text with reply buttons, or with one URL button. A string
 * becomes `{ id, label }` with the label as its id. A tap arrives as
 * `message.received` with `button_reply` content carrying the button's `id`.
 */
export function buttons(
  text: string,
  items: Array<string | Button>,
  extras: Omit<ButtonsMessage, "kind" | "text" | "buttons"> = {},
): ButtonsKind {
  return { kind: "buttons", text, buttons: items.map((b) => (typeof b === "string" ? { id: b, label: b } : b)), ...extras };
}

/**
 * A WhatsApp `list` message: `text`, the menu button's label, and its rows, given as
 * sections or, for one section without a title, as rows. A tap arrives as
 * `button_reply` with the row's `id`.
 *
 * ```ts
 * list("Which size?", "Sizes", [{ id: "s", title: "Small" }, { id: "m", title: "Medium" }]);
 * ```
 */
export function list(
  text: string,
  button: string,
  rows: ListSection[] | ListRow[],
  extras: Omit<ListMessage, "kind" | "text" | "button" | "sections"> = {},
): ListKind {
  const first = rows[0] as ListSection | ListRow | undefined;
  const sections: ListSection[] = first && "rows" in first ? (rows as ListSection[]) : [{ rows: rows as ListRow[] }];
  return { kind: "list", text, button, sections, ...extras };
}

/** A WhatsApp `carousel`: text and 2 to 10 cards. */
export function carousel(text: string, cards: CarouselCard[]): CarouselKind {
  return { kind: "carousel", text, cards };
}

/** A WhatsApp `template` (to start a conversation, or to write after the 24-hour window). */
export function template(templateId: string, language: string, params?: TemplateParams): TemplateKind {
  return { kind: "template", template_id: templateId, language, ...(params ? { params } : {}) };
}

/** A `location`. */
export function location(lat: number, lng: number, extras: Omit<LocationMessage, "kind" | "lat" | "lng"> = {}): LocationKind {
  return { kind: "location", lat, lng, ...extras };
}

/** A `contact_card`. Telegram needs at least one phone. */
export function contactCard(name: string, extras: Omit<ContactCardMessage, "kind" | "name"> = {}): ContactCardKind {
  return { kind: "contact_card", name, ...extras };
}

/** An iMessage `effect`: text sent with a screen or bubble effect. */
export function effect(text: string, name: EffectMessage["effect"]): EffectKind {
  return { kind: "effect", text, effect: name };
}

/** A `reaction` to a message: one emoji, or `null` to remove yours. */
export function reaction(messageId: string, emoji: string | null): ReactionKind {
  return { kind: "reaction", message_id: messageId, emoji };
}

/**
 * The text a person would read in a message: its text (a media caption included), a
 * voice note's transcript, a tapped button's label, a place's name. `""` when none.
 *
 * ```ts
 * const said = contentText(event.data.message.content);
 * ```
 */
export function contentText(content: MessageContent | OutboundKind | undefined): string {
  if (!content) return "";
  const c = content as { kind: string; text?: string; transcript?: string; label?: string; name?: string; address?: string; caption?: string };
  switch (c.kind) {
    case "basic":
    case "buttons":
    case "list":
    case "carousel":
    case "effect":
    case "edit":
      return c.text ?? "";
    case "voice":
      return c.transcript ?? "";
    case "button_reply":
      return c.label ?? "";
    case "location":
      return [c.name, c.address].filter(Boolean).join(", ");
    case "contact_card":
      return c.name ?? "";
    case "file_blocked":
      return c.caption ?? "";
    default:
      return "";
  }
}
