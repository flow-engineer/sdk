// Builders for the content union. Every send takes either a plain string (a text
// message) or one of these; they only build objects, so the API shape stays visible.
import type {
  Button,
  ButtonsContent,
  ContactCardContent,
  Content,
  EffectContent,
  LocationContent,
  MediaContent,
  ReactionContent,
  TemplateContent,
  TemplateParams,
  TextContent,
  VoiceContent,
} from "./types.js";

/** Plain text. */
export function text(value: string): TextContent {
  return { type: "text", text: value };
}

/** Markdown text, shown in each channel's own formatting. Pair with `fallback: "auto"` for channels without formatting. */
export function markdown(value: string): TextContent {
  return { type: "text", text: value, format: "markdown" };
}

type MediaSource = { url: string; file_id?: never } | { file_id: string; url?: never };
type MediaExtras = { caption?: string; filename?: string };

/** An image, video, document or audio file, by HTTPS `url` or by `file_id` from `flow.files.upload`. */
export function media(kind: MediaContent["kind"], source: string | MediaSource, extras: MediaExtras = {}): MediaContent {
  const src = typeof source === "string" ? (source.startsWith("file_") ? { file_id: source } : { url: source }) : source;
  return { type: "media", kind, ...src, ...extras };
}
export const image = (source: string | MediaSource, extras?: MediaExtras) => media("image", source, extras);
export const video = (source: string | MediaSource, extras?: MediaExtras) => media("video", source, extras);
export const document = (source: string | MediaSource, extras?: MediaExtras) => media("document", source, extras);
export const audio = (source: string | MediaSource, extras?: MediaExtras) => media("audio", source, extras);

/** A voice note, by HTTPS `url` or `file_id`. */
export function voice(source: string | MediaSource): VoiceContent {
  const src = typeof source === "string" ? (source.startsWith("file_") ? { file_id: source } : { url: source }) : source;
  return { type: "voice", ...src };
}

/**
 * Text with reply buttons (1 to 10). A tap arrives as `message.received` with
 * `button_reply` content carrying the button's `id`. Strings become `{ id, label }`
 * with the label as id.
 */
export function buttons(value: string, items: Array<string | Button>): ButtonsContent {
  return {
    type: "buttons",
    text: value,
    buttons: items.map((b) => (typeof b === "string" ? { id: b, label: b } : b)),
  };
}

/** React to a message with one emoji, or `null` to remove your reaction. */
export function reaction(messageId: string, emoji: string | null): ReactionContent {
  return { type: "reaction", message_id: messageId, emoji };
}

/** A WhatsApp template (to start a conversation or write after the 24-hour window). */
export function template(templateId: string, language: string, params?: TemplateParams): TemplateContent {
  return { type: "template", template_id: templateId, language, ...(params ? { params } : {}) };
}

/** A place. */
export function location(lat: number, lng: number, extras: { name?: string; address?: string } = {}): LocationContent {
  return { type: "location", lat, lng, ...extras };
}

/** A contact card. */
export function contactCard(name: string, extras: { phones?: string[]; emails?: string[] } = {}): ContactCardContent {
  return { type: "contact_card", name, ...extras };
}

/** Text with an iMessage effect (other channels need `fallback: "auto"`). */
export function effect(value: string, name: EffectContent["effect"]): EffectContent {
  return { type: "effect", text: value, effect: name };
}

/**
 * The text a person would read in a piece of content: the text, a media caption, a
 * voice note's transcript, a tapped button's label, a place's name. `""` when none.
 *
 * ```ts
 * const said = contentText(event.data.message.content);
 * ```
 */
export function contentText(content: Content | undefined): string {
  if (!content) return "";
  switch (content.type) {
    case "text":
    case "effect":
      return content.text;
    case "media":
      return content.caption ?? "";
    case "voice":
      return content.transcript ?? "";
    case "button_reply":
      return content.label;
    case "buttons":
      return content.text;
    case "location":
      return [content.name, content.address].filter(Boolean).join(", ");
    case "contact_card":
      return content.name;
    case "file_blocked":
      return content.caption ?? "";
    default:
      return "";
  }
}
