// The API's resources, one class each, mirroring the endpoints in the spec.
import { toSendRequest, type SendInput } from "./conversation.js";
import { sleep, type HttpClient, type Query, type RequestOptions } from "./core.js";
import { APIConnectionError, APIError, APITimeoutError, DeviceSignInError, RateLimitError } from "./errors.js";
import { PagePromise } from "./pagination.js";
import type {
  AppContext,
  Capabilities,
  Channel,
  Contact,
  Conversation,
  ConversationAction,
  Deleted,
  DeviceAuthorization,
  DeviceToken,
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
  SandboxKey,
  SandboxKeyRequest,
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
   * await flow.messages.send("conv_...", { content: text("Yes, that one."), reply_to: "msg_..." }); // an inline reply
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
  /** The bytes: a Blob/File, a Uint8Array (a Node `Buffer` is one) or an ArrayBuffer. Read a stream into one of these first. */
  file: Blob | Uint8Array | ArrayBuffer;
  /** The name to show; required unless `file` is a File with a name. */
  filename?: string;
  /** Check the file against this channel's size limit now. */
  channel?: Channel;
}

export class Files {
  constructor(private readonly http: HttpClient) {}

  /**
   * Uploads media to send later as `media` or `voice` content by `file_id`. The answer
   * is the stored `File`; its `id` (`file_...`) is the `file_id`.
   *
   * ```ts
   * const file = await flow.files.upload({ file: await readFile("receipt.pdf"), filename: "receipt.pdf" });
   * await flow.messages.send("conv_...", document(file.id, { caption: "Your receipt" }));
   * ```
   */
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

  /** Disconnects one of your Telegram bots (live keys): removes its webhook and token and retires the sender (status `banned`). */
  disconnect(senderId: string, options?: RequestOptions): Promise<Sender> {
    return this.http.request({ method: "DELETE", path: `/v1/senders/${enc(senderId)}`, options });
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

  /**
   * The app, account and key making the request, its mode, the sandbox join code and,
   * for sandbox apps, what is left of the sandbox `allowance`.
   */
  retrieve(options?: RequestOptions): Promise<AppContext> {
    return this.http.request({ method: "GET", path: "/v1/app", options });
  }
}

/** Test keys without an account. Needs no API key. */
export class Sandbox {
  constructor(private readonly http: HttpClient) {}

  /**
   * Makes a new app with a `fk_test_` key, without an account or an API key: the first
   * call for an agent that has no key. The answer's `key` and `claim_token` are shown
   * only this once: save them (as `FLOW_MESSAGING_KEY` and `FLOW_CLAIM_TOKEN`). Its
   * `senders` carry the links and join code a person uses to join the sandbox.
   *
   * The app has a sandbox allowance (1 contact, 50 messages, on the Telegram and
   * WhatsApp sandboxes) and its keys expire after 7 days; a person signs in with
   * `device.signIn({ claimToken })` to keep it. Do not call this when you already have
   * a key. Limited per client address (429 `rate_limited`).
   *
   * ```ts
   * const sandbox = await new FlowMessaging().sandbox.createKey();
   * const flow = new FlowMessaging({ apiKey: sandbox.key });
   * ```
   */
  createKey(params: SandboxKeyRequest = {}, options?: RequestOptions): Promise<SandboxKey> {
    return this.http.request({ method: "POST", path: "/v1/sandbox/keys", body: params, options, auth: false });
  }
}

export interface DeviceAuthorizeParams {
  /** The `claim_token` from `sandbox.createKey`, to claim that app when the person approves. */
  claimToken?: string;
  /** What is asking, shown on the approval page ("flow CLI", "Claude Code"). */
  clientName?: string;
  /** `false` never sends this client's key, even without `claimToken` (default `true`). */
  useKey?: boolean;
}

export interface DeviceWaitOptions {
  /** Seconds between polls, from the authorization (default 5). */
  interval?: number;
  /** When the codes expire, from the authorization; polling stops then. */
  expiresAt?: string;
  signal?: AbortSignal;
  /** Waits between polls (default: a timer). Tests pass their own. */
  wait?: (ms: number, signal?: AbortSignal) => Promise<void>;
}

export interface DeviceSignInParams extends DeviceAuthorizeParams, Omit<DeviceWaitOptions, "interval" | "expiresAt"> {
  /**
   * Shows the person `verification_uri_complete` (or `verification_uri` and
   * `user_code`); called once, before the first poll. Never show `device_code`.
   */
  prompt: (authorization: DeviceAuthorization) => void | Promise<void>;
}

/** Transient poll failures in a row before `waitForKey` gives up. */
const MAX_POLL_FAILURES = 5;

/**
 * Sign-in from an agent or CLI (the device flow): a person approves in a browser with
 * GitHub or Google, and the agent receives a key. Needs no API key.
 */
export class Device {
  constructor(private readonly http: HttpClient) {}

  /**
   * Starts a sign-in. With `claimToken` (or, without one, when this client holds a
   * `fk_test_` key, sent as the bearer) the person's approval claims that sandbox app:
   * its data and keys are kept, its keys stop expiring, its allowance becomes 3
   * contacts and 100 messages each.
   */
  authorize(params: DeviceAuthorizeParams = {}, options?: RequestOptions): Promise<DeviceAuthorization> {
    const body: Record<string, string> = {};
    if (params.claimToken) body.claim_token = params.claimToken;
    if (params.clientName) body.client_name = params.clientName;
    const bearer = !params.claimToken && params.useKey !== false && this.http.testMode;
    return this.http.request({ method: "POST", path: "/v1/device/authorizations", body, options, auth: bearer });
  }

  /** One poll of a sign-in: `pending`, `approved` (with `key`), `denied` or `expired`. */
  poll(deviceCode: string, options?: RequestOptions): Promise<DeviceToken> {
    return this.http.request({ method: "POST", path: "/v1/device/token", body: { device_code: deviceCode }, options, auth: false });
  }

  /**
   * Polls a started sign-in until the person approves, every `interval` seconds; a 429
   * (`rate_limited`) slows it down by 5 seconds and waits at least its `retry_after`.
   * Resolves with the approved `DeviceToken` (its `key` is shown once); throws a
   * `DeviceSignInError` when the person refuses or the codes expire.
   */
  async waitForKey(deviceCode: string, o: DeviceWaitOptions = {}): Promise<DeviceToken> {
    const wait = o.wait ?? sleep;
    const deadline = o.expiresAt ? Date.parse(o.expiresAt) : NaN;
    let interval = Math.max(1, o.interval ?? 5) * 1000;
    let next = interval;
    let failures = 0;
    for (;;) {
      await wait(next, o.signal);
      next = interval;
      let t: DeviceToken;
      try {
        t = await this.poll(deviceCode, { maxRetries: 0, signal: o.signal });
      } catch (e) {
        if (e instanceof RateLimitError) {
          interval += 5000;
          next = Math.max(interval, (e.retryAfter ?? 0) * 1000);
          continue;
        }
        const transient = e instanceof APIConnectionError || e instanceof APITimeoutError || e instanceof APIError;
        if (!transient || ++failures >= MAX_POLL_FAILURES) throw e;
        continue;
      }
      failures = 0;
      switch (t.status) {
        case "approved":
          return t;
        case "denied":
          throw new DeviceSignInError("denied");
        case "expired":
          throw new DeviceSignInError("expired");
      }
      interval = Math.max(interval, t.interval * 1000);
      next = interval;
      if (Date.now() >= deadline) throw new DeviceSignInError("expired");
    }
  }

  /**
   * Runs the whole sign-in: starts it, calls `prompt` with the link and code, and polls
   * until the person approves. Store the answer's `key` in place of the sandbox key.
   *
   * ```ts
   * const flow = new FlowMessaging({ apiKey: process.env.FLOW_MESSAGING_KEY });
   * const token = await flow.device.signIn({
   *   claimToken: process.env.FLOW_CLAIM_TOKEN,
   *   prompt: (a) => console.log(`Open ${a.verification_uri_complete} and check the code ${a.user_code}`),
   * });
   * // save token.key as FLOW_MESSAGING_KEY; FLOW_CLAIM_TOKEN is used up
   * ```
   */
  async signIn(params: DeviceSignInParams): Promise<DeviceToken> {
    const auth = await this.authorize(
      { claimToken: params.claimToken, clientName: params.clientName, useKey: params.useKey },
      { signal: params.signal },
    );
    await params.prompt(auth);
    return this.waitForKey(auth.device_code, {
      interval: auth.interval,
      expiresAt: auth.expires_at,
      signal: params.signal,
      wait: params.wait,
    });
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
