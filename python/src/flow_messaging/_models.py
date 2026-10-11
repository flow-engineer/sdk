# Generated from openapi/openapi.yaml by python/scripts/generate.py. Do not edit.
# The friendly names to import are in flow_messaging.types.
# ruff: noqa

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class Account(BaseModel):
    """
    A customer company. Holds the plan, billing and members. Every app belongs to one account.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["acct_01JB8YZ3N2Q4R6T8V0X2Z4B6D8"])]
    """
    An account ID, `acct_` and a ULID.
    """
    name: str
    """
    The company's name.
    """
    plan: Literal["free", "pro", "business", "enterprise"]
    """
    The account's plan.
    """
    hipaa: bool | None = None
    """
    `true` when the account handles protected health information under a
    business associate agreement with Flow. Its messages then go only
    through channels Flow holds such an agreement for (SMS): sends, typing,
    read receipts and sender connections on Telegram, WhatsApp and iMessage
    answer `403 permission` with `channel_code` `hipaa_channel_not_covered`,
    and messages already queued there fail the same way. The sandbox
    senders answer the account's contacts with a fixed refusal and store
    and deliver nothing they send; turning the flag on ends the account's
    sandbox joins. Only SMS can be simulated (`POST /v1/test/conversations`):
    creating a simulated Telegram, WhatsApp or iMessage conversation, or posting a
    turn to one made before the flag was set, answers the same refusal.
    Set by the Flow team.

    """
    created_at: datetime
    """
    When the account was created.
    """


class AllowanceCount(BaseModel):
    """
    Contacts the allowance has room for, and how many have joined (with `scope` `person`, over all the person's apps).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    limit: int
    """
    How many contacts may join on the sandbox (1 for an anonymous app; 3 for a signed-in person, over all their apps).
    """
    used: int
    """
    How many have joined so far.
    """


class AllowanceMessages(BaseModel):
    """
    Messages sent against the allowance, over all its contacts (with `scope` `person`, from all the person's apps).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    limit: int
    """
    `contacts.limit` times `messages_per_contact`.
    """
    used: int
    """
    Messages sent so far on the allowance's sandbox senders.
    """
    remaining: int
    """
    Messages still allowed, counting each contact's own cap and the contacts that may still join.
    """


class ApiKey(BaseModel):
    """
    An API key's record. The key itself is shown once, at creation, and stored only as a hash.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["key_01JB8Z1B2D4F6H8K0M2P4R6T8W"])]
    """
    An API key's ID, `key_` and a ULID. Not the secret key itself.
    """
    mode: Literal["test", "live"]
    """
    `test` (sandbox senders and test data only) or `live`.
    """
    last4: str
    """
    The key's last four characters, to tell keys apart.
    """
    created_at: datetime
    """
    When the key was created.
    """
    expires_at: datetime | None = None
    """
    When the key stops working. Set only on keys of an unclaimed app made with
    `POST /v1/sandbox/keys` (7 days after it was made); signing in through the
    device flow claims the app and removes it. An expired key can still start
    that sign-in for 30 days after this time, and claiming the app within those
    30 days makes the key work again.

    """


class App(BaseModel):
    """
    One agent integration. Owns API keys (per mode), webhook endpoints and settings.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["app_01JB8Z0A1C3E5G7J9K1M3P5R7T"])]
    """
    An app ID, `app_` and a ULID.
    """
    account: Annotated[str, Field(examples=["acct_01JB8YZ3N2Q4R6T8V0X2Z4B6D8"])]
    """
    An account ID, `acct_` and a ULID.
    """
    name: str
    """
    The app's name.
    """
    api_version: date
    """
    The API version pinned to the app when it was created, used when a request sends no `Flow-Version`.
    """
    settings: AppSettings
    sandbox_join_code: Annotated[str | None, Field(examples=["brave-otter-40718263"])] = (
        None
    )
    """
    The app's sandbox join code on its own, without the word `join`: two words and eight digits, for example `brave-otter-40718263`. A contact joins this app by sending `join ` followed by it to a shared sandbox sender (`join brave-otter-40718263`); each shared sender's `join_code` gives that whole message.

    """
    created_at: datetime
    """
    When the app was created.
    """


class AppContext(BaseModel):
    """
    Who is calling, as worked out from the API key.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    account: Account
    app: App
    api_key: ApiKey
    livemode: bool
    """
    `true` for a live key, `false` for a test key.
    """
    allowance: SandboxAllowance | None = None


class AppSettings(BaseModel):
    """
    Per-app behaviour. The Flow team sets it for now; ask them to change it.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    transcription: bool
    """
    When on, inbound voice notes carry a `transcript` (adds about 1 to 2 seconds to voice notes only).
    """
    auto_read: bool
    """
    When on, Flow marks inbound messages as read as soon as your endpoint accepts them.
    """


class ButtonReplyContent(BaseModel):
    """
    Inbound only. The contact tapped a reply button (or, where buttons fell back to numbered text, answered with its number).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["button_reply"]
    """
    Always `button_reply`.
    """
    button_id: str
    """
    The `id` of the tapped button.
    """
    label: str
    """
    The tapped button's label.
    """
    message_id: Annotated[
        str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])
    ] = None
    """
    A message ID, `msg_` and a ULID.
    """


class ButtonsContent(BaseModel):
    """
    Text with buttons, sent only. Telegram shows an inline keyboard; WhatsApp shows
    up to 3 reply buttons, or a list for more; iMessage has no buttons (use
    `fallback`). A tap arrives as a `message.received` event with `button_reply`
    content carrying the button's `id`. URL buttons open a link and send nothing
    back.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["buttons"]
    """
    Always `buttons`.
    """
    text: str
    """
    The text above the buttons: at most 4096 characters on Telegram (the same
    as a text message, in UTF-16 code units; Telegram's 1024 limit is for media
    captions only) and 1024 on WhatsApp (its limit for messages with buttons). On iMessage,
    `fallback: auto` sends the text and the numbered choices as one text
    message, which must fit the channel's `max_text_length`. Longer text is
    refused with `invalid_request`.

    """
    buttons: list[ReplyButton | UrlButton]
    """
    1 to 10 buttons, in order.
    """


class Capabilities(BaseModel):
    """
    What a conversation's channel supports now.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    conversation: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    window: WindowState
    content: list[ContentSupport]
    """
    One entry per content type that can be sent.
    """
    limits: ChannelLimits | None = None


class ChannelLimits(BaseModel):
    """
    Size limits on this channel.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    max_text_length: int | None = None
    """
    The longest text one message may carry, in characters (4096 on Telegram and WhatsApp, 9999 on iMessage, 1530 on SMS). Telegram counts UTF-16 code units, so an emoji such as 😀 counts as 2; the other channels count Unicode characters. A media caption takes at most 1024. Longer text is refused with `invalid_request`.
    """
    max_sms_segments: int | None = None
    """
    SMS only. The most segments one text may take (10); see `SmsSegments`. A text of more segments is refused with `invalid_request`: 1530 GSM-7 characters (fewer when it uses GSM-7's two-unit characters such as `{` or `€`), or 670 when it holds an emoji or other character outside GSM-7.

    """
    max_buttons: int | None = None
    """
    The most buttons one message may carry natively.
    """
    max_file_bytes: int | None = None
    """
    The largest file one message may carry.
    """


class ChannelOptions(BaseModel):
    """
    **Unstable escape hatch.** Extra channel parameters for how a message looks
    and notifies, for example `{"parse_mode": "HTML"}` on Telegram. Each channel
    has an allowlist: keys not on it are dropped, never passed to the channel, and
    the typed request always wins over a key that sets the same thing. Who
    receives the message and what it says always come from the typed request.
    Keys starting with `_flow_` are reserved and refused with `invalid_request`.
    Flow does not validate the values, and they may break when a channel
    changes. Prefer typed content.

    - **Telegram** (Bot API parameters, on every send): `parse_mode`,
      `entities`, `caption_entities`, `link_preview_options`,
      `disable_web_page_preview`, `show_caption_above_media`,
      `disable_notification`, `protect_content`, `allow_paid_broadcast`,
      `message_effect_id`, `has_spoiler`, `supports_streaming`, `duration`,
      `width`, `height`, `performer`, `horizontal_accuracy`, `foursquare_id`,
      `foursquare_type`, `google_place_id`, `google_place_type`, `vcard`,
      `is_big` (reactions).
    - **iMessage**: on messages, `subject`, `effect`, `preview`,
      `reply_to_id` and `contact_file`; on `typing` content, `typing` (how long
      to show it, 1 to 60 seconds). Reactions, read receipts, edits and unsends
      take none.
    - **WhatsApp**: on `text` content, `preview_url` (show a link preview;
      by default on when the text holds an http(s) link). Everything else
      (recipient, message type, reply context) comes from the typed fields.

    """

    model_config = ConfigDict(
        extra="allow",
    )


class Consent(BaseModel):
    """
    The contact's consent to receive messages from you, as you recorded it
    before starting the conversation. Required to start an SMS conversation
    with someone who has never texted your numbers (US law, the TCPA, needs
    their prior express consent). Flow keeps it on the contact. It does not
    undo an opt-out: only the contact texting START does.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    obtained_at: datetime
    """
    When the person gave consent. Not in the future.
    """
    method: Literal["web_form", "paper_form", "verbal", "text_message", "app", "other"]
    """
    How they gave it.
    """
    proof: str | None = None
    """
    Your own reference to the record of consent (a form submission ID or URL). Do not put health information here.
    """


class Contact(BaseModel):
    """
    A person on one channel. There is no cross-channel identity, and a contact may have no phone number at all (a Telegram user, a WhatsApp username, an iMessage email handle).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])]
    """
    A contact ID, `ct_` and a ULID.
    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    livemode: bool
    """
    Whether the contact belongs to live mode.
    """
    address: ContactAddress
    name: str | None = None
    """
    The contact's display name, as the channel reports it. May change or be missing.
    """
    opted_out_at: datetime | None = None
    """
    SMS. When the contact opted out of your app's SMS messages. Absent when
    they have not, or texted START (or UNSTOP, YES) since to a number they
    opted out through (START to another of your numbers does not lift it,
    since carriers and providers block per number). While it is set, sends
    to them on every SMS sender of your app answer `403 permission` with
    `channel_code` `contact_opted_out`. Every opt-out, opt-in and recorded
    consent is kept in the contact's history.

    """
    opted_out_via: Literal["keyword", "carrier"] | None = None
    """
    SMS. How the contact opted out: `keyword` (they texted STOP or one of
    its variants) or `carrier` (the carrier or provider reported the number
    unsubscribed when Flow sent to it). Set with `opted_out_at`.

    """
    consent: ContactConsent | None = None
    simulated: bool | None = None
    """
    `true` for a simulated contact, who exists only inside Flow (test mode only, from `POST /v1/test/conversations`); absent otherwise.
    """
    created_at: datetime
    """
    When Flow first saw the contact.
    """


class ContactAddress(BaseModel):
    """
    How the contact is reached on their channel. Which fields are set depends on the channel; do not assume `phone`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    phone: str | None = None
    """
    E.164 phone number (WhatsApp and SMS; iMessage when the handle is a number).
    """
    username: str | None = None
    """
    A username without `@` (Telegram, WhatsApp usernames).
    """
    telegram_user_id: str | None = None
    """
    Telegram's numeric user ID, as a string.
    """
    handle: str | None = None
    """
    iMessage handle (a phone number or an email address).
    """


class ContactCardContent(BaseModel):
    """
    A contact card, both ways. Channels without cards need `fallback` (`auto` sends it as text).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["contact_card"]
    """
    Always `contact_card`.
    """
    name: str
    """
    The person's or business's name.
    """
    phones: list[str] | None = None
    """
    Phone numbers, E.164 where known.
    """
    emails: list[str] | None = None
    """
    Email addresses.
    """


class ContactConsent(Consent):
    """
    SMS. The consent recorded with the latest start to this contact that carried one. Absent when none was recorded.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    recorded_at: datetime
    """
    When Flow recorded it.
    """


class ContactDeletedData(BaseModel):
    """
    The contact that was deleted. Only the ID is kept.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    contact: Annotated[str, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])]
    """
    A contact ID, `ct_` and a ULID.
    """


class ContactList(BaseModel):
    """
    A page of contacts.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    data: list[Contact]
    has_more: bool
    """
    Whether more items lie beyond this page in the direction you paged.
    """


class ContentSupport(BaseModel):
    """
    How the channel handles one content type.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["text", "media", "voice", "buttons", "button_reply", "reaction", "template", "location", "contact_card", "effect", "typing", "read", "edit", "unsend", "file_blocked"]
    """
    The kinds of content. Each is described in its own schema, with the direction it travels in.
    """
    support: Literal["native", "fallback", "unsupported"]
    """
    `native` (shown as sent), `fallback` (needs `fallback`; `auto` sends `fallback_type`) or `unsupported` (cannot be sent).
    """
    fallback_type: Literal["text", "media", "none"] | None = None
    """
    With `support` `fallback`, what `fallback: "auto"` sends instead, or `none` when it is skipped.
    """
    note: str | None = None
    """
    A limit worth knowing (for example "up to 3 buttons, else a list").
    """


class Conversation(BaseModel):
    """
    One sender talking with one contact. Holds the window state and whether the contact opted in.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    app: Annotated[str, Field(examples=["app_01JB8Z0A1C3E5G7J9K1M3P5R7T"])]
    """
    An app ID, `app_` and a ULID.
    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    contact: Annotated[str, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])]
    """
    A contact ID, `ct_` and a ULID.
    """
    livemode: bool
    """
    Whether the conversation belongs to live mode.
    """
    last_inbound_at: datetime | None = None
    """
    When the contact last wrote. Absent if they never have.
    """
    window_open_until: datetime | None = None
    """
    WhatsApp only. Until when free-form messages may be sent; after it, only templates. Absent when the window is closed or the channel has none.
    """
    opted_in: bool
    """
    Whether the contact has agreed to receive messages (wrote first, joined the sandbox, or you recorded consent).
    """
    simulated: bool | None = None
    """
    `true` for a simulated conversation, whose contact exists only inside Flow (test mode only, from `POST /v1/test/conversations`); absent otherwise.
    """
    metadata: dict[str, str] | None = None
    created_at: datetime
    """
    When the conversation began.
    """


class ConversationAction(BaseModel):
    """
    The result of a typing or read call.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    conversation: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    action: Literal["typing_on", "typing_off", "read"]
    """
    Which action was taken.
    """
    delivered_as: DeliveredAs | None = None


class ConversationList(BaseModel):
    """
    A page of conversations.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    data: list[Conversation]
    has_more: bool
    """
    Whether more items lie beyond this page in the direction you paged.
    """


class ConversationRef(BaseModel):
    """
    The conversation an event happened in, inlined so most handlers need no extra call.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    contact: Annotated[str, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])]
    """
    A contact ID, `ct_` and a ULID.
    """
    window_open_until: datetime | None = None
    """
    WhatsApp only. Until when free-form messages may be sent. Absent when closed or not applicable.
    """
    simulated: bool | None = None
    """
    `true` for a simulated conversation, whose contact exists only inside Flow (test mode only, from `POST /v1/test/conversations`); absent otherwise.
    """


class ConversationStartedData(BaseModel):
    """
    The new conversation and how it began.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    conversation: Conversation
    via: Literal["inbound", "sandbox_join", "outbound"]
    """
    `inbound` (the contact wrote first), `sandbox_join` (they sent your app's join code) or `outbound` (you started it).
    """


class Deleted(BaseModel):
    """
    Confirms that an object was deleted.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: str
    """
    The deleted object's ID.
    """
    deleted: bool
    """
    Always `true`.
    """


class DeliveredAs(BaseModel):
    """
    Present when what the contact sees differs from what you sent: the `fallback`
    was used, or the action was skipped because the channel has no equivalent.
    Absent when the content was shown as sent.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["text", "media", "voice", "buttons", "reaction", "template", "location", "contact_card", "effect", "typing", "read", "edit", "unsend", "none"]
    """
    The content type actually shown, or `none` when nothing was shown.
    """
    reason: str
    """
    Why, in one sentence (for example "iMessage cannot show buttons; sent numbered text").
    """


class DeviceAuthorization(BaseModel):
    """
    A device sign-in waiting for a person to approve it in a browser.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    device_code: Annotated[str, Field(examples=["fdc_..."])]
    """
    The secret you poll `POST /v1/device/token` with. Never show it to the person.
    """
    user_code: Annotated[str, Field(examples=["WDJB-MJHT"])]
    """
    The code the person types on the approval page, eight letters in two groups. Always show it to the person, also when you show `verification_uri_complete`.
    """
    verification_uri: Annotated[
        str, Field(examples=["https://api.flow.engineer/admin/device"])
    ]
    """
    The page where the person signs in and enters `user_code`.
    """
    verification_uri_complete: Annotated[
        str, Field(examples=["https://api.flow.engineer/admin/device?code=WDJB-MJHT"])
    ]
    """
    The same page for this sign-in. Show this link (or a QR code of it) to the person together with `user_code`; the page asks them to type the code they see from you and checks it against the link, so a link on its own cannot approve a sign-in.
    """
    expires_in: int
    """
    Seconds until the codes expire (15 minutes).
    """
    expires_at: datetime
    """
    When the codes expire.
    """
    interval: int
    """
    Seconds to wait between polls of `POST /v1/device/token`.
    """


class DeviceAuthorizationRequest(BaseModel):
    """
    Optional details for a device sign-in.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    claim_token: str | None = None
    """
    The `claim_token` from `POST /v1/sandbox/keys`, to claim that app when the person approves.
    """
    client_name: str | None = None
    """
    What is asking, shown to the person on the approval page, for example "flow CLI" or "Claude Code".
    """


class DeviceToken(BaseModel):
    """
    A device sign-in's state. With `approved`, it carries a new test key (shown
    once), the app it belongs to and whether a sandbox app was claimed.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    status: Literal["pending", "approved", "denied", "expired"]
    """
    - `pending`: the person has not finished; poll again after `interval` seconds.
    - `approved`: signed in; `key` is set. The device code is now used up.
    - `denied`: the person refused. Stop polling.
    - `expired`: the codes ran out or were already used. Start again.

    """
    interval: int
    """
    Seconds to wait before the next poll.
    """
    key: str | None = None
    """
    `approved` only. A new API key (`fk_test_...`), shown once; store it as `FLOW_MESSAGING_KEY` in place of the sandbox key. When the sign-in claimed a sandbox app, that app's sandbox keys stop working as this key is handed out.
    """
    api_key: ApiKey | None = None
    account: Account | None = None
    app: App | None = None
    claimed: bool | None = None
    """
    `approved` only. `true` when the sign-in claimed the app of the `claim_token` or key it was started with.
    """
    allowance: SandboxAllowance | None = None
    user: SignedInUser | None = None


class DeviceTokenRequest(BaseModel):
    """
    The device sign-in to poll.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    device_code: str
    """
    The `device_code` from `POST /v1/device/authorizations`.
    """


class EditContent(BaseModel):
    """
    Replaces the text of one of your sent messages, sent only (over HTTP use `PATCH /v1/messages/{message_id}`). Telegram and iMessage; WhatsApp refuses it with `unsupported_content`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["edit"]
    """
    Always `edit`.
    """
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """
    content: TextContent


class EditMessageRequest(BaseModel):
    """
    The new text of a sent message.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    content: TextContent


class EffectContent(BaseModel):
    """
    Text sent with an iMessage effect, sent only. Other channels need `fallback` (`auto` sends the plain text). Which effects are available may vary.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["effect"]
    """
    Always `effect`.
    """
    text: str
    """
    The text, at most the channel's `max_text_length` characters (4096 on Telegram and WhatsApp, 9999 on iMessage, 1530 on SMS, where it must also fit in 10 segments, 670 characters when it holds an emoji or other character outside GSM-7; see `GET /v1/capabilities`). Telegram counts UTF-16 code units, so an emoji such as 😀 counts as 2. Longer text is refused with `invalid_request`.
    """
    effect: Literal["slam", "loud", "gentle", "invisible_ink", "echo", "spotlight", "balloons", "confetti", "love", "lasers", "fireworks", "celebration"]
    """
    The effect.
    """


class Error(BaseModel):
    """
    The body of every error answer.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    error: ErrorBody


class ErrorBody(BaseModel):
    """
    The details of an error.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["invalid_request", "authentication", "permission", "not_found", "idempotency_conflict", "outside_window", "unsupported_content", "new_contact_limit", "sender_throttled", "file_blocked", "rate_limited", "channel_error", "not_implemented", "api_error"]
    """
    What went wrong. A closed list: new types arrive only with a new API version.
    Each type has a page at `https://api.flow.engineer/docs/errors/<type>`, given in
    the error's `doc_url`; the error's `hint` says what to change for the case.

    - `invalid_request` (400, or 413 for a request body over the size limit): the request is malformed or a parameter is invalid. Fix the parameter named in `param`; the `hint` says what it must look like. Every endpoint answers it for a `Flow-Version` header that is not a version this API serves.
    - `authentication` (401): the API key is missing, malformed, unknown, revoked or expired. Send `Authorization: Bearer fk_test_...` or `fk_live_...` with a current key; with no key at all, get a test key with `POST /v1/sandbox/keys`. A sandbox key past its `expires_at` has `channel_code` `sandbox_key_expired`: sign in to claim the app, or get a new key.
    - `permission` (403): the key may not do this, for example a test key using a live sender, a sandbox contact who joined another app, a new conversation from an iMessage line that may only reply, or a send past the app's sandbox allowance (`channel_code` `sandbox_allowance_used`, `sandbox_contact_limit` or `sandbox_channel_not_included`). Use the key of the right mode, have the contact send your join code, wait for the contact to message the line first, or sign in through the device flow to lift the allowance. On SMS: `contact_opted_out` (the contact texted STOP; nothing more goes to them until they text START), `consent_required` (a start to someone who never texted your numbers: record their consent with `consent` on the start). In a HIPAA account: `hipaa_channel_not_covered` (the channel has no business associate agreement; use SMS). Simulated conversations: `simulated_contact` (a real sender was pointed at a simulated contact; reply in the contact's simulated conversation), `not_simulated` (a simulated sender or test endpoint was pointed at a real contact), `test_mode_only`, `simulated_conversation_limit`. In `message.failed`: `sandbox_contact_left` (the contact joined another app on the sandbox sender while the message was queued; have them send your join code again).
    - `not_found` (404): no such object for this app and mode. Check the ID's prefix and that it was made with a key of the same mode (test and live data are separate).
    - `idempotency_conflict` (409): the idempotency key was used for a different request (`channel_code` `body_mismatch`: use a new key), or that request is still running (`in_progress`: wait `retry_after` seconds and repeat it with the same key), or it already created a secret that is shown only once (`secret_not_kept`: creating a webhook endpoint, rotating its secret; a secret that was lost must be rotated again).
    - `outside_window` (409, or in `message.failed`): the channel will not deliver outside its conversation window. On WhatsApp the 24-hour window is closed: send a `template` (`POST /v1/messages` with `content.type=template`), or wait for the contact to write. On iMessage the contact has not messaged the line (or opted in) yet, or not recently, so the failure arrives as a `message.failed` event: wait for the contact to write, then reply in that conversation. Typing and read receipts answer `409 outside_window` directly when the channel's window for them is closed (iMessage typing works only within 5 minutes of the contact's last message; WhatsApp read receipts go at any time); ignore it and send your reply. On SMS, `channel_code` `quiet_hours`: the contact has not texted in the last hour and it is inside the sender's quiet hours in their time zone; retry after `retry_after` seconds, or wait for them to text. In `message.failed`: `window_closed` (WhatsApp's 24-hour window closed while the message was queued; send a template) and `queued_too_long` (the message waited in the queue longer than its sender allows, for example while the sender was paused; send it again if it still applies).
    - `unsupported_content` (422): the channel cannot show this content and no `fallback` was set. Set `fallback` (`"auto"` or your own content), or check `GET /v1/capabilities` first.
    - `new_contact_limit` (429): the sender has used its budget for starting conversations. Wait `retry_after` seconds; replies into existing conversations still go.
    - `sender_throttled` (429): abuse signals tripped (the same text to many new contacts, many starts with no reply, blocks), so the sender may not start conversations until `retry_after`; replies into existing conversations still go. Personalise first messages and start only conversations people expect.
    - `file_blocked` (422): the file failed the malware scan and was not stored. Send a different file.
    - `rate_limited` (429): either too many requests for this key (the per-key request limit, reported in the `RateLimit-*` headers) or sends faster than the sender's sending rate (pacing). Wait `Retry-After` (`retry_after`) seconds and retry with the same `Idempotency-Key`.
    - `channel_error` (502, or in `message.failed`): the channel refused or failed the message, or timed out; `channel_code` carries its own code. Read `message`, change what the channel objected to, and send again. From typing and read receipts, which call the channel at once, it is safe to ignore. SMS codes are Flow's, the same whichever carrier network carries the message: `carrier_filtered` (a carrier's spam filter blocked it: make it read like a person's message, no shortened links), `unreachable`, `invalid_number`, `landline`, `registration_required` (the number's 10DLC or toll-free registration is not approved yet), `carrier_error`, and `provider_not_configured` (the SMS sender is not fully set up on Flow's side, so nothing was sent; contact the Flow team). Flow's own codes on every channel: `channel_timeout_unknown_outcome` (in `message.failed`: the channel did not answer after the message was sent, and the resends its policy allows did not settle it, so the message may have arrived or not; check with the contact before sending it again) and `unknown_outcome` (from typing and read receipts: the call timed out after it was sent).
    - `not_implemented` (501): this endpoint or channel is not live yet during the beta. Use a channel that is live (Telegram, iMessage), or check the changelog.
    - `api_error` (500, 503): something went wrong on Flow's side. Retry with the same idempotency key after `retry_after` seconds, and quote `request_id` if it persists.

    """
    message: str
    """
    A sentence for a developer saying what went wrong. Do not parse it; switch on `type`.
    """
    hint: Annotated[
        str,
        Field(
            examples=["Send a template instead: POST /v1/messages with content.type=template."]
        ),
    ]
    """
    One sentence saying what to change to make the request succeed, specific
    to this case, for example "Send a template instead: POST /v1/messages with
    content.type=template." Written for developers and coding agents alike. Do
    not parse it; it may be reworded at any time.

    """
    doc_url: Annotated[
        str, Field(examples=["https://api.flow.engineer/docs/errors/outside_window"])
    ]
    """
    The documentation page for this error's type, `https://api.flow.engineer/docs/errors/<type>`. It says what the error means, why it happens and how to fix it, with code.
    """
    param: str | None = None
    """
    The request parameter the error is about, as a dotted path (`content.buttons`, `limit`).
    """
    retry_after: int | None = None
    """
    Seconds to wait before retrying, for errors that clear by themselves.
    """
    conversation: Annotated[
        str | None, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])
    ] = None
    """
    A conversation ID, `conv_` and a ULID.
    """
    sender: Annotated[str | None, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])] = (
        None
    )
    """
    A sender ID, `snd_` and a ULID.
    """
    channel_code: str | None = None
    """
    For `channel_error`, the channel's own error code, as given by the
    channel. For some other errors, Flow's own code naming the case, for
    example `sandbox_allowance_used` (`permission`: the sandbox allowance is
    used up), `sandbox_contact_limit` (`permission`: the allowance has no
    room for another contact), `sandbox_channel_not_included` (`permission`:
    the allowance does not cover this sandbox channel), `sign_in_required`
    (`permission`: an app made without an account cannot do this) or
    `sandbox_key_expired` (`authentication`: a key from `POST
    /v1/sandbox/keys` passed its `expires_at`; `permission`, for a send
    that carries no key, such as a reply in a webhook answer, from such an
    app). For `idempotency_conflict`, always one of `body_mismatch` (the
    key was used for a different request), `in_progress` (the first
    request is still running; `retry_after` says when to repeat it) or
    `secret_not_kept` (its answer carried a secret shown only once).
    SMS: `contact_opted_out` and `consent_required` (`permission`),
    `quiet_hours` (`outside_window`, with `retry_after`), and
    `carrier_filtered`, `unreachable`, `invalid_number`, `landline`,
    `registration_required`, `carrier_error` and `provider_not_configured`
    (`channel_error`). HIPAA accounts: `hipaa_channel_not_covered`
    (`permission`). Simulated conversations (`permission`): `test_mode_only`,
    `not_simulated`, `simulated_contact` and `simulated_conversation_limit`.
    For a message that failed after it was queued (`message.failed`):
    `sandbox_contact_left` (`permission`), `window_closed` and
    `queued_too_long` (`outside_window`), and
    `channel_timeout_unknown_outcome` (`channel_error`: the channel never
    confirmed the send, so it may or may not have arrived). From typing and
    read receipts, `unknown_outcome` (`channel_error`: the call timed out after
    it was sent).

    """
    request_id: str | None = None
    """
    Flow's ID for this request. Quote it when asking for help.
    """


class EventBase(BaseModel):
    """
    The fields every event has.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["evt_01JB8ZE5N7Q9S1V3X5Z7B9D1E3"])]
    """
    An event ID, `evt_` and a ULID.
    """
    created_at: datetime
    """
    When the event was created. Events are ordered in the log by commit, not by this time.
    """
    app: Annotated[str, Field(examples=["app_01JB8Z0A1C3E5G7J9K1M3P5R7T"])]
    """
    An app ID, `app_` and a ULID.
    """
    livemode: bool
    """
    Whether the event belongs to live mode.
    """
    conversation: ConversationRef | None = None
    timing: Timing


class ContactDeletedEvent(EventBase):
    """
    A contact was deleted with `DELETE /v1/contacts/{contact_id}`: their address,
    messages, files and events are erased at Flow. Delete what you keep about
    them too. Sent once, for the first delete; it has no `conversation`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["contact.deleted"]
    """
    Always `contact.deleted`.
    """
    data: ContactDeletedData


class ConversationStartedEvent(EventBase):
    """
    A new conversation began. Sent before the first `message.received` of a new
    contact, or, when you started the conversation (`data.via` `outbound`), with
    your first send to the contact. A sandbox join (`data.via` `sandbox_join`) also starts one: the join
    message itself is not delivered as `message.received`, and the sandbox bot's
    confirmation ("You're connected to <your app>") is sent by Flow itself, not
    by your app, and counts against no allowance. Joining again in a
    conversation that already exists sends no new `conversation.started`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["conversation.started"]
    """
    Always `conversation.started`.
    """
    data: ConversationStartedData


class ConversationWindowClosingEvent(EventBase):
    """
    WhatsApp only, opt-in per endpoint. The conversation's 24-hour window closes in 1 hour.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["conversation.window_closing"]
    """
    Always `conversation.window_closing`.
    """
    data: WindowClosingData


class EventList(BaseModel):
    """
    A page of events, oldest first.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    data: list[
        Annotated[
            MessageReceivedEvent | MessageSentEvent | MessageDeliveredEvent | MessageReadEvent | MessageFailedEvent | ReactionAddedEvent | ReactionRemovedEvent | TypingStartedEvent | TypingStoppedEvent | ConversationStartedEvent | ConversationWindowClosingEvent | SenderStatusChangedEvent | TemplateStatusChangedEvent | ContactDeletedEvent,
            Field(discriminator="type"),
        ]
    ]
    has_more: bool
    """
    Whether more committed events follow this page.
    """


class File(BaseModel):
    """
    A stored file. Send it as `media` or `voice` content by `file_id`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5"])]
    """
    A file ID, `file_` and a ULID.
    """
    mime_type: str
    """
    The real type, checked from the first bytes.
    """
    size_bytes: int
    """
    The file's size.
    """
    filename: str | None = None
    """
    The file's name, if it has one.
    """
    url: str
    """
    Its Flow URL (`https://api.flow.engineer/v1/files/{file_id}`), which redirects to the bytes for an authenticated request.
    """
    livemode: bool
    """
    Whether the file belongs to live mode.
    """
    created_at: datetime
    """
    When the file was stored.
    """
    expires_at: datetime
    """
    When the file will be deleted under your plan's retention.
    """


class FileBlockedContent(BaseModel):
    """
    Inbound only. The contact sent a file that Flow did not keep: it failed the
    malware scan, its real type is one Flow does not pass on (programs, web
    pages), it could not be scanned, or it is larger than the channel lets Flow
    download. The file is not stored and has no `url`; what is known about it is
    here. Images, audio and video are not scanned; documents (PDF, Office,
    archives) are.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["file_blocked"]
    """
    Always `file_blocked`.
    """
    reason: Literal["malware", "type_not_allowed", "scan_failed", "too_large"]
    """
    Why the file was not kept: `malware` (the scan found something), `type_not_allowed`, `scan_failed` (the scanner could not check it; ask the contact to send it again), or `too_large`.
    """
    kind: Literal["image", "video", "document", "audio"] | None = None
    """
    What kind of media the channel said it was.
    """
    filename: str | None = None
    """
    The file's name, if it had one.
    """
    mime_type: str | None = None
    """
    The real type, read from the file's first bytes, when Flow read them.
    """
    size_bytes: int | None = None
    """
    The file's size, when known.
    """
    caption: str | None = None
    """
    Text the contact sent with the file.
    """


class FileUpload(BaseModel):
    """
    A file to upload, as multipart form data.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    file: bytes
    """
    The file's bytes. Its real type is read from its first bytes.
    """
    filename: str | None = None
    """
    The name to show for the file; defaults to the uploaded part's file name.
    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"] | None = None
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """


class LocationContent(BaseModel):
    """
    A place, both ways. Inbound, a location the contact shared. Channels without locations need `fallback` (`auto` sends a maps link).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["location"]
    """
    Always `location`.
    """
    lat: float
    """
    Latitude in degrees.
    """
    lng: float
    """
    Longitude in degrees.
    """
    name: str | None = None
    """
    The place's name.
    """
    address: str | None = None
    """
    The place's address.
    """


class MediaContent(BaseModel):
    """
    An image, video, document or audio file, both ways. When sending, give either
    `url` (Flow fetches it) or `file_id` (from `POST /v1/files`). Inbound media
    always has `url`, a Flow file URL (`GET /v1/files/{file_id}`), and `file_id`,
    on every channel (an SMS contact's MMS files included), and `mime_type` and
    `size_bytes` once Flow kept the file. On SMS Flow always keeps its own copy
    (the provider's is deleted): an MMS file it could not fetch or check arrives
    as `file_blocked` instead. Send a received file again by its `file_id`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["media"]
    """
    Always `media`.
    """
    kind: Literal["image", "video", "document", "audio"]
    """
    What kind of media it is.
    """
    url: str | None = None
    """
    Where the bytes are. Sending, an HTTPS URL Flow can fetch; inbound, a Flow file URL.
    """
    file_id: Annotated[str | None, Field(examples=["file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5"])] = (
        None
    )
    """
    A file ID, `file_` and a ULID.
    """
    caption: str | None = None
    """
    Text shown with the media, at most 1024 characters. Telegram counts UTF-16 code units, so an emoji such as 😀 counts as 2. Longer captions are refused with `invalid_request`.
    """
    filename: str | None = None
    """
    The file's name, shown for documents.
    """
    mime_type: str | None = None
    """
    The real type, checked from the file's first bytes.
    """
    size_bytes: int | None = None
    """
    The file's size.
    """


class Message(BaseModel):
    """
    One message in or out of a conversation, with its typed content and delivery status.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """
    conversation: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    direction: Literal["in", "out"]
    """
    `in` from the contact, `out` from your app.
    """
    status: Literal["received", "queued", "sent", "delivered", "read", "failed", "unsent"]
    """
    - `received`: inbound from the contact.
    - `queued`: accepted by the gate, waiting for its turn in the conversation.
    - `sent`: the channel accepted it.
    - `delivered`: it reached the contact's device, where the channel reports this.
    - `read`: the contact read it, where the channel reports this.
    - `failed`: it could not be sent; see `error`.
    - `unsent`: you unsent it.

    """
    content: Annotated[
        TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent,
        Field(discriminator="type"),
    ]
    """
    One piece of content, in either direction. `type` selects the shape. Inbound
    messages use `text`, `media`, `voice`, `button_reply`, `reaction`, `location`,
    `contact_card` and `file_blocked`; sends use every type except `button_reply`
    and `file_blocked`.

    | type | Telegram | WhatsApp | iMessage | SMS (US, pilot) | `fallback: "auto"` |
    |---|---|---|---|---|---|
    | text | yes | yes | yes | yes (at most 10 segments) | markdown to plain |
    | media | yes | yes | yes | images, audio, video as MMS (no documents) | none |
    | voice | yes | yes | yes | as an MMS audio file | audio file |
    | buttons | inline keyboard | up to 3 buttons, else a list | no | no | numbered text |
    | reaction | yes | yes | tapbacks, other emoji as emoji reactions | no | closest tapback, else skipped (SMS: none) |
    | template | no | yes | no | no | none |
    | location | yes | yes | no | no | maps link as text |
    | contact_card | yes | yes | no | no | text |
    | effect | no | no | yes | no | plain text |
    | typing | yes | yes | yes (within 5 minutes of the contact's last message) | no | skipped |
    | read | no (bots) | yes | yes (the whole conversation) | no | skipped |
    | edit | yes | no | yes (within 15 minutes) | no | none |
    | unsend | yes (within 48 hours) | no | yes (within 2 minutes) | no | none |

    """
    delivered_as: DeliveredAs | None = None
    error: ErrorBody | None = None
    channel_message_id: str | None = None
    """
    The channel's own ID for the message, once the channel accepted it.
    """
    sms: SmsSegments | None = None
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    The Flow ID of the message this one replies to. For a sent message, the
    message the send named in `reply_to`. For a received message, the message it
    replies to inline (a Telegram reply; on iMessage, the thread's root message).
    Absent when the message is not a reply or the quoted message is not known
    to Flow.

    """
    livemode: bool
    """
    Whether the message belongs to live mode.
    """
    metadata: dict[str, str] | None = None
    created_at: datetime
    """
    When Flow received (inbound) or accepted (outbound) the message.
    """
    updated_at: datetime | None = None
    """
    When the status last changed.
    """


class MessageDeliveredEvent(EventBase):
    """
    One of your messages reached the contact's device.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["message.delivered"]
    """
    Always `message.delivered`.
    """
    data: MessageEventData


class MessageEventData(BaseModel):
    """
    The message the event is about.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    message: Message


class MessageFailedEvent(EventBase):
    """
    One of your messages could not be sent. `data.message.error` says why, mapped to an `ErrorType`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["message.failed"]
    """
    Always `message.failed`.
    """
    data: MessageEventData


class MessageList(BaseModel):
    """
    A page of messages.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    data: list[Message]
    has_more: bool
    """
    Whether more items lie beyond this page in the direction you paged.
    """


class MessageReadEvent(EventBase):
    """
    The contact read one of your messages.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["message.read"]
    """
    Always `message.read`.
    """
    data: MessageEventData


class MessageReceivedEvent(EventBase):
    """
    The contact sent a message. `data.message.content` is what they sent.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["message.received"]
    """
    Always `message.received`.
    """
    data: MessageEventData


class MessageSentEvent(EventBase):
    """
    The channel accepted one of your messages.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["message.sent"]
    """
    Always `message.sent`.
    """
    data: MessageEventData


class QuietHours(BaseModel):
    """
    The hours, in the contact's local time zone (worked out from their area
    code; when it is not known, every US time zone must be outside the
    hours), in which the sender does not message contacts who have not texted
    it in the last hour. Absent when the sender has no quiet hours. A send
    inside them answers `409 outside_window` with `channel_code` `quiet_hours`
    and `retry_after`; a message that waited in the queue into them is held
    until they end. Replies to a contact who texted within the hour always
    go.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    start: Annotated[str, Field(examples=["21:00"])]
    """
    When the quiet hours begin, `HH:MM` on a 24-hour clock.
    """
    end: Annotated[str, Field(examples=["08:00"])]
    """
    When they end, `HH:MM` on a 24-hour clock (earlier than `start` when they span midnight).
    """


class ReactionAddedEvent(EventBase):
    """
    The contact reacted to a message.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["reaction.added"]
    """
    Always `reaction.added`.
    """
    data: ReactionEventData


class ReactionContent(BaseModel):
    """
    A reaction to a message, both ways. Set `emoji` to `null` to remove your
    reaction. iMessage has a fixed set of tapbacks; with `fallback: "auto"` the
    closest tapback is used, or the reaction is skipped and reported in
    `delivered_as`. Inbound reactions also arrive as `reaction.added` and
    `reaction.removed` events.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["reaction"]
    """
    Always `reaction`.
    """
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """
    emoji: str | None
    """
    One emoji, or `null` to remove the reaction.
    """


class ReactionEventData(BaseModel):
    """
    A reaction the contact added or removed.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """
    emoji: str
    """
    The emoji (iMessage tapbacks are mapped to their closest emoji).
    """


class ReactionRemovedEvent(EventBase):
    """
    The contact removed a reaction.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["reaction.removed"]
    """
    Always `reaction.removed`.
    """
    data: ReactionEventData


class ReadContent(BaseModel):
    """
    A read receipt, sent only (over HTTP use `POST /v1/conversations/{conversation_id}/read`). Skipped on Telegram, where bots cannot send them. On iMessage the whole conversation is marked read.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["read"]
    """
    Always `read`.
    """
    up_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    The latest inbound message to mark read (default the latest inbound message). No effect on iMessage.
    """


class ReadRequest(BaseModel):
    """
    Which messages to mark as read.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    up_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    The latest inbound message to mark read (default the latest inbound message). On iMessage it has no effect, since the whole conversation is marked read.
    """


class Recipient(BaseModel):
    """
    Who to start a conversation with: an existing `contact`, or an address on the
    sender's channel. Give exactly one field.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    contact: Annotated[str | None, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])] = (
        None
    )
    """
    A contact ID, `ct_` and a ULID.
    """
    phone: str | None = None
    """
    WhatsApp, iMessage or SMS. E.164 phone number; on SMS a US or Canadian number, `+1` and ten digits.
    """
    telegram_user_id: str | None = None
    """
    Telegram. The user's numeric ID; they must have started the bot.
    """
    handle: str | None = None
    """
    iMessage. A phone number or an email address.
    """


class ReplyButton(BaseModel):
    """
    A button that sends its `id` back as a `button_reply` when tapped.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: str
    """
    Your ID for the button, returned in `button_reply`.
    """
    label: str
    """
    The button's text. WhatsApp shows at most 20 characters.
    """


class SandboxAllowance(BaseModel):
    """
    What the app may still send on the shared sandbox senders for free. Present
    only on apps that have one: apps made with `POST /v1/sandbox/keys`
    (`anonymous`, one allowance per app), and apps of people who signed in
    (`signed_in`, one allowance per person: every app the person owns or claimed
    draws on the same contacts and messages, so the counts here are the
    person's, over all those apps). Only messages your agent sends count, on the
    channels in `channels`; inbound messages are free. A contact counts once it
    joins an app on a sandbox sender, and keeps counting after it leaves. Sends
    past the allowance answer `403 permission` with `channel_code`
    `sandbox_allowance_used`; a join past `contacts.limit` is refused in the
    chat.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    tier: Literal["anonymous", "signed_in"]
    """
    `anonymous`: an app made without an account, whose keys expire. `signed_in`: an app of a person who signed in (GitHub; Google sign-in is not enabled yet).
    """
    scope: Literal["app", "person"]
    """
    Who the counts belong to. `app`: this app alone (`anonymous`). `person`:
    the signed-in person, shared by every app they own or claimed, so sends
    from their other apps use the same contacts and messages.

    """
    channels: list[Literal["telegram", "whatsapp", "imessage", "sms"]]
    """
    The sandbox channels the allowance covers whose shared sandbox is open now (Telegram today; WhatsApp when its sandbox opens). Shared senders of other channels (iMessage) are not part of it and refuse its sends.
    """
    contacts: AllowanceCount
    messages_per_contact: int
    """
    How many messages may be sent to each contact (50 anonymous, so 50 in total; 100 signed in).
    """
    messages: AllowanceMessages
    expires_at: datetime | None = None
    """
    `anonymous` only: when the app's keys expire. Signing in removes it.
    """
    upgrade: str
    """
    One sentence saying how to raise the allowance, for example by signing in with `npx @flow-engineer/messaging login`.
    """


class SandboxKey(BaseModel):
    """
    A new app made without an account, with its test key. `key` and `claim_token` are shown only here.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    key: Annotated[str, Field(examples=["fk_test_..."])]
    """
    The API key itself (`fk_test_...`). Shown once; store it as `FLOW_MESSAGING_KEY`.
    """
    api_key: ApiKey
    account: Account
    app: App
    allowance: SandboxAllowance
    claim_token: Annotated[str, Field(examples=["fct_..."])]
    """
    Proves you hold this app when a person signs in to claim it: pass it to
    `POST /v1/device/authorizations`. Shown once; keep it with the key. It
    stops working once the app is claimed.

    """
    claim_url: Annotated[
        str, Field(examples=["https://api.flow.engineer/admin/claim#token=fct_..."])
    ]
    """
    A page where a person signs in with GitHub and claims the app in the browser, without the CLI. It holds the claim token, so treat it like one. The claim hands out no key and revokes the app's keys unless the person ticks "Keep my agent's current key working"; afterwards they make keys on the dashboard's Keys page.
    """
    senders: list[Sender]
    """
    The shared sandbox senders the key can use, each with the link a person opens to join the app (`address.link`) and the join message (`join_code`).
    """


class SandboxKeyRequest(BaseModel):
    """
    Optional details for a new sandbox app.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    name: str | None = None
    """
    The app's name, shown in the dashboard once it is claimed. Defaults to "Sandbox app".
    """


class SendMessageRequest(BaseModel):
    """
    One piece of content to send into a conversation.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    content: Annotated[
        TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent,
        Field(discriminator="type"),
    ]
    """
    One piece of content, in either direction. `type` selects the shape. Inbound
    messages use `text`, `media`, `voice`, `button_reply`, `reaction`, `location`,
    `contact_card` and `file_blocked`; sends use every type except `button_reply`
    and `file_blocked`.

    | type | Telegram | WhatsApp | iMessage | SMS (US, pilot) | `fallback: "auto"` |
    |---|---|---|---|---|---|
    | text | yes | yes | yes | yes (at most 10 segments) | markdown to plain |
    | media | yes | yes | yes | images, audio, video as MMS (no documents) | none |
    | voice | yes | yes | yes | as an MMS audio file | audio file |
    | buttons | inline keyboard | up to 3 buttons, else a list | no | no | numbered text |
    | reaction | yes | yes | tapbacks, other emoji as emoji reactions | no | closest tapback, else skipped (SMS: none) |
    | template | no | yes | no | no | none |
    | location | yes | yes | no | no | maps link as text |
    | contact_card | yes | yes | no | no | text |
    | effect | no | no | yes | no | plain text |
    | typing | yes | yes | yes (within 5 minutes of the contact's last message) | no | skipped |
    | read | no (bots) | yes | yes (the whole conversation) | no | skipped |
    | edit | yes | no | yes (within 15 minutes) | no | none |
    | unsend | yes (within 48 hours) | no | yes (within 2 minutes) | no | none |

    """
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as a reply to an earlier message in the same conversation.
    Telegram and iMessage show it as an inline reply; channels without inline
    replies send it as a normal message. Refused with `not_found` (`param`
    `reply_to`) when the target is not a message in this conversation, and with
    `invalid_request` (`param` `reply_to`) when the content is `typing`, `read`,
    `reaction`, `edit` or `unsend`, or when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    fallback: Literal["auto"] | TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent | None = (
        None
    )
    """
    What to send when the channel cannot show `content`. Without it, such a send
    fails with `unsupported_content`; nothing is converted silently.

    - `"auto"`: use the documented default for the content type (markdown becomes
      plain text, buttons become numbered text whose replies are matched back to
      the button IDs, a voice note becomes an audio file, a location becomes a
      maps link, a contact card becomes text, an effect becomes plain text, a
      reaction becomes the closest tapback or is skipped).
    - A `Content` object: send exactly this instead.

    The message's `delivered_as` reports what was used.

    """
    channel_options: ChannelOptions | None = None
    metadata: dict[str, str] | None = None


class Sender(BaseModel):
    """
    What your agent talks from: a Telegram bot, a WhatsApp number, an iMessage
    line or a US SMS number. `shared` senders are Flow's sandbox, used by many apps in test mode;
    `dedicated` senders are yours alone; `simulated` senders exist only in test
    mode, for simulated conversations. Each sender has its own limits and warm-up
    state.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    kind: Literal["shared", "dedicated", "simulated"]
    """
    `shared` (the sandbox), `dedicated` (yours) or `simulated` (test mode only:
    your app's stand-in for a channel, used by simulated conversations from
    `POST /v1/test/conversations`; it never touches a network).

    """
    livemode: bool
    """
    `false` for sandbox and simulated senders, `true` for dedicated senders used in live mode.
    """
    display_name: str | None = None
    """
    The name contacts see, where the channel shows one.
    """
    status: Literal["pending", "active", "warming_up", "throttled", "flagged", "banned"]
    """
    - `pending`: requested, being provisioned.
    - `active`: sending normally.
    - `warming_up`: active, with a new-contact budget that grows day by day.
    - `throttled`: the gate slowed it after an abuse signal; it recovers by itself.
    - `flagged`: the channel or Flow flagged it; starts are paused. A Telegram
      bot is also `flagged` when Telegram rejects its token (revoked in
      @BotFather): it then sends nothing, new sends answer `403 permission`, and
      queued messages wait until you connect the bot again with its new token
      (`POST /v1/senders`). They wait at most 72 hours after Flow accepted
      them; older ones fail with `outside_window` (`channel_code`
      `queued_too_long`) in `message.failed` instead of going out late.
    - `banned`: it cannot send or receive: the channel banned it, you
      disconnected it (`DELETE /v1/senders/{sender_id}`), or its bot or line was
      connected to another app.

    """
    throttled_until: datetime | None = None
    """
    With status `throttled`, when starts are allowed again. Recovery is automatic.
    """
    address: SenderAddress
    limits: SenderLimits
    quality_rating: Literal["green", "yellow", "red", "unknown"] | None = None
    """
    WhatsApp only. Meta's quality rating for the number.
    """
    sms: SmsSender | None = None
    join_code: Annotated[str | None, Field(examples=["join brave-otter-40718263"])] = (
        None
    )
    """
    Shared senders only. The whole message a contact sends to this sender to join your app: `join `, a space, then the app's `sandbox_join_code` (from `GET /v1/app`), for example `join brave-otter-40718263`. Show it to testers as is.

    """
    created_at: datetime
    """
    When the sender was created.
    """


class SenderAddress(BaseModel):
    """
    How contacts reach the sender. Which fields are set depends on the channel.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    phone: str | None = None
    """
    WhatsApp, iMessage and SMS. E.164 phone number.
    """
    username: str | None = None
    """
    Telegram. The bot's username, without `@`.
    """
    handle: str | None = None
    """
    iMessage. The line's handle (phone number or email address).
    """
    link: str | None = None
    """
    A link that opens a chat with the sender: `https://t.me/...` for a Telegram
    bot, `https://wa.me/...` for a WhatsApp number. For an iMessage line it is
    the line's opt-in link, which opens Messages with the line and a prefilled
    text the person sends to start the conversation; it is set only when the
    line has one configured.

    """


class SenderLimits(BaseModel):
    """
    The sender's current budget for starting conversations.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    new_contacts_per_day: int
    """
    New conversations the sender may start per day today (grows during warm-up).
    """
    new_contacts_per_hour: int
    """
    New conversations the sender may start per hour.
    """
    whatsapp_tier: str | None = None
    """
    WhatsApp only. Meta's messaging tier for the number.
    """


class SenderList(BaseModel):
    """
    A page of senders.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    data: list[Sender]
    has_more: bool
    """
    Whether more items lie beyond this page in the direction you paged.
    """


class SenderRequest(BaseModel):
    """
    A request for a dedicated sender.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    display_name: str | None = None
    """
    The name contacts should see.
    """
    country: str | None = None
    """
    WhatsApp and iMessage. ISO 3166-1 alpha-2 country for the number, for example `IN`.
    """
    telegram_bot_token: str | None = None
    """
    Telegram only, and required there. The bot token from BotFather. Stored encrypted; never returned.
    """


class SenderStatusChangedData(BaseModel):
    """
    The sender as it is now, and what changed.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    sender: Sender
    previous_status: Literal["pending", "active", "warming_up", "throttled", "flagged", "banned"]
    """
    - `pending`: requested, being provisioned.
    - `active`: sending normally.
    - `warming_up`: active, with a new-contact budget that grows day by day.
    - `throttled`: the gate slowed it after an abuse signal; it recovers by itself.
    - `flagged`: the channel or Flow flagged it; starts are paused. A Telegram
      bot is also `flagged` when Telegram rejects its token (revoked in
      @BotFather): it then sends nothing, new sends answer `403 permission`, and
      queued messages wait until you connect the bot again with its new token
      (`POST /v1/senders`). They wait at most 72 hours after Flow accepted
      them; older ones fail with `outside_window` (`channel_code`
      `queued_too_long`) in `message.failed` instead of going out late.
    - `banned`: it cannot send or receive: the channel banned it, you
      disconnected it (`DELETE /v1/senders/{sender_id}`), or its bot or line was
      connected to another app.

    """
    reason: str
    """
    Why, in one sentence (for example "Many new conversations got no reply; starts are slowed for 24 hours").
    """


class SenderStatusChangedEvent(EventBase):
    """
    A sender's status or WhatsApp quality rating changed.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["sender.status_changed"]
    """
    Always `sender.status_changed`.
    """
    data: SenderStatusChangedData


class SignedInUser(BaseModel):
    """
    The person who approved a device sign-in.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    name: str
    """
    Their name or login at the provider.
    """
    email: str | None = None
    """
    Their verified email address, where the provider gave one.
    """
    provider: Literal["github", "google"]
    """
    Where they signed in.
    """


class SimulatedInbound(BaseModel):
    """
    A simulated turn Flow accepted. Its `message.received` event follows.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    message: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    The ID the received message will have, in its `message.received` event and in the transcript.
    """
    conversation: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    channel_message_id: str
    """
    The simulated channel's ID for the message (the received message's `channel_message_id`).
    """
    status: Literal["queued"]
    """
    Always `queued`; the message is stored and delivered right after.
    """


class SimulatedInboundRequest(BaseModel):
    """
    One turn from a simulated contact (test keys only).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    content: Annotated[
        TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent,
        Field(discriminator="type"),
    ]
    """
    What the contact sends: `text`, `media`, `voice`, `location`,
    `contact_card` or `button_reply`. Media and voice take a `file_id` from
    `POST /v1/files`. Other types answer `400 invalid_request`.

    """
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    A message of this conversation the contact replies to inline, on channels with inline replies (Telegram, iMessage; on SMS it answers `400 invalid_request`). The received message shows it in `reply_to`.
    """


class SmsSegments(BaseModel):
    """
    SMS text messages only: how the text travels as SMS. Carriers bill and
    deliver SMS in segments: 160 GSM-7 characters fit one segment (153 each
    when split), but a single character outside GSM-7 (an emoji, curly quotes,
    most non-Latin letters) makes the whole text UCS-2, 70 characters in one
    segment (67 each when split). An SMS send may use at most `max_sms_segments`
    (`GET /v1/capabilities`, 10). Absent on MMS and on other channels.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    segments: int
    """
    How many SMS segments the text takes.
    """
    encoding: Literal["gsm7", "ucs2"]
    """
    `gsm7` or `ucs2`.
    """


class SmsSender(BaseModel):
    """
    SMS senders only: how the number is registered with US carriers and what it
    can do. An SMS number stays `pending` until its registration is approved
    (carriers block traffic from unregistered numbers).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    number_type: Literal["10dlc", "toll_free"]
    """
    `10dlc` (a local 10-digit number, registered as a brand and campaign) or `toll_free` (a verified toll-free number).
    """
    registration_status: Literal["pending", "approved", "rejected"]
    """
    The number's carrier registration (the 10DLC campaign, or toll-free
    verification): `pending` (submitted, not approved yet; the sender is
    `pending` and sends nothing), `approved`, or `rejected` (the sender is
    `flagged`; the Flow team resubmits).

    """
    two_way: bool
    """
    Whether the number receives texts. Always `true` for senders Flow connects today.
    """
    mms: bool
    """
    Whether the number sends and receives MMS (images, audio and video). Without it, `media` and `voice` sends answer `422 unsupported_content`.
    """
    quiet_hours: QuietHours | None = None


class StartConversationRequest(BaseModel):
    """
    The first message from one of your senders to a contact.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    to: Recipient
    content: Annotated[
        TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent,
        Field(discriminator="type"),
    ]
    """
    One piece of content, in either direction. `type` selects the shape. Inbound
    messages use `text`, `media`, `voice`, `button_reply`, `reaction`, `location`,
    `contact_card` and `file_blocked`; sends use every type except `button_reply`
    and `file_blocked`.

    | type | Telegram | WhatsApp | iMessage | SMS (US, pilot) | `fallback: "auto"` |
    |---|---|---|---|---|---|
    | text | yes | yes | yes | yes (at most 10 segments) | markdown to plain |
    | media | yes | yes | yes | images, audio, video as MMS (no documents) | none |
    | voice | yes | yes | yes | as an MMS audio file | audio file |
    | buttons | inline keyboard | up to 3 buttons, else a list | no | no | numbered text |
    | reaction | yes | yes | tapbacks, other emoji as emoji reactions | no | closest tapback, else skipped (SMS: none) |
    | template | no | yes | no | no | none |
    | location | yes | yes | no | no | maps link as text |
    | contact_card | yes | yes | no | no | text |
    | effect | no | no | yes | no | plain text |
    | typing | yes | yes | yes (within 5 minutes of the contact's last message) | no | skipped |
    | read | no (bots) | yes | yes (the whole conversation) | no | skipped |
    | edit | yes | no | yes (within 15 minutes) | no | none |
    | unsend | yes (within 48 hours) | no | yes (within 2 minutes) | no | none |

    """
    fallback: Literal["auto"] | TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent | None = (
        None
    )
    """
    What to send when the channel cannot show `content`. Without it, such a send
    fails with `unsupported_content`; nothing is converted silently.

    - `"auto"`: use the documented default for the content type (markdown becomes
      plain text, buttons become numbered text whose replies are matched back to
      the button IDs, a voice note becomes an audio file, a location becomes a
      maps link, a contact card becomes text, an effect becomes plain text, a
      reaction becomes the closest tapback or is skipped).
    - A `Content` object: send exactly this instead.

    The message's `delivered_as` reports what was used.

    """
    channel_options: ChannelOptions | None = None
    metadata: dict[str, str] | None = None
    consent: Consent | None = None
    """
    SMS. The contact's consent, required when they have never texted any of your SMS numbers; recorded on the contact. Ignored on other channels.
    """


class StreamAckFrame(BaseModel):
    """
    Server to client. A `send` or `start` frame was accepted.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["ack"]
    """
    Always `ack`.
    """
    ref: str
    """
    The `ref` of the frame being answered.
    """
    message: Message


class StreamErrorFrame(BaseModel):
    """
    Server to client. A `send` or `start` frame was refused (with its `ref`), or the stream itself was refused or failed (without `ref`; the server then closes the socket with a 4000-range close code, `4401` for `authentication`, see `GET /v1/stream`).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["error"]
    """
    Always `error`.
    """
    ref: str | None = None
    """
    The `ref` of the frame being answered, if any.
    """
    error: ErrorBody


class StreamEventFrame(BaseModel):
    """
    Server to client. One event from the log.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["event"]
    """
    Always `event`.
    """
    event: Annotated[
        MessageReceivedEvent | MessageSentEvent | MessageDeliveredEvent | MessageReadEvent | MessageFailedEvent | ReactionAddedEvent | ReactionRemovedEvent | TypingStartedEvent | TypingStoppedEvent | ConversationStartedEvent | ConversationWindowClosingEvent | SenderStatusChangedEvent | TemplateStatusChangedEvent | ContactDeletedEvent,
        Field(discriminator="type"),
    ]
    """
    One entry in your app's log. `type` says what happened and selects the shape
    of `data`. `conversation` is set for every event that happened in a
    conversation (all but `sender.status_changed`, `template.status_changed` and
    `contact.deleted`).

    """


class StreamReconnectFrame(BaseModel):
    """
    Server to client. The server is restarting; reconnect with `after` set to the last event you received. The socket closes after this frame.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["reconnect"]
    """
    Always `reconnect`.
    """
    after: Annotated[str | None, Field(examples=["evt_01JB8ZE5N7Q9S1V3X5Z7B9D1E3"])] = (
        None
    )
    """
    An event ID, `evt_` and a ULID.
    """


class StreamSendFrame(BaseModel):
    """
    Client to server. Same as `POST /v1/conversations/{conversation_id}/messages`; `ref` is also the idempotency key.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["send"]
    """
    Always `send`.
    """
    ref: str
    """
    Your ID for this frame, echoed in the answer and used as the idempotency key.
    """
    conversation: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    message: SendMessageRequest


class StreamStartFrame(BaseModel):
    """
    Client to server. Same as `POST /v1/messages`; `ref` is also the idempotency key.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["start"]
    """
    Always `start`.
    """
    ref: str
    """
    Your ID for this frame, echoed in the answer and used as the idempotency key.
    """
    message: StartConversationRequest


class StreamFrame(
    RootModel[
        StreamEventFrame
        | StreamAckFrame
        | StreamErrorFrame
        | StreamReconnectFrame
        | StreamSendFrame
        | StreamStartFrame
    ]
):
    root: Annotated[
        StreamEventFrame | StreamAckFrame | StreamErrorFrame | StreamReconnectFrame | StreamSendFrame | StreamStartFrame,
        Field(discriminator="type"),
    ]
    """
    One JSON frame on the `/v1/stream` WebSocket. The server sends `event`, `ack`,
    `error` and `reconnect`; the client sends `send` and `start`.

    """


class Template(BaseModel):
    """
    A WhatsApp message template, mirrored from Meta with its approval status.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["tpl_01JB8Z9X2D4F6H8K0M2P4R6T8V"])]
    """
    A template ID, `tpl_` and a ULID.
    """
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    name: str
    """
    The template's name at Meta.
    """
    language: str
    """
    The template's language, as Meta names it.
    """
    category: Literal["marketing", "utility", "authentication"]
    """
    Meta's category for the template, which sets its price.
    """
    status: Literal["pending", "approved", "rejected", "paused", "disabled"]
    """
    A template's approval status at Meta.
    """
    components: list[TemplateComponent]
    """
    The template's parts, as submitted.
    """
    rejection_reason: str | None = None
    """
    Meta's reason, when the template was rejected.
    """
    created_at: datetime
    """
    When the template was submitted.
    """


class TemplateButton(BaseModel):
    """
    One button of a template.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["quick_reply", "url", "phone_number"]
    """
    What the button does.
    """
    text: str
    """
    The button's label.
    """
    url: str | None = None
    """
    For `url` buttons, the link, optionally ending in a `{{1}}` placeholder.
    """
    phone: str | None = None
    """
    For `phone_number` buttons, the E.164 number.
    """


class TemplateButtonParam(BaseModel):
    """
    The value for one of the template's buttons.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    index: int
    """
    The button's position in the template, from 0.
    """
    value: str
    """
    The URL suffix or the quick-reply payload.
    """


class TemplateComponent(BaseModel):
    """
    One part of a template. Placeholders are written `{{1}}`, `{{2}}`, ...
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["header", "body", "footer", "buttons"]
    """
    Which part this is.
    """
    format: Literal["text", "image", "video", "document"] | None = None
    """
    For headers, what the header holds.
    """
    text: str | None = None
    """
    The part's text, with placeholders.
    """
    buttons: list[TemplateButton] | None = None
    """
    For `buttons`, the buttons in order.
    """


class TemplateContent(BaseModel):
    """
    A WhatsApp message template, sent only. Required to start a WhatsApp
    conversation or to write after the 24-hour window closed. The template must be
    `approved`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["template"]
    """
    Always `template`.
    """
    template_id: Annotated[str, Field(examples=["tpl_01JB8Z9X2D4F6H8K0M2P4R6T8V"])]
    """
    A template ID, `tpl_` and a ULID.
    """
    language: str
    """
    The template language to use, as Meta names it (`en`, `en_US`, `hi`).
    """
    params: TemplateParams | None = None


class TemplateCreateRequest(BaseModel):
    """
    A template to submit to Meta.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    name: str
    """
    Lowercase letters, digits and underscores.
    """
    language: str
    """
    The template's language, as Meta names it (`en`, `en_US`, `hi`).
    """
    category: Literal["marketing", "utility", "authentication"]
    """
    Meta's category for the template, which sets its price.
    """
    components: list[TemplateComponent]
    """
    The template's parts. A body is required.
    """


class TemplateHeaderParam(BaseModel):
    """
    The value of a template's header, when it has a placeholder or media.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["text", "image", "video", "document"]
    """
    What the header holds.
    """
    text: str | None = None
    """
    For `text` headers, the placeholder's value.
    """
    url: str | None = None
    """
    For media headers, an HTTPS URL of the media.
    """
    file_id: Annotated[str | None, Field(examples=["file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5"])] = (
        None
    )
    """
    A file ID, `file_` and a ULID.
    """


class TemplateList(BaseModel):
    """
    A page of templates.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    data: list[Template]
    has_more: bool
    """
    Whether more items lie beyond this page in the direction you paged.
    """


class TemplateParams(BaseModel):
    """
    Values for the template's placeholders.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    header: TemplateHeaderParam | None = None
    body: list[str] | None = None
    """
    Values for the body's `{{1}}`, `{{2}}`, ... in order.
    """
    buttons: list[TemplateButtonParam] | None = None
    """
    Values for buttons that take one (URL suffixes, quick-reply payloads).
    """


class TemplateStatusChangedData(BaseModel):
    """
    The template as it is now, and what changed.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    template: Template
    previous_status: Literal["pending", "approved", "rejected", "paused", "disabled"]
    """
    A template's approval status at Meta.
    """
    reason: str | None = None
    """
    Meta's reason, when it gives one.
    """


class TemplateStatusChangedEvent(EventBase):
    """
    Meta approved, rejected or paused a template.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["template.status_changed"]
    """
    Always `template.status_changed`.
    """
    data: TemplateStatusChangedData


class TestContactAddress(BaseModel):
    """
    The simulated contact's address on the channel. Give one field that fits the
    channel: `phone` on SMS, iMessage and WhatsApp, `handle` on iMessage,
    `telegram_user_id` on Telegram. Omit `contact` to get a new contact with a made-up address.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    phone: str | None = None
    """
    SMS, iMessage or WhatsApp. E.164 phone number; on SMS a US number (`+1` and ten digits).
    """
    handle: str | None = None
    """
    iMessage. A phone number or an email address.
    """
    telegram_user_id: str | None = None
    """
    Telegram. A numeric user ID.
    """


class TestConversationRequest(BaseModel):
    """
    A simulated conversation to create (test keys only).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    The channel to simulate. `telegram`, `whatsapp`, `imessage` or `sms`.
    """
    contact: TestContactAddress | None = None
    name: str | None = None
    """
    The simulated contact's display name, as a channel would report it.
    """


class TestTranscript(BaseModel):
    """
    A page of a simulated conversation, both directions, oldest first.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    conversation: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    data: list[TranscriptEntry]
    has_more: bool
    """
    Whether more messages follow; page on with `after` set to the last message's ID.
    """


class TextContent(BaseModel):
    """
    Text, both ways. With `format` `markdown`, Flow renders it in each channel's own formatting; a channel without formatting needs `fallback`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["text"]
    """
    Always `text`.
    """
    text: str
    """
    The text, at most the channel's `max_text_length` characters (4096 on Telegram and WhatsApp, 9999 on iMessage, 1530 on SMS, where it must also fit in 10 segments, 670 characters when it holds an emoji or other character outside GSM-7; see `GET /v1/capabilities`). Telegram counts UTF-16 code units of the text as shown (after markdown), so an emoji such as 😀 counts as 2. In an edit of a media message the text replaces its caption, and the caption limit applies (1024). Longer text is refused with `invalid_request`.
    """
    format: Literal["plain", "markdown"] | None = "plain"
    """
    How to read `text`. `markdown` is CommonMark (`**bold**`, `*italic*`); Flow converts it to each channel's marks. `plain` is sent as written, so a channel's own marks (WhatsApp's `*bold*`) work with `plain`. Inbound text is always `plain`.
    """


class Timing(BaseModel):
    """
    When the event moved through Flow, to measure Flow's overhead
    (`delivered_at` minus `received_at`).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    received_at: datetime
    """
    When Flow received it from the channel, or when it happened inside Flow.
    """
    stored_at: datetime
    """
    When it was committed to the log.
    """
    delivered_at: datetime | None = None
    """
    When the event went out to a webhook endpoint. Its value depends on
    where you read it. In a webhook delivery's body, it is when that delivery
    attempt started (each attempt to each endpoint gets its own), unless an
    endpoint had already accepted the event, in which case it is that
    acceptance time. In the event log (`GET /v1/events`,
    `GET /v1/events/{event_id}`, the stream), it is when the first endpoint
    accepted the event, and it is absent until one has (always, for an app
    with no webhook endpoints).

    """


class TranscriptEntry(Message):
    """
    One message of a simulated conversation: the `Message`, plus `shown` for a
    sent message.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    shown: Annotated[
        TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent | None,
        Field(discriminator="type"),
    ] = None
    """
    Sent messages only: what the simulated contact sees, after the send gate
    applied any fallback (the same as `content` when it was shown as sent).
    Absent for received messages, for messages not sent yet or failed, and
    when nothing was shown (`delivered_as.type` `none`, such as typing on
    SMS).

    """


class TypingContent(BaseModel):
    """
    The typing indicator, sent only (the stream's and webhook replies' way to type; over HTTP use `POST /v1/conversations/{conversation_id}/typing`). Skipped where the channel has none.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["typing"]
    """
    Always `typing`.
    """
    state: Literal["on", "off"]
    """
    `on` shows the indicator, `off` clears it.
    """


class TypingEventData(BaseModel):
    """
    Who is typing.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    contact: Annotated[str, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])]
    """
    A contact ID, `ct_` and a ULID.
    """


class TypingRequest(BaseModel):
    """
    Turn the typing indicator on or off.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    state: Literal["on", "off"]
    """
    `on` shows the indicator, `off` clears it.
    """


class TypingStartedEvent(EventBase):
    """
    The contact started typing, where the channel reports it.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["typing.started"]
    """
    Always `typing.started`.
    """
    data: TypingEventData


class TypingStoppedEvent(EventBase):
    """
    The contact stopped typing, where the channel reports it.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["typing.stopped"]
    """
    Always `typing.stopped`.
    """
    data: TypingEventData


class UnsendContent(BaseModel):
    """
    Removes one of your sent messages from the contact's chat, sent only (over HTTP use `DELETE /v1/messages/{message_id}`). Telegram and iMessage; WhatsApp refuses it with `unsupported_content`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["unsend"]
    """
    Always `unsend`.
    """
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """


class UrlButton(BaseModel):
    """
    A button that opens a link.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    url: str
    """
    The HTTPS link to open.
    """
    label: str
    """
    The button's text.
    """


class VoiceContent(BaseModel):
    """
    A voice note, both ways. Inbound voice notes always come with the audio file
    (`url`, `file_id`) and, when the app has transcription on, a `transcript`.
    When sending, give `url` or `file_id` of an audio file; channels without
    voice notes need `fallback` (`auto` sends it as an audio file).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["voice"]
    """
    Always `voice`.
    """
    url: str | None = None
    """
    Where the audio is. Sending, an HTTPS URL Flow can fetch; inbound, a Flow file URL.
    """
    file_id: Annotated[str | None, Field(examples=["file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5"])] = (
        None
    )
    """
    A file ID, `file_` and a ULID.
    """
    duration_seconds: float | None = None
    """
    The voice note's length.
    """
    transcript: str | None = None
    """
    Inbound only, when transcription is on. What was said.
    """


class WebhookEndpoint(BaseModel):
    """
    A URL that receives your app's events of the types it subscribes to.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["we_01JB8ZF6P8R0T2W4Y6A8C0E2F4"])]
    """
    A webhook endpoint ID, `we_` and a ULID.
    """
    url: str
    """
    The HTTPS URL events are posted to.
    """
    events: list[Literal["message.received", "message.sent", "message.delivered", "message.read", "message.failed", "reaction.added", "reaction.removed", "typing.started", "typing.stopped", "conversation.started", "conversation.window_closing", "sender.status_changed", "template.status_changed", "contact.deleted"]]
    """
    The event types delivered to this endpoint.
    """
    description: str | None = None
    """
    Your note about the endpoint.
    """
    enabled: bool
    """
    Whether events are delivered. Disabled endpoints keep their place; nothing is lost from the log.
    """
    livemode: bool
    """
    Whether the endpoint receives live-mode or test-mode events.
    """
    secret: str | None = None
    """
    The signing secret (`whsec_...`). Only in the answers to create and to rotate the secret.
    """
    previous_secret_expires_at: datetime | None = None
    """
    While a secret rotation overlaps, when the previous secret stops signing. Absent when only one secret is active.
    """
    created_at: datetime
    """
    When the endpoint was created.
    """


class WebhookEndpointCreateRequest(BaseModel):
    """
    A new webhook endpoint.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    url: str
    """
    An HTTPS URL on a public address.
    """
    events: list[Literal["message.received", "message.sent", "message.delivered", "message.read", "message.failed", "reaction.added", "reaction.removed", "typing.started", "typing.stopped", "conversation.started", "conversation.window_closing", "sender.status_changed", "template.status_changed", "contact.deleted"]]
    """
    The event types to deliver.
    """
    description: str | None = None
    """
    Your note about the endpoint.
    """


class WebhookEndpointList(BaseModel):
    """
    A page of webhook endpoints.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    data: list[WebhookEndpoint]
    has_more: bool
    """
    Whether more items lie beyond this page in the direction you paged.
    """


class WebhookEndpointUpdateRequest(BaseModel):
    """
    Changes to a webhook endpoint. Fields left out are kept.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    url: str | None = None
    """
    An HTTPS URL on a public address.
    """
    events: list[Literal["message.received", "message.sent", "message.delivered", "message.read", "message.failed", "reaction.added", "reaction.removed", "typing.started", "typing.stopped", "conversation.started", "conversation.window_closing", "sender.status_changed", "template.status_changed", "contact.deleted"]] | None = (
        None
    )
    """
    The event types to deliver.
    """
    description: str | None = None
    """
    Your note about the endpoint.
    """
    enabled: bool | None = None
    """
    Whether to deliver events.
    """


class WebhookReply(BaseModel):
    """
    The optional body of your answer to a `message.received` delivery. `reply` is
    one piece of content or a list of up to 10, sent in order into the event's
    conversation through the send gate. A non-empty string, as `reply` or as an
    item of the list, is text: `{"reply": "Hi"}` is short for
    `{"reply": {"type": "text", "text": "Hi"}}`. Leave `reply` out, set it to `null`, or
    answer `{}`, an empty body or any body that is not a JSON object (such as
    `OK`) to send nothing now; that is not an error.

    A JSON object whose `reply` (or `fallback`, alongside a `reply`) does not match
    this shape, or a body that starts with `{` but is not valid JSON, sends
    nothing at all (no piece of a list goes out) and is recorded on the delivery as an `invalid_request` error
    with the reason; the delivery counts as delivered and is not retried.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    reply: str | list[str | TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent] | TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent | None = (
        None
    )
    """
    One piece of content, or a list of 1 to 10 pieces sent in order. A non-empty string is text content. `null` sends nothing.
    """
    fallback: Literal["auto"] | TextContent | MediaContent | VoiceContent | ButtonsContent | ButtonReplyContent | ReactionContent | TemplateContent | LocationContent | ContactCardContent | EffectContent | TypingContent | ReadContent | EditContent | UnsendContent | FileBlockedContent | None = (
        None
    )
    """
    What to send when the channel cannot show a piece of `reply`, as on HTTP sends. It applies to every piece.
    """


class WebhookSecretRotateRequest(BaseModel):
    """
    Options for rotating a webhook endpoint's signing secret.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    overlap_seconds: int | None = 86400
    """
    How long the previous secret keeps signing alongside the new one, in seconds (at most 7 days). `0` retires it at once.
    """


class WindowClosingData(BaseModel):
    """
    When the window closes.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    window_open_until: datetime
    """
    After this time only templates can be sent.
    """


class WindowState(BaseModel):
    """
    Whether free-form messages can be sent now.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    open: bool
    """
    `true` when any content can be sent; `false` when only a `template` can (WhatsApp after 24 hours).
    """
    open_until: datetime | None = None
    """
    WhatsApp only. When the window closes, if it is open.
    """
