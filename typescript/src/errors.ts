import type { ErrorBody, ErrorType } from "./types.js";

/**
 * Every error the API returns is a `FlowError` subclass chosen by `error.type`
 * (a closed list). Switch on the class or on `type`, never on `message`.
 *
 * ```ts
 * try { await flow.messages.send(convId, "hi") }
 * catch (err) {
 *   if (err instanceof OutsideWindowError) await flow.messages.send(convId, template(...))
 *   else throw err
 * }
 * ```
 */
export class FlowError extends Error {
  override name = "FlowError";
  /** The API's error type, or `connection_error` / `timeout` / `signature_verification` for errors raised in the SDK. */
  readonly type: ErrorType | "connection_error" | "timeout" | "signature_verification";
  /** The HTTP status, when the error came from an answer. */
  readonly status: number | undefined;
  /** The request parameter the error is about (`content.buttons`, `limit`). */
  readonly param: string | undefined;
  /** Seconds to wait before retrying, for errors that clear by themselves. */
  readonly retryAfter: number | undefined;
  /** The conversation the error is about (`outside_window`). */
  readonly conversation: string | undefined;
  /** The sender the error is about (`new_contact_limit`, `sender_throttled`). */
  readonly sender: string | undefined;
  /** For `channel_error`, the channel's own error code. */
  readonly channelCode: string | undefined;
  /** Flow's ID for the request. Quote it when asking for help. */
  readonly requestId: string | undefined;
  /** The page for this error type, `https://api.flow.engineer/docs/errors/<type>`, when the API gives one. */
  readonly docUrl: string | undefined;
  /** A short hint on what to do next, when the API gives one. */
  readonly hint: string | undefined;
  /** The error body as the API sent it. */
  readonly body: ErrorBody | undefined;
  /** The answer's headers, when there was an answer. */
  readonly headers: Headers | undefined;

  constructor(
    message: string,
    init: {
      type: FlowError["type"];
      status?: number;
      body?: ErrorBody;
      headers?: Headers;
      cause?: unknown;
    },
  ) {
    super(message, init.cause === undefined ? undefined : { cause: init.cause });
    const b = (init.body ?? {}) as ErrorBody & { doc_url?: string; hint?: string };
    this.type = init.type;
    this.status = init.status;
    this.body = init.body;
    this.headers = init.headers;
    this.param = b.param;
    this.conversation = b.conversation;
    this.sender = b.sender;
    this.channelCode = b.channel_code;
    this.requestId = b.request_id ?? init.headers?.get("flow-request-id") ?? undefined;
    this.docUrl = b.doc_url;
    this.hint = b.hint;
    const header = init.headers?.get("retry-after");
    this.retryAfter = b.retry_after ?? (header && /^\d+$/.test(header) ? Number(header) : undefined);
  }
}

/** 400 `invalid_request`: the request is malformed or a parameter is invalid; see `param`. */
export class InvalidRequestError extends FlowError {
  override name = "InvalidRequestError";
}
/** 401 `authentication`: the API key is missing, unknown or revoked. */
export class AuthenticationError extends FlowError {
  override name = "AuthenticationError";
}
/** 403 `permission`: the key may not do this (for example a test key using a live sender). */
export class PermissionError extends FlowError {
  override name = "PermissionError";
}
/** 404 `not_found`: no such object for this app and mode. */
export class NotFoundError extends FlowError {
  override name = "NotFoundError";
}
/** 409 `idempotency_conflict`: the idempotency key was used for a different request, or that request is still running. */
export class IdempotencyConflictError extends FlowError {
  override name = "IdempotencyConflictError";
}
/** 409 `outside_window`: WhatsApp's 24-hour window is closed; send a `template`. */
export class OutsideWindowError extends FlowError {
  override name = "OutsideWindowError";
}
/** 422 `unsupported_content`: the channel cannot show this content; set `fallback: "auto"` or send something else. */
export class UnsupportedContentError extends FlowError {
  override name = "UnsupportedContentError";
}
/** 429 `new_contact_limit`: the sender used its budget for starting conversations; see `retryAfter`. */
export class NewContactLimitError extends FlowError {
  override name = "NewContactLimitError";
}
/** 429 `sender_throttled`: abuse signals tripped; starts are paused until `retryAfter`, replies still go. */
export class SenderThrottledError extends FlowError {
  override name = "SenderThrottledError";
}
/** 422 `file_blocked`: the file failed the malware scan and was not stored. */
export class FileBlockedError extends FlowError {
  override name = "FileBlockedError";
}
/** 429 `rate_limited`: too many requests for this key; see `retryAfter`. Retried automatically. */
export class RateLimitError extends FlowError {
  override name = "RateLimitError";
}
/** 502 `channel_error`: the channel refused or failed the message; see `channelCode`. */
export class ChannelError extends FlowError {
  override name = "ChannelError";
}
/** 501 `not_implemented`: this endpoint is not live yet during the beta. */
export class NotImplementedError extends FlowError {
  override name = "NotImplementedError";
}
/** 500/503 `api_error`: something went wrong on Flow's side. Retried automatically with the same idempotency key. */
export class APIError extends FlowError {
  override name = "APIError";
}
/** The request never got an answer (network failure). Retried automatically. */
export class APIConnectionError extends FlowError {
  override name = "APIConnectionError";
}
/** The request took longer than `timeout`. Retried automatically. */
export class APITimeoutError extends FlowError {
  override name = "APITimeoutError";
}
/** A webhook's `Flow-Signature` did not match, or its timestamp is outside the tolerance. Answer 400. */
export class WebhookSignatureError extends FlowError {
  override name = "WebhookSignatureError";
}

const byType: Record<ErrorType, typeof FlowError> = {
  invalid_request: InvalidRequestError,
  authentication: AuthenticationError,
  permission: PermissionError,
  not_found: NotFoundError,
  idempotency_conflict: IdempotencyConflictError,
  outside_window: OutsideWindowError,
  unsupported_content: UnsupportedContentError,
  new_contact_limit: NewContactLimitError,
  sender_throttled: SenderThrottledError,
  file_blocked: FileBlockedError,
  rate_limited: RateLimitError,
  channel_error: ChannelError,
  not_implemented: NotImplementedError,
  api_error: APIError,
};

/** Builds the typed error for an API error body. Unknown types become `FlowError`. */
export function errorFromBody(status: number, body: ErrorBody | undefined, headers?: Headers): FlowError {
  const type = (body?.type ?? (status >= 500 ? "api_error" : "invalid_request")) as ErrorType;
  const Cls = byType[type] ?? FlowError;
  const message = body?.message ?? `Flow Messaging answered ${status} with no error body.`;
  return new Cls(message, { type, status, body, headers });
}
