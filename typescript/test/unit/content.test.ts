import { describe, expect, it } from "vitest";
import {
  basic,
  buttons,
  carousel,
  contactCard,
  contentText,
  document,
  effect,
  image,
  list,
  location,
  media,
  reaction,
  template,
  voice,
} from "../../src/index.js";

describe("kind builders", () => {
  it("build kind objects with kind set, converting nothing", () => {
    expect(basic("**Hi**")).toEqual({ kind: "basic", text: "**Hi**" });
    expect(basic({ text: "See https://example.com", link_preview: false })).toEqual({ kind: "basic", text: "See https://example.com", link_preview: false });
    expect(image("file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5", "A")).toEqual({ kind: "basic", text: "A", media: { type: "image", file_id: "file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5" } });
    expect(document("https://example.com/a.pdf")).toEqual({ kind: "basic", media: { type: "document", url: "https://example.com/a.pdf" } });
    expect(media("document", "https://example.com/a.pdf", { filename: "a.pdf" }).media).toEqual({ type: "document", url: "https://example.com/a.pdf", filename: "a.pdf" });
    expect(voice("https://example.com/a.ogg")).toEqual({ kind: "voice", url: "https://example.com/a.ogg" });
    expect(buttons("Size?", ["S", { id: "m", label: "M" }])).toEqual({ kind: "buttons", text: "Size?", buttons: [{ id: "S", label: "S" }, { id: "m", label: "M" }] });
    expect(list("Which?", "Sizes", [{ title: "All", rows: [{ id: "s", title: "Small" }] }]).sections).toEqual([{ title: "All", rows: [{ id: "s", title: "Small" }] }]);
    expect(carousel("Pick", []).kind).toBe("carousel");
    expect(template("tpl_01JB8ZG7Q9S1V3X5Z7B9D1F3G5", "en")).toEqual({ kind: "template", template_id: "tpl_01JB8ZG7Q9S1V3X5Z7B9D1F3G5", language: "en" });
    expect(location(1, 2, { name: "Office" })).toEqual({ kind: "location", lat: 1, lng: 2, name: "Office" });
    expect(contactCard("Asha", { phones: ["+15550100"] })).toEqual({ kind: "contact_card", name: "Asha", phones: ["+15550100"] });
    expect(effect("Happy birthday", "balloons")).toEqual({ kind: "effect", text: "Happy birthday", effect: "balloons" });
    expect(reaction("msg_1", null)).toEqual({ kind: "reaction", message_id: "msg_1", emoji: null });
  });

  it("contentText reads what a person would read", () => {
    expect(contentText({ kind: "basic", text: "hi" })).toBe("hi");
    expect(contentText({ kind: "voice", transcript: "hello there" } as never)).toBe("hello there");
    expect(contentText({ kind: "button_reply", button_id: "s", label: "Small", message_id: "msg_1" } as never)).toBe("Small");
    expect(contentText({ kind: "location", lat: 1, lng: 2, name: "Office", address: "1 Main St" })).toBe("Office, 1 Main St");
    expect(contentText({ kind: "reaction", message_id: "msg_1", emoji: "👍" })).toBe("");
    expect(contentText(undefined)).toBe("");
  });
});
