// The list parameter types are written out by hand (src/types.ts) so editors show
// each field; these checks fail when one differs from the spec's query parameters.
import { describe, expectTypeOf, it } from "vitest";
import type {
  ListContactsParams,
  ListConversationsParams,
  ListEventsParams,
  ListMessagesParams,
  ListSendersParams,
  ListTemplatesParams,
  ListWebhookEndpointsParams,
  TestTranscriptParams,
  operations,
} from "../../src/index.js";

type Query<K extends keyof operations> = NonNullable<operations[K]["parameters"]["query"]>;

describe("list parameter types", () => {
  it("match the spec's query parameters", () => {
    expectTypeOf<ListEventsParams>().toEqualTypeOf<Query<"listEvents">>();
    expectTypeOf<ListConversationsParams>().toEqualTypeOf<Query<"listConversations">>();
    expectTypeOf<ListMessagesParams>().toEqualTypeOf<Query<"listConversationMessages">>();
    expectTypeOf<ListSendersParams>().toEqualTypeOf<Query<"listSenders">>();
    expectTypeOf<ListTemplatesParams>().toEqualTypeOf<Query<"listTemplates">>();
    expectTypeOf<ListWebhookEndpointsParams>().toEqualTypeOf<Query<"listWebhookEndpoints">>();
    expectTypeOf<ListContactsParams>().toEqualTypeOf<Query<"listContacts">>();
    expectTypeOf<TestTranscriptParams>().toEqualTypeOf<Query<"getTestTranscript">>();
  });
});
