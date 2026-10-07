# TypeScript SDK

Not written yet; this SDK comes first. It will be a typed client generated from
`../openapi/openapi.yaml`, plus hand-written parts: webhook verification, the typed
event union (a discriminated union on `type`), the event stream with resume, retries
and idempotency keys, splitting an LLM stream into message bubbles, and `flow listen`
for local development.
