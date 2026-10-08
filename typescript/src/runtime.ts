// What the JavaScript runtime can do, in one place so tests can stand in for another one.

/**
 * Whether this runtime's WebSocket can send headers (Node, Bun, Deno). Browsers and
 * edge runtimes cannot set `Authorization` on a WebSocket.
 */
export function canSendWebSocketHeaders(): boolean {
  const g = globalThis as { process?: { versions?: { node?: string; bun?: string } }; Deno?: unknown; Bun?: unknown };
  return Boolean(g.process?.versions?.node || g.Bun || g.Deno);
}
