// The API's resources, one class each, mirroring the endpoints in the spec.
import { toSendRequest, type SendInput } from "./conversation.js";
import type { HttpClient, Query, RequestOptions } from "./core.js";
import { PagePromise } from "./pagination.js";
import type {
  AppContext,
  Capabilities,
  Channel,
  Contact,
  Conversation,
  ConversationAction,
  Deleted,
  Event,
  File,
  ListContactsParams,
  ListConversationsParams,
  ListEventsParams,
  ListMessagesParams,
  ListSendersParams,
  ListTemplatesParams,
  ListWebhookEndpointsParams,
  Message,
  Sender,
  SenderRequest,
  StartConversationRequest,
  Template,
  TemplateCreateRequest,
  TextContent,
  WebhookEndpoint,
  WebhookEndpointCreateRequest,
  WebhookEndpointUpdateRequest,
  WebhookSecretRotateRequest,
} from "./types.js";

const enc = encodeURIComponent;

function list<T extends { id: string }>(http: HttpClient, path: string, params: Query = {}): PagePromise<T> {
  const { after, ...rest } = params;
  return new PagePromise<T>(
    (cursor) => http.request({ method: "GET", path, query: { ...rest, after: cursor } }),
    typeof after === "string" ? after : undefined,
  );
}

export class Messages {
  constructor(private readonly http: HttpClient) {}

  /**
   * Sends into a conversation (the normal reply): a string, a piece of content, or a
   * full request with `fallback`, `channel_options`, `metadata`. The answer is the
   * queued message; progress arrives as `message.sent` / `.delivered` / `.read` / `.failed`.
   *
   * ```ts
   * await flow.messages.send("conv_...", "Your order shipped.");
   * await flow.messages.send("conv_...", { content: buttons("Size?", ["S", "M", "L"]), fallback: "auto" });
   * ```
   */
  send(conversationId: string, input: SendInput, options?: RequestOptions): Promise<Message> {
    return this.http.request({
      method: "POST",
      path: `/v1/conversations/${enc(conversationId)}/messages`,
      body: toSendRequest(input),
      options,
    });
  }

  /**
   * Starts a conversation from one of your senders: `{ sender, to, content }`. Spends
   * the sender's new-contact budget; on WhatsApp outside the window only a template.
   * In test mode `to` must be a contact who joined the sandbox through your app.
   */
  start(params: StartConversationRequest, options?: RequestOptions): Promise<Message> {
    return this.http.request({ method: "POST", path: "/v1/messages", body: params, options });
  }

  /** One message, inbound or outbound, with its current status. */
  retrieve(messageId: string, options?: RequestOptions): Promise<Message> {
    return this.http.request({ method: "GET", path: `/v1/messages/${enc(messageId)}`, options });
  }

  /** Replaces the text of one of your sent messages (Telegram). */
  edit(messageId: string, content: string | TextContent, options?: RequestOptions): Promise<Message> {
    const c: TextContent = typeof content === "string" ? { type: "text", text: content } : content;
    return this.http.request({ method: "PATCH", path: `/v1/messages/${enc(messageId)}`, body: { content: c }, options });
  }

  /** Removes one of your sent messages from the contact's chat (Telegram, within 48 hours). */
  unsend(messageId: string, options?: RequestOptions): Promise<Message> {
    return this.http.request({ method: "DELETE", path: `/v1/messages/${enc(messageId)}`, options });
  }
}

export class Conversations {
  constructor(private readonly http: HttpClient) {}

  /** Your app's conversations in this mode, newest first. */
  list(params: ListConversationsParams = {}): PagePromise<Conversation> {
    return list(this.http, "/v1/conversations", params);
  }

  /** One conversation with its window state. */
  retrieve(conversationId: string, options?: RequestOptions): Promise<Conversation> {
    return this.http.request({ method: "GET", path: `/v1/conversations/${enc(conversationId)}`, options });
  }

  /** A conversation's messages, inbound and outbound, newest first. */
  messages(conversationId: string, params: ListMessagesParams = {}): PagePromise<Message> {
    return list(this.http, `/v1/conversations/${enc(conversationId)}/messages`, params);
  }

  /** Shows (`on`) or clears (`off`) the typing indicator. Channels clear it after a few seconds. */
  typing(conversationId: string, state: "on" | "off" = "on", options?: RequestOptions): Promise<ConversationAction> {
    return this.http.request({ method: "POST", path: `/v1/conversations/${enc(conversationId)}/typing`, body: { state }, options });
  }

  /** Marks the contact's messages as read, up to and including `upTo` (default: the latest inbound). */
  markRead(conversationId: string, upTo?: string, options?: RequestOptions): Promise<ConversationAction> {
    return this.http.request({
      method: "POST",
      path: `/v1/conversations/${enc(conversationId)}/read`,
      body: upTo ? { up_to: upTo } : {},
      options,
    });
  }
}

export class Capabilities_ {
  constructor(private readonly http: HttpClient) {}

  /** What the conversation's channel can show now, and whether its window is open. */
  retrieve(conversationId: string, options?: RequestOptions): Promise<Capabilities> {
    return this.http.request({ method: "GET", path: "/v1/capabilities", query: { conversation: conversationId }, options });
  }
}

export interface UploadParams {
  /** The bytes: a Blob/File, a Uint8Array or an ArrayBuffer. */
  file: Blob | Uint8Array | ArrayBuffer;
  /** The name to show; required unless `file` is a File with a name. */
  filename?: string;
  /** Check the file against this channel's size limit now. */
  channel?: Channel;
}

export class Files {
  constructor(private readonly http: HttpClient) {}

  /** Uploads media to send later as `media` or `voice` content by `file_id`. */
  upload(params: UploadParams, options?: RequestOptions): Promise<File> {
    const form = new FormData();
    const blob = params.file instanceof Blob ? params.file : new Blob([params.file as BlobPart]);
    const name = params.filename ?? (params.file as { name?: string }).name ?? "file";
    form.append("file", blob, name);
    if (params.filename) form.append("filename", params.filename);
    if (params.channel) form.append("channel", params.channel);
    return this.http.request({ method: "POST", path: "/v1/files", form, options });
  }

  /** Downloads a file's bytes (inbound media URLs point here). */
  async download(fileIdOrUrl: string, options?: RequestOptions): Promise<Blob> {
    const id = fileIdOrUrl.includes("/") ? fileIdOrUrl.split("/").pop()! : fileIdOrUrl;
    const res = await this.http.request<Response>({ method: "GET", path: `/v1/files/${enc(id)}`, options, raw: true });
    return res.blob();
  }
}

export class Senders {
  constructor(private readonly http: HttpClient) {}

  /** Senders your app can use in this mode. Test keys see the shared sandbox senders. */
  list(params: ListSendersParams = {}): PagePromise<Sender> {
    return list(this.http, "/v1/senders", params);
  }

  /** One sender with its status and limits. */
  retrieve(senderId: string, options?: RequestOptions): Promise<Sender> {
    return this.http.request({ method: "GET", path: `/v1/senders/${enc(senderId)}`, options });
  }

  /** Requests a dedicated sender (live keys). A Telegram bot connects at once with `telegram_bot_token`. */
  request(params: SenderRequest, options?: RequestOptions): Promise<Sender> {
    return this.http.request({ method: "POST", path: "/v1/senders", body: params, options });
  }
}

export class Templates {
  constructor(private readonly http: HttpClient) {}

  /** WhatsApp templates of your senders, newest first. */
  list(params: ListTemplatesParams = {}): PagePromise<Template> {
    return list(this.http, "/v1/templates", params);
  }

  /** Submits a WhatsApp template for review. */
  create(params: TemplateCreateRequest, options?: RequestOptions): Promise<Template> {
    return this.http.request({ method: "POST", path: "/v1/templates", body: params, options });
  }

  retrieve(templateId: string, options?: RequestOptions): Promise<Template> {
    return this.http.request({ method: "GET", path: `/v1/templates/${enc(templateId)}`, options });
  }

  delete(templateId: string, options?: RequestOptions): Promise<Deleted> {
    return this.http.request({ method: "DELETE", path: `/v1/templates/${enc(templateId)}`, options });
  }
}

export class WebhookEndpoints {
  constructor(private readonly http: HttpClient) {}

  list(params: ListWebhookEndpointsParams = {}): PagePromise<WebhookEndpoint> {
    return list(this.http, "/v1/webhook_endpoints", params);
  }

  /** Registers an HTTPS URL for the listed event types. The answer's `secret` (`whsec_...`) is shown only this once. */
  create(params: WebhookEndpointCreateRequest, options?: RequestOptions): Promise<WebhookEndpoint> {
    return this.http.request({ method: "POST", path: "/v1/webhook_endpoints", body: params, options });
  }

  retrieve(endpointId: string, options?: RequestOptions): Promise<WebhookEndpoint> {
    return this.http.request({ method: "GET", path: `/v1/webhook_endpoints/${enc(endpointId)}`, options });
  }

  update(endpointId: string, params: WebhookEndpointUpdateRequest, options?: RequestOptions): Promise<WebhookEndpoint> {
    return this.http.request({ method: "PATCH", path: `/v1/webhook_endpoints/${enc(endpointId)}`, body: params, options });
  }

  delete(endpointId: string, options?: RequestOptions): Promise<Deleted> {
    return this.http.request({ method: "DELETE", path: `/v1/webhook_endpoints/${enc(endpointId)}`, options });
  }

  /**
   * Makes a new signing secret; the answer's `secret` is shown only this once. The old
   * secret keeps signing for `overlap_seconds` (default one day, `0` retires it at
   * once), so deliveries verify with either secret while you deploy the new one.
   */
  rotateSecret(endpointId: string, params: WebhookSecretRotateRequest = {}, options?: RequestOptions): Promise<WebhookEndpoint> {
    return this.http.request({ method: "POST", path: `/v1/webhook_endpoints/${enc(endpointId)}/rotate_secret`, body: params, options });
  }
}

export class Contacts {
  constructor(private readonly http: HttpClient) {}

  list(params: ListContactsParams = {}): PagePromise<Contact> {
    return list(this.http, "/v1/contacts", params);
  }

  retrieve(contactId: string, options?: RequestOptions): Promise<Contact> {
    return this.http.request({ method: "GET", path: `/v1/contacts/${enc(contactId)}`, options });
  }
}

export class AppResource {
  constructor(private readonly http: HttpClient) {}

  /** The app, account and key making the request, its mode and the sandbox join code. */
  retrieve(options?: RequestOptions): Promise<AppContext> {
    return this.http.request({ method: "GET", path: "/v1/app", options });
  }
}

/** The event log, read by page (`list`) or live (`stream`, defined on the client). */
export class EventLog {
  constructor(protected readonly http: HttpClient) {}

  /** The log, oldest first. Pass the last event you processed as `after` to catch up. */
  list(params: ListEventsParams = {}): PagePromise<Event> {
    return list(this.http, "/v1/events", params);
  }

  retrieve(eventId: string, options?: RequestOptions): Promise<Event> {
    return this.http.request({ method: "GET", path: `/v1/events/${enc(eventId)}`, options });
  }
}
