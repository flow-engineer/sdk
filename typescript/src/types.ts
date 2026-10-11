// Friendly names for the types generated from the OpenAPI spec
// (src/generated/openapi.ts, made by `npm run generate`; never edit that file).
import type { components } from "./generated/openapi.js";

type S = components["schemas"];

export type { components, operations, paths, webhooks } from "./generated/openapi.js";

export type Channel = S["Channel"];
export type Mode = S["Mode"];
export type Metadata = S["Metadata"];
export type Deleted = S["Deleted"];
export type ErrorType = S["ErrorType"];
export type ErrorBody = S["ErrorBody"];

export type Account = S["Account"];
export type App = S["App"];
export type AppSettings = S["AppSettings"];
export type ApiKey = S["ApiKey"];
export type AppContext = S["AppContext"];

export type SandboxAllowance = S["SandboxAllowance"];
export type AllowanceCount = S["AllowanceCount"];
export type AllowanceMessages = S["AllowanceMessages"];
export type SandboxKeyRequest = S["SandboxKeyRequest"];
export type SandboxKey = S["SandboxKey"];
export type DeviceAuthorizationRequest = S["DeviceAuthorizationRequest"];
export type DeviceAuthorization = S["DeviceAuthorization"];
export type DeviceTokenRequest = S["DeviceTokenRequest"];
export type DeviceToken = S["DeviceToken"];
export type SignedInUser = S["SignedInUser"];

export type Sender = S["Sender"];
export type SenderKind = S["SenderKind"];
export type SenderStatus = S["SenderStatus"];
export type SenderAddress = S["SenderAddress"];
export type SenderLimits = S["SenderLimits"];
export type SenderRequest = S["SenderRequest"];

export type Contact = S["Contact"];
export type ContactAddress = S["ContactAddress"];
export type Recipient = S["Recipient"];

export type Conversation = S["Conversation"];
export type ConversationRef = S["ConversationRef"];
export type ConversationAction = S["ConversationAction"];

export type Message = S["Message"];
export type MessageStatus = S["MessageStatus"];
export type MessageDirection = S["MessageDirection"];
export type DeliveredAs = S["DeliveredAs"];
export type Fallback = S["Fallback"];
export type ChannelOptions = S["ChannelOptions"];
export type SendMessageRequest = S["SendMessageRequest"];
export type StartConversationRequest = S["StartConversationRequest"];
export type EditMessageRequest = S["EditMessageRequest"];

export type ContentType = S["ContentType"];
export type Content = S["Content"];
export type TextContent = S["TextContent"];
export type MediaContent = S["MediaContent"];
export type VoiceContent = S["VoiceContent"];
export type ButtonsContent = S["ButtonsContent"];
export type Button = S["Button"];
export type ReplyButton = S["ReplyButton"];
export type UrlButton = S["UrlButton"];
export type ButtonReplyContent = S["ButtonReplyContent"];
export type ReactionContent = S["ReactionContent"];
export type TemplateContent = S["TemplateContent"];
export type TemplateParams = S["TemplateParams"];
export type LocationContent = S["LocationContent"];
export type ContactCardContent = S["ContactCardContent"];
export type EffectContent = S["EffectContent"];
export type TypingContent = S["TypingContent"];
export type ReadContent = S["ReadContent"];
export type EditContent = S["EditContent"];
export type UnsendContent = S["UnsendContent"];
export type FileBlockedContent = S["FileBlockedContent"];

export type EventType = S["EventType"];
/**
 * One entry in your app's event log as the API sends it (plain JSON; `conversation` is
 * a `ConversationRef`): a discriminated union on `type`. `flow.events.list()` and
 * `retrieve()` return it. Handlers given events by `flow.events.stream()` or
 * `flow.webhooks` receive a `FlowEvent` instead, whose `conversation` can `reply`.
 */
export type Event = S["Event"];
export type MessageReceivedEvent = S["MessageReceivedEvent"];
export type MessageSentEvent = S["MessageSentEvent"];
export type MessageDeliveredEvent = S["MessageDeliveredEvent"];
export type MessageReadEvent = S["MessageReadEvent"];
export type MessageFailedEvent = S["MessageFailedEvent"];
export type ReactionAddedEvent = S["ReactionAddedEvent"];
export type ReactionRemovedEvent = S["ReactionRemovedEvent"];
export type TypingStartedEvent = S["TypingStartedEvent"];
export type TypingStoppedEvent = S["TypingStoppedEvent"];
export type ConversationStartedEvent = S["ConversationStartedEvent"];
export type ConversationWindowClosingEvent = S["ConversationWindowClosingEvent"];
export type SenderStatusChangedEvent = S["SenderStatusChangedEvent"];
export type TemplateStatusChangedEvent = S["TemplateStatusChangedEvent"];
/** The event whose `type` is `T`. */
export type EventOf<T extends EventType> = Extract<Event, { type: T }>;

export type StreamFrame = S["StreamFrame"];
export type Capabilities = S["Capabilities"];
export type ContentSupport = S["ContentSupport"];
export type File = S["File"];
export type Template = S["Template"];
export type TemplateStatus = S["TemplateStatus"];
export type TemplateCreateRequest = S["TemplateCreateRequest"];
export type WebhookEndpoint = S["WebhookEndpoint"];
export type WebhookEndpointCreateRequest = S["WebhookEndpointCreateRequest"];
export type WebhookEndpointUpdateRequest = S["WebhookEndpointUpdateRequest"];
export type WebhookSecretRotateRequest = S["WebhookSecretRotateRequest"];
export type WebhookReply = S["WebhookReply"];
export type TestConversationRequest = S["TestConversationRequest"];
export type TestContactAddress = S["TestContactAddress"];
export type SimulatedInboundRequest = S["SimulatedInboundRequest"];
export type SimulatedInbound = S["SimulatedInbound"];
export type TestTranscript = S["TestTranscript"];
export type TranscriptEntry = S["TranscriptEntry"];

// ---------------------------------------------------------------- list parameters
// Written out by hand so editors show each field and its meaning; a type test
// (test/unit/params.test.ts) fails when one differs from the spec's query parameters.

/**
 * Cursor paging, shared by every list call. A list call returns a `PagePromise`:
 * `await` it for one page, or `for await` it to walk every item across pages (it
 * follows `after` for you).
 */
export interface PageParams {
  /** An item ID: returns the items that come after it in the list's order. Pass the last ID you processed to read on from there. */
  after?: string;
  /** An item ID: returns the items that come before it in the list's order. Give `after` or `before`, not both. */
  before?: string;
  /** How many items one page holds, 1 to 100 (default 20). */
  limit?: number;
}

/**
 * `flow.events.list(params)`: the event log, **oldest first**. Pass the last event you
 * processed as `after` to catch up; to wait for an event, use `flow.events.waitFor` or
 * the helpers on a conversation (`waitForReply`, `ask`) instead of listing in a loop.
 *
 * ```ts
 * const page = await flow.events.list({ type: ["message.received"], conversation: "conv_...", limit: 50 });
 * ```
 */
export interface ListEventsParams extends PageParams {
  /** Only events of these types (at most 20), e.g. `["message.received", "conversation.started"]`. */
  type?: EventType[];
  /** Only events in this conversation (`conv_...`). An ID with no conversation of this app and mode throws `NotFoundError`. */
  conversation?: string;
}

/** `flow.conversations.list(params)`: your app's conversations in this mode, newest first. */
export interface ListConversationsParams extends PageParams {
  /** Only conversations on this sender (`snd_...`). */
  sender?: string;
  /** Only conversations with this contact (`ct_...`). */
  contact?: string;
  /** Only conversations on this channel. */
  channel?: Channel;
}

/** `flow.conversations.messages(id, params)` and `conversation.messages(params)`: a conversation's messages, inbound and outbound, newest first. */
export type ListMessagesParams = PageParams;

/** `flow.senders.list(params)`: the senders your app can use in this mode. */
export interface ListSendersParams extends PageParams {
  /** Only senders on this channel. */
  channel?: Channel;
  /** Only senders of this kind. `simulated` lists your app's simulated senders (test keys only), which are otherwise left out. */
  kind?: SenderKind;
}

/** `flow.templates.list(params)`: WhatsApp templates of your senders, newest first. */
export interface ListTemplatesParams extends PageParams {
  /** Only templates of this sender (`snd_...`). */
  sender?: string;
  /** Only templates in this status. */
  status?: TemplateStatus;
}

/** `flow.webhookEndpoints.list(params)`: your app's webhook endpoints in this mode. */
export type ListWebhookEndpointsParams = PageParams;

/** `flow.contacts.list(params)`: your app's contacts in this mode. */
export interface ListContactsParams extends PageParams {
  /** Only contacts on this channel. */
  channel?: Channel;
}

/** `flow.test.transcript(id, params)`: both sides of a simulated conversation, oldest first. */
export interface TestTranscriptParams {
  /** An entry ID: returns the entries after it. */
  after?: string;
  /** How many entries one page holds, 1 to 100 (default 20). */
  limit?: number;
}
