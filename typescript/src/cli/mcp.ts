// `flow-messaging mcp`: a stdio bridge to the hosted MCP server
// (https://api.flow.engineer/mcp, Streamable HTTP). It reads newline-delimited
// JSON-RPC from stdin, POSTs each message with the API key, and writes the answers
// (JSON or server-sent events) to stdout, one message per line. Logs go to stderr.
import { createInterface } from "node:readline";

export interface BridgeOptions {
  url: string;
  apiKey: string;
  input?: NodeJS.ReadableStream;
  write?: (line: string) => void;
  log?: (msg: string) => void;
  fetch?: typeof fetch;
  headers?: Record<string, string>;
}

/** Reads SSE `data:` payloads from a response body. */
export async function* sseMessages(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let data: string[] = [];
  for (;;) {
    const { done, value } = await reader.read();
    if (value) buf += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).replace(/\r$/, "");
      buf = buf.slice(nl + 1);
      if (line === "") {
        if (data.length) yield data.join("\n");
        data = [];
      } else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (done) {
      if (data.length) yield data.join("\n");
      return;
    }
  }
}

/** Runs the bridge until stdin ends. */
export async function runBridge(o: BridgeOptions): Promise<void> {
  const f = o.fetch ?? fetch;
  const write = o.write ?? ((line: string) => void process.stdout.write(line + "\n"));
  const log = o.log ?? ((m: string) => void process.stderr.write(`[flow-messaging mcp] ${m}\n`));
  let session: string | undefined;
  let protocol: string | undefined;
  const inflight = new Set<Promise<void>>();

  const forward = async (line: string) => {
    let msg: { id?: string | number; method?: string } | Array<unknown>;
    try {
      msg = JSON.parse(line);
    } catch {
      log(`ignored a line that is not JSON`);
      return;
    }
    const id = Array.isArray(msg) ? undefined : msg.id;
    const headers: Record<string, string> = {
      Authorization: `Bearer ${o.apiKey}`,
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      ...o.headers,
    };
    if (session) headers["Mcp-Session-Id"] = session;
    if (protocol) headers["MCP-Protocol-Version"] = protocol;
    try {
      const res = await f(o.url, { method: "POST", headers, body: line });
      const sid = res.headers.get("mcp-session-id");
      if (sid) session = sid;
      if (res.status === 202 || res.status === 204) return;
      const type = res.headers.get("content-type") ?? "";
      if (!res.ok && !type.includes("json") && !type.includes("event-stream")) {
        throw new Error(`${res.status} ${(await res.text()).slice(0, 200)}`);
      }
      const emit = (payload: string) => {
        try {
          const parsed = JSON.parse(payload) as { result?: { protocolVersion?: string } };
          if (parsed?.result?.protocolVersion) protocol = parsed.result.protocolVersion;
          write(JSON.stringify(parsed));
        } catch {
          log(`ignored a server message that is not JSON`);
        }
      };
      if (type.includes("text/event-stream") && res.body) {
        for await (const payload of sseMessages(res.body)) emit(payload);
      } else {
        const text = await res.text();
        if (text.trim()) emit(text);
      }
    } catch (err) {
      log(`request failed: ${(err as Error).message}`);
      if (id !== undefined) {
        write(JSON.stringify({ jsonrpc: "2.0", id, error: { code: -32000, message: `Flow Messaging MCP unreachable: ${(err as Error).message}` } }));
      }
    }
  };

  const rl = createInterface({ input: o.input ?? process.stdin, crlfDelay: Infinity });
  for await (const line of rl) {
    if (!line.trim()) continue;
    // Requests run concurrently; the server matches answers by id.
    const p = forward(line).finally(() => inflight.delete(p));
    inflight.add(p);
  }
  await Promise.all(inflight);
  if (session) {
    await f(o.url, { method: "DELETE", headers: { Authorization: `Bearer ${o.apiKey}`, "Mcp-Session-Id": session } }).catch(() => undefined);
  }
}
