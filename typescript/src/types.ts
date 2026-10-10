// Friendly names for the types generated from the OpenAPI spec
// (src/generated/openapi.ts, made by `npm run generate`; never edit that file).
import type { components, operations } from "./generated/openapi.js";

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

export type Sender = S["Sender"];
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

/** Query parameters of list endpoints, by operation. */
export type ListConversationsParams = NonNullable<operations["listConversations"]["parameters"]["query"]>;
export type ListMessagesParams = NonNullable<operations["listConversationMessages"]["parameters"]["query"]>;
export type ListEventsParams = NonNullable<operations["listEvents"]["parameters"]["query"]>;
export type ListSendersParams = NonNullable<operations["listSenders"]["parameters"]["query"]>;
export type ListTemplatesParams = NonNullable<operations["listTemplates"]["parameters"]["query"]>;
export type ListWebhookEndpointsParams = NonNullable<operations["listWebhookEndpoints"]["parameters"]["query"]>;
export type ListContactsParams = NonNullable<operations["listContacts"]["parameters"]["query"]>;
