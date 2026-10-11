"""The smallest Flow Messaging agent: answers every message with what it said.

Run: FLOW_MESSAGING_KEY=fk_test_... python agent.py   (pip install flow-messaging)
"""

from flow_messaging import Flow, content_text

flow = Flow()  # reads FLOW_MESSAGING_KEY

app = flow.app.retrieve().app

with flow.events.stream(types=["message.received"]) as events:  # connected from here on
    print(
        "Echo agent ready. From your phone, open the sandbox link and tap Start "
        f"(on iMessage, text: join {app.sandbox_join_code}).",
        flush=True,
    )
    for event in events:
        content = event.data.message.content
        said = content_text(content) or f"a {content.type}"
        print(f"[{event.conversation.channel}] {event.conversation.id}: {said}", flush=True)
        flow.conversation(event).send(f"You said: {said}")
