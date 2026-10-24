"""The smallest Flow Messaging agent: answers every message with what it said.

Run: FLOW_MESSAGING_KEY=fk_test_... python agent.py   (pip install flow-messaging)
"""

from flow_messaging import Flow, content_text

flow = Flow()  # reads FLOW_MESSAGING_KEY

# Where to join: each sandbox sender's link, and its join message (join_code) to send as is.
for s in flow.senders.list():
    if s.kind == "shared":
        where = s.address.link or s.address.handle or s.address.phone or s.id
        print(f"{s.channel}: {where}" + (f' (or send "{s.join_code}")' if s.join_code else ""), flush=True)

with flow.events.stream(types=["message.received"]) as events:  # connected from here on
    print("Echo agent ready. From your phone, open the sandbox link and tap Start, or send the join message.", flush=True)
    for event in events:
        content = event.data.message.content
        said = content_text(content) or f"a {content.kind}"
        print(f"[{event.conversation.channel}] {event.conversation.id}: {said}", flush=True)
        flow.conversation(event).send(f"You said: {said}")
