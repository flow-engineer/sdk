#!/usr/bin/env python3
"""Runs each example in examples/ against a local Flow Messaging service and checks
what it does, playing the Telegram user through the Telegram simulator's /_sim/ API.

scripts/check-examples.sh --e2e starts the service and calls this; it is not meant
to be run by hand. Standard library only. Keys are never printed.

Environment (set by check-examples.sh):
  E2E_API              the service's base URL
  E2E_SIM              the Telegram simulator's base URL
  E2E_SIM_TOKEN        the simulator's admin token
  E2E_SANDBOX_TOKEN    the sandbox bot's token in the simulator
  E2E_LIVE_KEY_FILE    a file holding a fk_live_ key of a local tenant
  E2E_TS_DIR           a folder with node_modules and each TypeScript example as <name>.ts
  E2E_PYTHON           a Python with the Python examples' requirements installed
  E2E_EXAMPLES         the examples/ folder
Arguments: scenario names to run (default: all).
"""

import hashlib
import hmac
import json
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

API = os.environ["E2E_API"]
SIM = os.environ["E2E_SIM"]
SIM_AUTH = {"Authorization": "Bearer " + os.environ["E2E_SIM_TOKEN"]}
SANDBOX_TOKEN = os.environ["E2E_SANDBOX_TOKEN"]
TS_DIR = os.environ["E2E_TS_DIR"]
PYTHON = os.environ["E2E_PYTHON"]
EXAMPLES = os.environ["E2E_EXAMPLES"]
WAIT = 20  # seconds any one expectation may take


class Failed(Exception):
    pass


def http(method, url, body=None, headers=None, raw=None):
    """One HTTP call; returns (status, parsed JSON or None)."""
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=WAIT + 10) as res:
            text = res.read()
            return res.status, json.loads(text) if text.strip() else None
    except urllib.error.HTTPError as e:
        text = e.read()
        try:
            return e.code, json.loads(text) if text.strip() else None
        except ValueError:
            return e.code, None


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


STARTED = []  # every Proc of the running scenario, to show their output when it fails


class Proc:
    """An example running in the background; its output is read line by line."""

    def __init__(self, name, cmd, env, cwd):
        self.name, self.lines, self.q = name, [], queue.Queue()
        STARTED.append(self)
        full_env = {k: v for k, v in os.environ.items() if not k.startswith("E2E_")}
        full_env.update({"FLOW_MESSAGING_BASE_URL": API, "PYTHONUNBUFFERED": "1"}, **env)
        self.p = subprocess.Popen(cmd, cwd=cwd, env=full_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.p.stdout:
            line = line.rstrip("\n")
            self.lines.append(line)
            self.q.put(line)
        self.q.put(None)

    def expect(self, pattern, timeout=WAIT):
        """Waits for an output line matching the regex pattern; returns the match."""
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            try:
                line = self.q.get(timeout=max(left, 0.01))
            except queue.Empty:
                line = ""
            if line is None:
                raise Failed(f"{self.name} exited (code {self.p.wait()}) before printing /{pattern}/")
            m = re.search(pattern, line)
            if m:
                return m
            if left <= 0:
                raise Failed(f"{self.name} did not print /{pattern}/ within {timeout}s")

    def wait_exit(self, timeout=WAIT):
        code = self.p.wait(timeout=timeout)
        time.sleep(0.05)  # let the reader thread drain the last lines
        return code

    def stop(self):
        if self.p.poll() is None:
            self.p.terminate()
            try:
                self.p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.p.kill()


def ts(name, *args, env):
    return Proc(f"{name} (TypeScript)", ["node", f"{name}.ts", *args], env, TS_DIR)


def py(name, *args, env):
    return Proc(f"{name} (Python)", [PYTHON, os.path.join(EXAMPLES, name, "python", "main.py"), *args], env, os.path.join(EXAMPLES, name, "python"))


# ---------------------------------------------------------------- the Telegram user

class User:
    """A Telegram user writing to a bot, through the simulator."""

    next_id = 9001

    def __init__(self, bot_token=SANDBOX_TOKEN):
        self.id, self.bot, self.mid = User.next_id, bot_token, 0
        User.next_id += 1

    def _deliver(self, update):
        status, body = http("POST", SIM + "/_sim/deliver", {"token": self.bot, "update": {"update_id": 0, **update}}, SIM_AUTH)
        if status != 200 or body.get("status") != 200:
            raise Failed(f"the service refused a Telegram update: {status} {body}")

    def say(self, text):
        self.mid += 1
        self._deliver({"message": {"message_id": self.mid, "from": {"id": self.id, "is_bot": False, "first_name": "Asha"},
                                   "chat": {"id": self.id, "type": "private"}, "date": int(time.time()), "text": text}})

    def tap(self, bot_message_id, data):
        self._deliver({"callback_query": {"id": f"cbq{self.id}{bot_message_id}", "from": {"id": self.id, "is_bot": False, "first_name": "Asha"},
                                          "data": data, "message": {"message_id": bot_message_id, "chat": {"id": self.id, "type": "private"},
                                                                    "date": int(time.time()), "text": "buttons"}}})

    def seq(self):
        """The simulator's latest call number, to wait only for calls after it."""
        _, body = http("GET", SIM + "/_sim/calls", headers=SIM_AUTH)
        return max([c["seq"] for c in body["calls"]], default=0)

    def receive(self, after):
        """Waits for the next message the bot sends this user after call number `after`."""
        q = f"token={urllib.request.quote(self.bot)}&method=sendMessage&chat_id={self.id}&after={after}&min=1&wait_ms={WAIT * 1000}"
        _, body = http("GET", SIM + "/_sim/calls?" + q, headers=SIM_AUTH)
        if not body["calls"]:
            raise Failed(f"the bot sent user {self.id} nothing within {WAIT}s")
        return body["calls"][0]


def sandbox_key():
    """A new sandbox app, as `curl -X POST .../v1/sandbox/keys` makes it."""
    status, body = http("POST", API + "/v1/sandbox/keys")
    if status != 201:
        raise Failed(f"POST /v1/sandbox/keys answered {status}: {body}")
    return body


def join(user, sk):
    """The user taps the sandbox link (/start <code>), which joins them to the app."""
    user.say("/start " + sk["app"]["sandbox_join_code"])


def check(cond, what):
    if not cond:
        raise Failed(what)


# ---------------------------------------------------------------- scenarios

def echo(run):
    sk = sandbox_key()
    p = run("telegram-echo", env={"FLOW_MESSAGING_KEY": sk["key"]})
    try:
        p.expect(r'^Write to https://t\.me/\w+\?start=[\w-]+ \(or send "join [\w-]+"\)$')
        p.expect(r"^Echo agent ready\.$")
        u = User()
        join(u, sk)
        after = u.seq()
        u.say("hello from the e2e test")
        call = u.receive(after)
        check(call["params"]["text"] == "You said: hello from the e2e test", f"echo sent {call['params']['text']!r}")
        p.expect(r"^\[conv_\w+\] hello from the e2e test$")
        p.expect(r"^  -> sent msg_\w+$")
    finally:
        p.stop()
    return p


class StubLLM(ThreadingHTTPServer):
    """A stand-in for the Anthropic Messages API (ANTHROPIC_BASE_URL), so the agent's real
    SDK call runs without a key. It answers "Stub answer <n>" and keeps every request."""

    def __init__(self):
        self.requests = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                stub.requests.append(body)
                n = sum(1 for m in body["messages"] if m["role"] == "user")
                answer = json.dumps({"id": f"msg_stub{n}", "type": "message", "role": "assistant", "model": body["model"],
                                     "content": [{"type": "text", "text": f"Stub answer {n}"}], "stop_reason": "end_turn",
                                     "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}).encode()
                self.send_response(200 if self.path.startswith("/v1/messages") else 404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(answer)))
                self.end_headers()
                self.wfile.write(answer)

            def log_message(self, *args):
                pass

        super().__init__(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.serve_forever, daemon=True).start()


def ai_agent(run, fake_llm):
    sk = sandbox_key()
    stub = None
    if fake_llm:
        p = run("telegram-ai-agent", "--fake-llm", env={"FLOW_MESSAGING_KEY": sk["key"], "ANTHROPIC_API_KEY": ""})
        first, second = '(fake LLM) Answer 1: you said "Where is my order?"', "(fake LLM) Answer 2:"
    else:
        stub = StubLLM()
        p = run("telegram-ai-agent", env={"FLOW_MESSAGING_KEY": sk["key"], "ANTHROPIC_API_KEY": "stub-not-a-key",
                                          "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{stub.server_address[1]}"})
        first, second = "Stub answer 1", "Stub answer 2"
    try:
        p.expect(r"^Support agent ready( \(fake LLM\))?\. Write to your sandbox bot\.$")
        u = User()
        join(u, sk)
        after = u.seq()
        u.say("Where is my order?")
        call = u.receive(after)
        check(call["params"]["text"] == first, f"agent sent {call['params']['text']!r}")
        keyboard = call["params"].get("reply_markup", {}).get("inline_keyboard")
        check(keyboard == [[{"callback_data": "talk_to_human", "text": "Talk to a human"}]], f"agent's buttons: {keyboard}")
        p.expect(r"^\[conv_\w+\] customer: Where is my order\?$")
        p.expect(r"^\[conv_\w+\] agent: " + re.escape(first))

        after = u.seq()
        u.say("It is order 1042")  # the history is kept per conversation: this is answer 2
        call = u.receive(after)
        check(call["params"]["text"].startswith(second), f"agent sent {call['params']['text']!r}")
        if stub:
            last = stub.requests[-1]
            check(last["model"] == "claude-sonnet-5-5", f"the agent asked model {last['model']!r}")
            check("support agent" in json.dumps(last.get("system")), "the agent sent no system prompt")
            turns = [(m["role"], m["content"]) for m in last["messages"]]
            want = [("user", "Where is my order?"), ("assistant", "Stub answer 1"), ("user", "It is order 1042")]
            check(turns == want, f"the agent sent the LLM {turns}")

        after = u.seq()
        u.tap(call["message_id"], "talk_to_human")
        call = u.receive(after)
        check(call["params"]["text"] == "Thanks. A person from our team will answer here soon.", f"agent sent {call['params']['text']!r}")
        p.expect(r"^\[conv_\w+\] handed to a human$")
        u.say("Hello?")
        p.expect(r"^\[conv_\w+\] \(with a human\) Hello\?$")
    finally:
        p.stop()
        if stub:
            stub.shutdown()
    return p


def sign(secret, body, t=None):
    t = str(int(time.time()) if t is None else t)
    return f"t={t},v1=" + hmac.new(secret.encode(), b"t." + t.encode() + b"." + body, hashlib.sha256).hexdigest()


def webhook_receiver(run):
    sk = sandbox_key()
    port = free_port()
    url = f"http://127.0.0.1:{port}/flow/webhook"
    status, ep = http("POST", API + "/v1/webhook_endpoints", {"url": url, "events": ["message.received", "message.failed"]},
                      {"Authorization": "Bearer " + sk["key"], "Idempotency-Key": f"e2e-endpoint-{port}"})
    check(status == 201, f"POST /v1/webhook_endpoints answered {status}: {ep}")
    secret = ep["secret"]
    p = run("webhook-receiver", env={"FLOW_MESSAGING_WEBHOOK_SECRET": secret, "PORT": str(port)})
    try:
        p.expect(rf"Listening on http://localhost:{port}/flow/webhook$|Uvicorn running on http://0\.0\.0\.0:{port} ")
        u = User()
        join(u, sk)
        after = u.seq()
        u.say("hi webhook")
        call = u.receive(after)  # the reply in the webhook answer
        check(call["params"]["text"] == "You said: hi webhook", f"receiver replied {call['params']['text']!r}")
        p.expect(r"^evt_\w+ \[conv_\w+\] hi webhook$")

        body = json.dumps({"id": "evt_e2eduplicate", "type": "message.received", "conversation": {"id": "conv_e2e"},
                           "data": {"message": {"id": "msg_e2e", "content": {"type": "text", "text": "twice"}}}}).encode()
        for sig, want in [("t=1,v1=" + "0" * 64, 400), (sign(secret, body, time.time() - 600), 400), (sign("whsec_wrong", body), 400)]:
            status, _ = http("POST", url, raw=body, headers={"Flow-Signature": sig})
            check(status == want, f"a bad signature got {status}, want {want}")
            p.expect(r"^rejected: bad Flow-Signature$")
        status, answer = http("POST", url, raw=body, headers={"Flow-Signature": sign(secret, body)})
        check(status == 200 and answer == {"reply": {"type": "text", "text": "You said: twice"}}, f"first delivery: {status} {answer}")
        # While a secret rotation overlaps, the header carries two v1 values; one matching is enough.
        status, answer = http("POST", url, raw=body, headers={"Flow-Signature": sign(secret, body) + ",v1=" + "0" * 64})
        check(status == 200 and answer == {}, f"repeated delivery: {status} {answer}")
        p.expect(r"^duplicate evt_e2eduplicate: skipped$")
    finally:
        p.stop()
    return p


def own_telegram_bot(run):
    with open(os.environ["E2E_LIVE_KEY_FILE"]) as f:
        live_key = f.read().strip()
    status, bot = http("POST", SIM + "/_sim/bots", {"username": "e2e_own_bot"}, SIM_AUTH)
    check(status in (200, 201), f"the simulator made no bot: {status}")

    # A test key cannot connect a bot: the API says so, with a hint.
    p = run("own-telegram-bot", "connect", env={"FLOW_MESSAGING_KEY": sandbox_key()["key"], "TELEGRAM_BOT_TOKEN": bot["token"]})
    check(p.wait_exit() == 1, "connect with a test key did not fail")
    check(any(l.startswith("permission: ") for l in p.lines) and any(l.startswith("hint: ") for l in p.lines), f"output: {p.lines}")

    p = run("own-telegram-bot", "connect", env={"FLOW_MESSAGING_KEY": live_key, "TELEGRAM_BOT_TOKEN": bot["token"]})
    sender = p.expect(r"^Connected @e2e_own_bot as (snd_\w+) \(status active\)\.$").group(1)
    p.expect(r"^Chat with it: https://t\.me/e2e_own_bot$")
    check(p.wait_exit() == 0, "connect failed")

    # Live now: the echo example answers on the bot, unchanged, with the live key.
    echo_p = ts("telegram-echo", env={"FLOW_MESSAGING_KEY": live_key})
    try:
        echo_p.expect(r"^Write to https://t\.me/e2e_own_bot$")
        echo_p.expect(r"^Echo agent ready\.$")
        u = User(bot["token"])
        after = u.seq()
        u.say("hi own bot")
        call = u.receive(after)
        check(call["params"]["text"] == "You said: hi own bot", f"own bot sent {call['params']['text']!r}")
    finally:
        echo_p.stop()

    for _ in range(2):  # disconnecting again is safe
        p = run("own-telegram-bot", "disconnect", sender, env={"FLOW_MESSAGING_KEY": live_key})
        p.expect(rf"^Disconnected {sender} \(status banned\)\.$")
        check(p.wait_exit() == 0, "disconnect failed")
    return p


SCENARIOS = {
    "telegram-echo/typescript": lambda: echo(ts),
    "telegram-echo/python": lambda: echo(py),
    "telegram-ai-agent/typescript": lambda: ai_agent(ts, fake_llm=False),
    "telegram-ai-agent/python": lambda: ai_agent(py, fake_llm=False),
    "telegram-ai-agent/typescript --fake-llm": lambda: ai_agent(ts, fake_llm=True),
    "telegram-ai-agent/python --fake-llm": lambda: ai_agent(py, fake_llm=True),
    "webhook-receiver/typescript": lambda: webhook_receiver(ts),
    "webhook-receiver/python": lambda: webhook_receiver(py),
    "own-telegram-bot/typescript": lambda: own_telegram_bot(ts),
}


def main():
    names = sys.argv[1:] or list(SCENARIOS)
    failed = []
    for name in names:
        started = time.monotonic()
        STARTED.clear()
        try:
            SCENARIOS[name]()
            print(f"PASS  {name} ({time.monotonic() - started:.1f}s)", flush=True)
        except Exception as e:  # report every scenario, then fail
            failed.append(name)
            print(f"FAIL  {name}: {e}", flush=True)
            for p in STARTED:
                p.stop()
                print(f"      output of {p.name}:", *("      | " + l for l in p.lines[-30:]), sep="\n", flush=True)
    if failed:
        sys.exit(f"{len(failed)} example(s) failed: {', '.join(failed)}")
    print(f"All {len(names)} examples passed.")


if __name__ == "__main__":
    main()
