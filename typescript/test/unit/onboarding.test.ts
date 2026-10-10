import { describe, expect, it } from "vitest";
import { AuthenticationError, DeviceSignInError, FlowMessaging, type DeviceAuthorization } from "../../src/index.js";
import { approvedToken, deviceAuthorization, json, mockFetch, sandboxKey } from "../helpers.js";

const pending = (interval = 5) => json(200, { status: "pending", interval });

/** A client whose key the keyless calls must not send (a claim token is given, or none applies). */
const client = (fetch: typeof globalThis.fetch) => new FlowMessaging({ fetch, apiKey: "fk_test_unit" });

describe("without a key", () => {
  // Reads FLOW_MESSAGING_KEY: the test clears it, so it cannot run in parallel with one that sets it.
  it("constructs, makes the keyless calls, and refuses the rest before sending anything", async () => {
    const old = process.env.FLOW_MESSAGING_KEY;
    delete process.env.FLOW_MESSAGING_KEY;
    try {
      const { fetch, calls } = mockFetch((req) => (req.url.pathname === "/v1/sandbox/keys" ? json(201, sandboxKey()) : undefined));
      const flow = new FlowMessaging({ fetch, baseURL: "https://example.test" });
      expect(flow.http.apiKey).toBeUndefined();
      const err = await flow.messages.send("conv_1", "hi").catch((e: unknown) => e);
      expect(err).toBeInstanceOf(AuthenticationError);
      expect((err as Error).message).toMatch(/v1\/sandbox\/keys/);
      expect(calls).toHaveLength(0);

      const sandbox = await flow.sandbox.createKey({ name: "Demo" });
      expect(sandbox.key).toBe("fk_test_unitsandbox");
      expect(sandbox.allowance.contacts.limit).toBe(1);
      expect(calls[0]!.method).toBe("POST");
      expect(calls[0]!.headers.authorization).toBeUndefined();
      expect(calls[0]!.headers["idempotency-key"]).toBeUndefined();
      expect(calls[0]!.body).toEqual({ name: "Demo" });
    } finally {
      if (old !== undefined) process.env.FLOW_MESSAGING_KEY = old;
    }
  });
});

describe("device sign-in", () => {
  it("claims with the claim token, or the test key as the bearer, or neither", async () => {
    const { fetch, calls } = mockFetch(() => json(201, deviceAuthorization()));
    const withKey = new FlowMessaging({ apiKey: "fk_test_unit", fetch });
    await withKey.device.authorize({ claimToken: "fct_unitclaim", clientName: "tests" });
    await withKey.device.authorize();
    await withKey.device.authorize({ useKey: false });
    await new FlowMessaging({ apiKey: "fk_live_unit", fetch }).device.authorize();
    expect(calls.map((c) => c.headers.authorization)).toEqual([undefined, "Bearer fk_test_unit", undefined, undefined]);
    expect(calls[0]!.body).toEqual({ claim_token: "fct_unitclaim", client_name: "tests" });
    expect(calls[0]!.url.pathname).toBe("/v1/device/authorizations");
  });

  it("polls every interval, slows down on 429 for at least retry_after, retries 5xx, and returns the key", async () => {
    let n = 0;
    const { fetch, calls } = mockFetch((req) => {
      if (req.url.pathname === "/v1/device/authorizations") return json(201, deviceAuthorization(5));
      n++;
      if (n === 1) return pending();
      if (n === 2) return json(429, { error: { type: "rate_limited", message: "slow down", retry_after: 7 } });
      if (n === 3) return json(503, { error: { type: "api_error", message: "busy" } });
      if (n === 4) return pending();
      return json(200, approvedToken());
    });
    const waits: number[] = [];
    const shown: DeviceAuthorization[] = [];
    const flow = client(fetch);
    const token = await flow.device.signIn({
      claimToken: "fct_unitclaim",
      prompt: (a) => void shown.push(a),
      wait: async (ms) => void waits.push(ms),
    });
    expect(token.key).toBe("fk_test_unitsignedin");
    expect(token.claimed).toBe(true);
    expect(shown.map((a) => a.user_code)).toEqual(["WDJB-MJHT"]);
    expect(waits).toEqual([5000, 5000, 10000, 10000, 10000]);
    const polls = calls.filter((c) => c.url.pathname === "/v1/device/token");
    expect(polls).toHaveLength(5);
    expect(polls.every((c) => c.headers.authorization === undefined && (c.body as { device_code: string }).device_code === "fdc_unitdevice")).toBe(true);
  });

  it("throws DeviceSignInError when the person refuses or the codes expire", async () => {
    for (const status of ["denied", "expired"] as const) {
      const { fetch } = mockFetch(() => json(200, { status, interval: 5 }));
      const err = await client(fetch)
        .device.waitForKey("fdc_unitdevice", { wait: async () => undefined })
        .catch((e: unknown) => e);
      expect(err).toBeInstanceOf(DeviceSignInError);
      expect((err as DeviceSignInError).reason).toBe(status);
    }
  });

  it("stops at the codes' expiry", async () => {
    const { fetch } = mockFetch(() => pending());
    const err = await client(fetch)
      .device.waitForKey("fdc_unitdevice", { expiresAt: "2000-01-01T00:00:00Z", wait: async () => undefined })
      .catch((e: unknown) => e);
    expect((err as DeviceSignInError).reason).toBe("expired");
  });
});
