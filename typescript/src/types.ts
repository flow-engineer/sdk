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
export type PeopleLimits = S["PeopleLimits"];
export type ChannelPeople = S["ChannelPeople"];
export type PeopleWindow = S["PeopleWindow"];

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
export type ImessageSender = S["ImessageSender"];
export type CallForwarding = S["CallForwarding"];

export type Contact = S["Contact"];
export type ContactAddress = S["ContactAddress"];
export type Recipient = S["Recipient"];

export type Conversation = S["Conversation"];
export type ConversationRef = S["ConversationRef"];
export type ConversationType = S["ConversationType"];
export type Group = S["Group"];
export type GroupParticipant = S["GroupParticipant"];
export type ConversationAction = S["ConversationAction"];

export type Message = S["Message"];
export type MessageStatus = S["MessageStatus"];
export type MessageDirection = S["MessageDirection"];
export type MessageNetwork = S["MessageNetwork"];
export type StartConversationRequest = S["StartConversationRequest"];
export type StartConversationTarget = S["StartConversationTarget"];
export type StartBasicMessage = S["StartBasicMessage"];
export type StartTemplateMessage = S["StartTemplateMessage"];
export type EditMessageRequest = S["EditMessageRequest"];
export type EditTelegramOptions = S["EditTelegramOptions"];
export type EditImessageOptions = S["EditImessageOptions"];
export type SmsSegments = S["SmsSegments"];

/** The kinds of message (a closed list): each sendable kind has its own endpoint and schema. */
export type MessageKind = S["MessageKind"];
/** A message's `content`: one kind object, in either direction, with `kind` saying which. */
export type MessageContent = S["MessageContent"];
/** One message to send where no URL names the kind: a webhook reply piece, a stream `send` frame's `message`, or `flow.messages.send`. */
export type OutboundKind = S["OutboundKind"];

export type BasicMessage = S["BasicMessage"];
export type Media = S["Media"];
export type ReplyTo = S["ReplyTo"];
export type TelegramParseMode = S["TelegramParseMode"];
export type BasicTelegramOptions = S["BasicTelegramOptions"];
export type BasicImessageOptions = S["BasicImessageOptions"];
export type ImessageStyle = S["ImessageStyle"];
export type VoiceMessage = S["VoiceMessage"];
export type ButtonsMessage = S["ButtonsMessage"];
export type ButtonsTelegramOptions = S["ButtonsTelegramOptions"];
export type ContentHeader = S["ContentHeader"];
export type Button = S["Button"];
export type ReplyButton = S["ReplyButton"];
export type UrlButton = S["UrlButton"];
export type ListMessage = S["ListMessage"];
export type ListSection = S["ListSection"];
export type ListRow = S["ListRow"];
export type CarouselMessage = S["CarouselMessage"];
export type CarouselCard = S["CarouselCard"];
export type TemplateMessage = S["TemplateMessage"];
export type TemplateParams = S["TemplateParams"];
export type TemplateCardParams = S["TemplateCardParams"];
export type TemplateHeaderParam = S["TemplateHeaderParam"];
export type TemplateButtonParam = S["TemplateButtonParam"];
export type ContactCardMessage = S["ContactCardMessage"];
export type LocationMessage = S["LocationMessage"];
export type EffectMessage = S["EffectMessage"];
export type ReactionMessage = S["ReactionMessage"];
export type ReactionTelegramOptions = S["ReactionTelegramOptions"];
export type TypingMessage = S["TypingMessage"];
export type TypingImessageOptions = S["TypingImessageOptions"];
export type ReadMessage = S["ReadMessage"];
export type EditMessage = S["EditMessage"];
export type UnsendMessage = S["UnsendMessage"];
export type ButtonReplyMessage = S["ButtonReplyMessage"];
export type FileBlockedMessage = S["FileBlockedMessage"];

export type BasicKind = S["BasicKind"];
export type VoiceKind = S["VoiceKind"];
export type ButtonsKind = S["ButtonsKind"];
export type ListKind = S["ListKind"];
export type CarouselKind = S["CarouselKind"];
export type TemplateKind = S["TemplateKind"];
export type ContactCardKind = S["ContactCardKind"];
export type LocationKind = S["LocationKind"];
export type EffectKind = S["EffectKind"];
export type ReactionKind = S["ReactionKind"];
export type TypingKind = S["TypingKind"];
export type ReadKind = S["ReadKind"];

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
export type CallReceivedEvent = S["CallReceivedEvent"];
export type Call = S["Call"];
/** The event whose `type` is `T`. */
export type EventOf<T extends EventType> = Extract<Event, { type: T }>;

export type StreamFrame = S["StreamFrame"];
export type StreamSendFrame = S["StreamSendFrame"];
export type StreamStartFrame = S["StreamStartFrame"];
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
export type TestGroupRequest = S["TestGroupRequest"];
export type TestGroupParticipant = S["TestGroupParticipant"];
export type SimulatedInboundRequest = S["SimulatedInboundRequest"];
export type SimulatedInboundContent = S["SimulatedInboundContent"];
export type SimulatedButtonTap = S["SimulatedButtonTap"];
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
