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
    plan: Literal["free", "shared", "dedicated", "pro", "business", "enterprise"]
    """
    The account's plan, bought by the workspace owner in the Flow dashboard
    (`https://flow.engineer/dashboard/plans`; `GET /v0/app`'s `plans` lists
    what is on sale, with prices). Each plan
    caps how many people your apps may talk with per channel; `people`
    shows the caps and what is used. Replies count: a person your app
    replies to is one of the people counted.

    - `free`: the free trial, 25 people per channel across all the account's
      apps (not per day or month).
    - `shared`: Flow's shared senders, with caps per channel a day and a
      month (200 a day and 300 a month today).
    - `dedicated`: your own iMessage line, with a daily cap on it and no
      monthly cap (1,000 people a day today; a new line starts at 250 a
      day and ramps to 1,000 over its first 14 days); on Flow's shared
      senders it has `shared`'s caps, counted apart (`people` shows each
      `pool`).

    The numbers are settings and may change; read the caps that apply
    now from `people`, not from this list.
    - `pro`, `business`, `enterprise`: older plans, kept for accounts that
      have them; they have no people caps.

    New values may be added; treat one you do not know like `free`.

    """
    people: PeopleLimits | None = None
    hipaa: bool | None = None
    """
    `true` when the account is marked as handling protected health
    information. Its messages then go only through the channels this
    setting allows (SMS): sends, typing,
    read receipts and sender connections on Telegram, WhatsApp and iMessage
    answer `403 permission` with `channel_code` `hipaa_channel_not_covered`,
    and messages already queued there fail the same way. The sandbox
    senders answer the account's contacts with a fixed refusal and store
    and deliver nothing they send; turning the flag on ends the account's
    sandbox joins. Only SMS can be simulated (`POST /v0/test/conversations`):
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
    `POST /v0/sandbox/keys` (7 days after it was made); signing in through the
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
    The app's sandbox join code on its own: two words and eight digits, for example `brave-otter-40718263`. A contact joins this app by sending a shared sandbox sender the join message, which ends with this code in brackets after `ref` (`Hi Sandbox app (ref brave-otter-40718263)`), or on Telegram by opening the bot's link with the code (`https://t.me/<bot>?start=brave-otter-40718263`, which sends `/start brave-otter-40718263`). Each shared sender's `join_code` gives the whole message: show that to testers, not this code.

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
    plans: PlanCatalog | None = None


class AppSettings(BaseModel):
    """
    Per-app behaviour. The Flow team sets it for now; ask them to change it.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    transcription: bool
    """
    On by default. When on, Flow transcribes the voice notes your app receives on
    WhatsApp, Telegram and simulated senders, and on iMessage when iMessage made no
    transcript of its own, and puts the text in the voice content's `transcript`
    (`transcript_source` `flow`) before it delivers `message.received`. Both modes
    are covered, within Flow's limits: a voice note longer than 10 minutes, or one
    past the app's 4 hours of transcribed audio a day (UTC), arrives without a
    transcript. Off, voice notes arrive with the audio only; on iMessage a voice
    note still carries the transcript iMessage made of it, whatever this setting
    says. Audio files sent as `basic` media and videos are never transcribed.

    """
    auto_read: bool
    """
    When on, Flow marks inbound messages as read as soon as your endpoint accepts them.
    """


class BasicImessageOptions(BaseModel):
    """
    iMessage only: styles and a subject line. On another channel the block
    answers `422 unsupported_content` with `param` `imessage`; an unknown key
    `400 invalid_request`. A message that goes by SMS or RCS (see
    `Message.network`) shows neither.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    styles: list[ImessageStyle] | None = None
    """
    Styled ranges of `text` (see `ImessageStyle`). Each range must lie within `text`; one that does not answers `400 invalid_request` naming it (`imessage.styles[0]`).
    """
    subject: str | None = None
    """
    iMessage's subject line, shown in bold above the text.
    """


class BasicMessage(BaseModel):
    """
    Text, or one media file with an optional caption, in either direction: the
    kind every channel takes (`POST /v0/conversations/{conversation_id}/basic`).
    Give `text`, `media`, or both (then `text` is the caption). A field not
    listed here is refused with `400 invalid_request` naming it in `param`;
    a field or channel block the conversation's channel does not take answers
    `422 unsupported_content` naming it.

    Received from a contact: their text and/or one file. Inbound media always
    has `url` (a Flow file URL, `GET /v0/files/{file_id}`) and `file_id`, on
    every channel (an SMS contact's MMS files included), and `mime_type` and
    `size_bytes` once Flow kept the file; send a received file again by its
    `file_id`. On SMS Flow always keeps its own copy (the provider's is
    deleted): an MMS file it could not fetch or check arrives as
    `file_blocked` instead.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["basic"] = "basic"
    """
    Always `basic`. Optional on `POST /v0/conversations/{conversation_id}/basic`; required where no URL names the kind (webhook replies, the stream, starts, a message's `content`).
    """
    text: str | None = None
    """
    The text, sent exactly as written: no markdown, no stripping. At most
    4096 UTF-16 code units on Telegram (an emoji such as 😀 counts as 2),
    4096 characters on WhatsApp, 9999 on iMessage, and 10 segments on SMS
    (see `SmsSegments`). With `media` it is the caption, at most 1024 (UTF-16
    code units on Telegram). Optional when `media` is given. Longer text is
    refused with `400 invalid_request`.

    """
    media: Media | None = None
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as an inline reply to an earlier message in the same
    conversation (Telegram, WhatsApp and iMessage show it quoted). SMS has no
    inline replies: there it answers `422 unsupported_content` with `param`
    `reply_to`. Refused with `404 not_found` (`param` `reply_to`) when the
    target is not a message in this conversation, and with `400
    invalid_request` (`param` `reply_to`) when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    link_preview: bool | None = None
    """
    Whether links in the text show a rich preview. Left out, the channel's
    default applies (Telegram, WhatsApp and iMessage show previews).
    `false` sends links as plain text. SMS never shows previews, and no
    channel shows one on a media message: `false` is accepted there, and
    `true` on SMS or with `media` answers `422 unsupported_content` with
    `param` `link_preview`.

    """
    telegram: BasicTelegramOptions | None = None
    imessage: BasicImessageOptions | None = None
    metadata: dict[str, str] | None = None


class BasicKind(BasicMessage):
    """
    A `basic` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`BasicMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["basic"]
    """
    Always `basic`. Optional on `POST /v0/conversations/{conversation_id}/basic`; required where no URL names the kind (webhook replies, the stream, starts, a message's `content`).
    """


class BasicTelegramOptions(BaseModel):
    """
    Telegram only: how the message looks and notifies on Telegram. On another
    channel the block answers `422 unsupported_content` with `param`
    `telegram`; an unknown key `400 invalid_request`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    parse_mode: Literal["HTML", "MarkdownV2"] | None = None
    """
    How Telegram reads the text: `HTML` or `MarkdownV2`, Telegram's own
    formatting (see Telegram's Bot API, "Formatting options"). Without it the
    text is plain. Text that Telegram cannot parse is refused by Telegram:
    the message fails (`message.failed`, `channel_error`).

    """
    disable_notification: bool | None = None
    """
    Deliver silently, with no sound.
    """
    protect_content: bool | None = None
    """
    Stop the contact forwarding or saving the message.
    """
    show_caption_above_media: bool | None = None
    """
    Media only. Show the caption above the photo or video instead of below it.
    """
    has_spoiler: bool | None = None
    """
    Media only (photos and videos). Cover it with a spoiler animation until tapped.
    """


class ButtonReplyMessage(BaseModel):
    """
    Inbound only. The contact tapped a reply button of a buttons or carousel message, or a row of a list.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["button_reply"]
    """
    Always `button_reply`.
    """
    button_id: str
    """
    The `id` of the tapped button or list row.
    """
    label: str
    """
    The tapped button's label, or the list row's title.
    """
    message_id: Annotated[
        str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])
    ] = None
    """
    A message ID, `msg_` and a ULID.
    """


class ButtonsMessage(BaseModel):
    """
    Text with buttons, sent only (`POST
    /v0/conversations/{conversation_id}/buttons`), optionally under a
    `header`. A tap on a reply button arrives as a `button_reply` message
    carrying the button's `id`. URL buttons open a link and send nothing back.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["buttons"] = "buttons"
    """
    Always `buttons`. Optional on its endpoint; required where no URL names the kind.
    """
    header: ContentHeader | None = None
    text: str
    """
    The text above the buttons, sent exactly as written: at most 4096 UTF-16
    code units on Telegram, or 1024 when the message has a media `header`
    (Telegram's caption limit), and 1024 characters on WhatsApp (its limit
    for messages with buttons). Longer text is refused with `400
    invalid_request`.

    """
    buttons: list[ReplyButton | UrlButton]
    """
    The buttons, in order: 1 to 10 on Telegram; on WhatsApp 1 to 3 reply
    buttons or exactly one URL button (anything else answers `422
    unsupported_content` with `param` `buttons`; send a `list` for more
    choices).

    """
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as an inline reply to an earlier message in the same
    conversation (Telegram, WhatsApp and iMessage show it quoted). SMS has no
    inline replies: there it answers `422 unsupported_content` with `param`
    `reply_to`. Refused with `404 not_found` (`param` `reply_to`) when the
    target is not a message in this conversation, and with `400
    invalid_request` (`param` `reply_to`) when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    telegram: ButtonsTelegramOptions | None = None
    metadata: dict[str, str] | None = None


class ButtonsKind(ButtonsMessage):
    """
    A `buttons` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`ButtonsMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["buttons"]
    """
    Always `buttons`. Optional on its endpoint; required where no URL names the kind.
    """


class ButtonsTelegramOptions(BaseModel):
    """
    Telegram only: how the message looks and notifies on Telegram. On another
    channel the block answers `422 unsupported_content` with `param`
    `telegram`; an unknown key `400 invalid_request`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    parse_mode: Literal["HTML", "MarkdownV2"] | None = None
    """
    How Telegram reads the text: `HTML` or `MarkdownV2`, Telegram's own
    formatting (see Telegram's Bot API, "Formatting options"). Without it the
    text is plain. Text that Telegram cannot parse is refused by Telegram:
    the message fails (`message.failed`, `channel_error`).

    """
    disable_notification: bool | None = None
    """
    Deliver silently, with no sound.
    """
    protect_content: bool | None = None
    """
    Stop the contact forwarding or saving the message.
    """


class Call(BaseModel):
    """
    One call attempt to an iMessage line.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    contact: Annotated[str, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])]
    """
    The contact who called.
    """
    network: Literal["facetime"]
    """
    How they called. `facetime` (a FaceTime call) today.
    """


class CallData(BaseModel):
    """
    The call the contact tried to make.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    call: Call


class CallForwarding(BaseModel):
    """
    Dedicated lines only, where it is included: where phone calls to the
    line's number are forwarded, set up with the Flow team. Forwarded calls
    send no event.
    FaceTime calls are not forwarded; they arrive as `call.received`. Absent
    when calls are not forwarded (always on shared lines).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    phone: Annotated[str, Field(examples=["+15555550123"])]
    """
    The E.164 number calls are forwarded to.
    """


class CarouselCard(BaseModel):
    """
    One card of a carousel.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    header: ContentHeader
    """
    The card's image or video, a `ContentHeader` of type `image` or `video` only (by `url` or `file_id`); any other type is refused with `400 invalid_request` at `cards[i].header.type`.
    """
    text: str | None = None
    """
    The card's text, at most 160 characters and 2 line breaks.
    """
    buttons: list[ReplyButton | UrlButton]
    """
    Exactly one URL button, or 1 to 2 reply buttons; the same number and kind on every card. Labels are at most 20 characters.
    """


class CarouselMessage(BaseModel):
    """
    A row of 2 to 10 cards the contact scrolls sideways, under one text, sent
    only (`POST /v0/conversations/{conversation_id}/carousel`; WhatsApp). Each
    card has an image or video, optional text, and its own buttons. A tap on a
    reply button arrives as a `button_reply` message carrying the button's
    `id`; URL buttons open a link and send nothing back. Every card has the
    same number and kind of buttons; a card has either exactly one URL button
    or 1 to 2 reply buttons; reply button `id`s are unique across the
    carousel. Each rule is refused with `400 invalid_request` when broken.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["carousel"] = "carousel"
    """
    Always `carousel`. Optional on its endpoint; required where no URL names the kind.
    """
    text: str
    """
    The message text shown above the cards, 1 to 1024 characters. Longer text is refused with `400 invalid_request`.
    """
    cards: list[CarouselCard]
    """
    2 to 10 cards, in the order shown (left to right).
    """
    metadata: dict[str, str] | None = None


class CarouselKind(CarouselMessage):
    """
    A `carousel` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`CarouselMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["carousel"]
    """
    Always `carousel`. Optional on its endpoint; required where no URL names the kind.
    """


class ChannelPeople(BaseModel):
    """
    The caps on people for one channel and one pool of senders, and how many
    people are held. A channel can appear twice, once per pool, since each
    pool is counted apart (a `dedicated` account has `shared`'s caps on Flow's
    shared senders and its own cap on its own line).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    channel: Literal["telegram", "whatsapp", "imessage", "sms"] | None = None
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    pool: Literal["shared", "own"]
    """
    `shared`: Flow's shared senders on this channel. `own`: the account's own senders on it (a dedicated line, its own bot or number). Counted apart.
    """
    limits: list[PeopleWindow]
    """
    Each window the plan caps (`free`: `total`; `shared`: `day` and `month`; `dedicated`: `day`).
    """
    held: int
    """
    People held now because a cap is reached; their messages wait and are delivered when a place frees or the window rolls over.
    """


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
    `true` for a simulated contact, who exists only inside Flow (test mode only, from `POST /v0/test/conversations`); absent otherwise.
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


class ContactCardMessage(BaseModel):
    """
    A contact card, in either direction (`POST
    /v0/conversations/{conversation_id}/contact-card` sends one; Telegram and
    WhatsApp). Inbound, a card the contact shared.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["contact_card"] = "contact_card"
    """
    Always `contact_card`. Optional on its endpoint; required where no URL names the kind.
    """
    name: str
    """
    The person's or business's name.
    """
    phones: list[str] | None = None
    """
    Phone numbers, E.164 where known. Telegram needs at least one (else `422 unsupported_content`, `param` `phones`).
    """
    emails: list[str] | None = None
    """
    Email addresses.
    """
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as an inline reply to an earlier message in the same
    conversation (Telegram, WhatsApp and iMessage show it quoted). SMS has no
    inline replies: there it answers `422 unsupported_content` with `param`
    `reply_to`. Refused with `404 not_found` (`param` `reply_to`) when the
    target is not a message in this conversation, and with `400
    invalid_request` (`param` `reply_to`) when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    metadata: dict[str, str] | None = None


class ContactCardKind(ContactCardMessage):
    """
    A `contact_card` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`ContactCardMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["contact_card"]
    """
    Always `contact_card`. Optional on its endpoint; required where no URL names the kind.
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


class ContactLeftData(BaseModel):
    """
    The contact who left, the shared sender they left, and why.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    contact: Annotated[str, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])]
    """
    A contact ID, `ct_` and a ULID.
    """
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    reason: Literal["joined_other_app"]
    """
    Why the contact left. `joined_other_app`: they sent the join message of
    another app on the shared sender, or of your app's other mode (test or live).

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


class ContentHeader(BaseModel):
    """
    What is shown above a buttons message's text, or a carousel card's image or
    video: an image, a video, a document or a short title. A media header
    takes exactly one of `url` (an HTTPS URL Flow fetches) or `file_id` (from
    `POST /v0/files`), and is fetched and checked for the channel like a basic
    message's `media` (so WebP and other formats work); a `text` header takes
    `text`. Anything else, or a value over a limit, is refused with `400
    invalid_request` naming the field in `param`.

    WhatsApp shows the header at the top of the same message bubble. Telegram
    sends one message: the media with the text as its caption and the buttons
    under it; a `text` header is the message's first line, in bold.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["image", "video", "document", "text"]
    """
    What the header holds.
    """
    url: str | None = None
    """
    Media headers only. An HTTPS URL of the media, which Flow fetches.
    """
    file_id: Annotated[str | None, Field(examples=["file_01JB8ZG7Q9S1V3X5Z7B9D1F3G5"])] = (
        None
    )
    """
    A file ID, `file_` and a ULID.
    """
    text: str | None = None
    """
    `text` headers only. The title, 1 to 60 characters (WhatsApp's header limit).
    """
    filename: str | None = None
    """
    `document` headers only. The file's name, shown with the document.
    """


class Conversation(BaseModel):
    """
    One sender talking with one contact (`type` `direct`), or with an iMessage
    group chat (`type` `group`). Holds the window state and whether the contact
    opted in.

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
    type: Literal["direct", "group"] | None = "direct"
    """
    Flow always sends it; read a missing one as `direct` (answers from
    before groups existed). `direct`: one sender and one contact (every
    channel). `group`: a group chat
    one of your dedicated iMessage lines was added to; it has `group` and no
    `contact`. Flow's shared iMessage line ignores group chats, so they never
    reach your app from it.

    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    contact: Annotated[str | None, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])] = (
        None
    )
    """
    The contact the conversation is with. Always set when `type` is `direct`; absent on group conversations (each message's `from` says who wrote).
    """
    group: Group | None = None
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
    Whether the contact has agreed to receive messages (wrote first, joined the sandbox, or you recorded consent). Always `true` on group conversations, which begin with the group writing.
    """
    simulated: bool | None = None
    """
    `true` for a simulated conversation, whose contact exists only inside Flow (test mode only, from `POST /v0/test/conversations`); absent otherwise.
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
    action: Literal["typing", "read"]
    """
    Which action the channel took. `typing` (the indicator was shown) or `read` (the read receipt was sent).
    """


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
    The conversation an event happened in, inlined so most handlers need no extra call. A group's participants are not inlined; read the conversation for them.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: Annotated[str, Field(examples=["conv_01JB8ZC3K5M7P9R1T3V5X7Z9B1"])]
    """
    A conversation ID, `conv_` and a ULID.
    """
    type: Literal["direct", "group"] | None = "direct"
    """
    Flow always sends it; read a missing one as `direct` (answers from
    before groups existed). `direct`: one sender and one contact (every
    channel). `group`: a group chat
    one of your dedicated iMessage lines was added to; it has `group` and no
    `contact`. Flow's shared iMessage line ignores group chats, so they never
    reach your app from it.

    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"]
    """
    A messaging channel. `sms` is US SMS and MMS (in pilot), from dedicated numbers only.
    """
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    contact: Annotated[str | None, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])] = (
        None
    )
    """
    The contact the conversation is with. Always set when `type` is `direct`; absent on group conversations (the message's `from` says who wrote).
    """
    group_name: str | None = None
    """
    Group conversations only. The group chat's name, when it has one.
    """
    window_open_until: datetime | None = None
    """
    WhatsApp only. Until when free-form messages may be sent. Absent when closed or not applicable.
    """
    simulated: bool | None = None
    """
    `true` for a simulated conversation, whose contact exists only inside Flow (test mode only, from `POST /v0/test/conversations`); absent otherwise.
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
    `inbound` (the contact wrote first), `sandbox_join` (they sent your app's join message or opened its Telegram link) or `outbound` (you started it).
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


class DeviceAuthorization(BaseModel):
    """
    A device sign-in waiting for a person to approve it in a browser.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    device_code: Annotated[str, Field(examples=["fdc_..."])]
    """
    The secret you poll `POST /v0/device/token` with. Never show it to the person.
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
    Seconds to wait between polls of `POST /v0/device/token`.
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
    The `claim_token` from `POST /v0/sandbox/keys`, to claim that app when the person approves.
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
    The `device_code` from `POST /v0/device/authorizations`.
    """


class EditImessageOptions(BaseModel):
    """
    iMessage only. Styles for the new text. An unknown key is refused with `400 invalid_request`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    styles: list[ImessageStyle] | None = None
    """
    Styled ranges of the new `text` (see `ImessageStyle`).
    """


class EditMessageRequest(BaseModel):
    """
    The new text of a sent message (`PATCH /v0/messages/{message_id}`), sent
    exactly as written. A field not listed here is refused with `400
    invalid_request` naming it in `param`; a channel block for another channel
    answers `422 unsupported_content` with `param` the block's name.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    text: str
    """
    The new text: at most 4096 UTF-16 code units on Telegram (1024 when it
    replaces a media message's caption) and 9999 characters on iMessage.
    Longer text is refused with `400 invalid_request`.

    """
    telegram: EditTelegramOptions | None = None
    imessage: EditImessageOptions | None = None


class EditMessage(EditMessageRequest):
    """
    A change to the text of one of your sent messages, as a kind: a piece of a
    webhook reply or on the stream, and the `content` of the message that
    carries an edit (`PATCH /v0/messages/{message_id}` over HTTP, whose rules
    apply). `message_id` names the message to change.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["edit"]
    """
    Always `edit`.
    """
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """


class EditTelegramOptions(BaseModel):
    """
    Telegram only. How Telegram reads the new text. An unknown key is refused with `400 invalid_request`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    parse_mode: Literal["HTML", "MarkdownV2"] | None = None
    """
    How Telegram reads the text: `HTML` or `MarkdownV2`, Telegram's own
    formatting (see Telegram's Bot API, "Formatting options"). Without it the
    text is plain. Text that Telegram cannot parse is refused by Telegram:
    the message fails (`message.failed`, `channel_error`).

    """


class EffectMessage(BaseModel):
    """
    Text sent with an iMessage effect, sent only (`POST /v0/conversations/{conversation_id}/effect`; iMessage). Which effects a contact's device shows may vary.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["effect"] = "effect"
    """
    Always `effect`. Optional on its endpoint; required where no URL names the kind.
    """
    text: str
    """
    The text, sent exactly as written, at most 9999 characters. Longer text is refused with `400 invalid_request`.
    """
    effect: Literal["slam", "loud", "gentle", "invisible_ink", "echo", "spotlight", "balloons", "confetti", "love", "lasers", "fireworks", "celebration"]
    """
    The effect.
    """
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as an inline reply to an earlier message in the same
    conversation (Telegram, WhatsApp and iMessage show it quoted). SMS has no
    inline replies: there it answers `422 unsupported_content` with `param`
    `reply_to`. Refused with `404 not_found` (`param` `reply_to`) when the
    target is not a message in this conversation, and with `400
    invalid_request` (`param` `reply_to`) when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    metadata: dict[str, str] | None = None


class EffectKind(EffectMessage):
    """
    An `effect` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`EffectMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["effect"]
    """
    Always `effect`. Optional on its endpoint; required where no URL names the kind.
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
    - `authentication` (401): the API key is missing, malformed, unknown, revoked or expired. An `Authorization: Bearer` header with nothing after it usually means the environment variable holding the key was empty when the header was built (for an MCP client, when the server was added): the `hint` says so. Send `Authorization: Bearer fk_test_...` or `fk_live_...` with a current key; with no key at all, get a test key with `POST /v0/sandbox/keys`. A sandbox key past its `expires_at` has `channel_code` `sandbox_key_expired`: sign in to claim the app, or get a new key.
    - `permission` (403): the key may not do this, for example a test key using a live sender, a sandbox contact who joined another app, a new conversation from an iMessage line that may only reply, or a send past the app's sandbox allowance (`channel_code` `sandbox_allowance_used`, `sandbox_contact_limit` or `sandbox_channel_not_included`). Use the key of the right mode, have the contact send your join message, wait for the contact to message the line first, or sign in through the device flow to lift the allowance. On SMS: `contact_opted_out` (the contact texted STOP; nothing more goes to them until they text START), `consent_required` (a start to someone who never texted your numbers: record their consent with `consent` on the start). In a HIPAA account: `hipaa_channel_not_covered` (the account's HIPAA setting does not allow the channel; use SMS). Simulated conversations: `simulated_contact` (a real sender was pointed at a simulated contact; reply in the contact's simulated conversation), `not_simulated` (a simulated sender or test endpoint was pointed at a real contact), `test_mode_only`, `simulated_conversation_limit`. In `message.failed`: `sandbox_contact_left` (the contact joined another app on the sandbox sender while the message was queued; have them send your join message again).
    - `not_found` (404): no such object for this app and mode. Check the ID's prefix and that it was made with a key of the same mode (test and live data are separate).
    - `idempotency_conflict` (409): the idempotency key was used for a different request (`channel_code` `body_mismatch`: use a new key), or that request is still running (`in_progress`: wait `retry_after` seconds and repeat it with the same key), or it already created a secret that is shown only once (`secret_not_kept`: creating a webhook endpoint, rotating its secret, connecting a WhatsApp number; a secret that was lost must be rotated again, and a WhatsApp number connected again to see its verify token).
    - `outside_window` (409, or in `message.failed`): the channel will not deliver outside its conversation window. On WhatsApp the 24-hour window is closed: send a template (`POST /v0/conversations/{conversation_id}/template`, or `POST /v0/messages` with `kind` `template` to start), or wait for the contact to write. On iMessage the contact has not messaged the line (or opted in) yet, so the failure arrives as a `message.failed` event: wait for the contact to write, then reply in that conversation. iMessage has no 24-hour window: once someone has texted your line, your agent can message them any time. Typing and read receipts answer `409 outside_window` directly when the channel's window for them is closed; ignore it and send your reply. On iMessage typing and read receipts work only in a two-way conversation, for 5 minutes after your line's last message to the contact, so send your reply first. On WhatsApp read receipts go at any time. On SMS, `channel_code` `quiet_hours`: the contact has not texted in the last hour and it is inside the sender's quiet hours in their time zone; retry after `retry_after` seconds, or wait for them to text. In `message.failed`: `window_closed` (WhatsApp's 24-hour window closed while the message was queued; send a template) and `queued_too_long` (the message waited in the queue longer than its sender allows, for example while the sender was paused; send it again if it still applies).
    - `unsupported_content` (422): the conversation's channel does not take this kind, field, block or value, and nothing was sent; Flow never converts a message. `param` names what was refused: `kind` (the endpoint's kind is not on this channel, such as a carousel on Telegram), a field or block (`reply_to` on SMS, `telegram` on WhatsApp, `telegram.is_big`), or the field whose value is not taken (`emoji` outside Telegram's reaction emoji, `buttons` for more than 3 WhatsApp buttons). `channel` is the conversation's channel and `hint` says what to send instead over plain HTTP; each endpoint's page lists its channels. In an iMessage group conversation, a reaction, typing or a read receipt answers it with `param` `kind` and `channel_code` `group_unsupported`: leave it out. Removing a reaction on iMessage (`emoji` `null`) when you have none on the message answers it with `param` `emoji` and `channel_code` `no_reaction_to_remove`: iMessage removes a reaction by naming it. Media to an SMS number without MMS answers it with `param` `media` and `channel_code` `no_mms`. An edit or unsend of an iMessage message that went by SMS or RCS (its `network`) answers it with `channel_code` `not_on_sms`: send a new message instead. An edit or unsend past the channel's time limit answers it with `channel_code` `edit_window_closed` or `unsend_window_closed` (iMessage: edits within 15 minutes of sending, unsends within 2 minutes; Telegram: unsends within 48 hours), and an iMessage edit of the message that started the conversation with `first_message_not_editable`; `message` states the limit and how long ago the message was sent. Send a new message instead. `POST /v0/files` answers it for a type Flow does not take (programs, web pages, unknown types). A send by `file_id` of a document a contact sent before Flow malware-scanned documents answers it too: Flow sends only documents it scanned. Flow's template on the shared WhatsApp sandbox sender answers it with `param` `params.body[0]` and `channel_code` `template_value_not_taken` when your message has a line break or tab, more than four spaces in a row, or makes the template longer than WhatsApp's 1024 characters: write it as one shorter line.
    - `new_contact_limit` (429): the sender has used its budget for starting conversations. Wait `retry_after` seconds; replies into existing conversations still go.
    - `sender_throttled` (429): abuse signals tripped (the same text to many new contacts, many starts with no reply, blocks), so the sender may not start conversations until `retry_after`; replies into existing conversations still go. Personalise first messages and start only conversations people expect.
    - `file_blocked` (422): the file failed the malware scan and was not stored. Send a different file. (When the scan cannot run at all, the upload answers a retryable `500 api_error` with `Retry-After` instead.)
    - `rate_limited` (429): either too many requests for this key (the per-key request limit, reported in the `RateLimit-*` headers) or sends faster than the sender's sending rate (pacing). Wait `Retry-After` (`retry_after`) seconds and retry with the same `Idempotency-Key`. On Flow's shared WhatsApp sandbox sender, `channel_code` `flow_template_limit`: your app already sent Flow's template to this contact in the last 24 hours; wait for them to reply, or send it after `retry_after` seconds.
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
            examples=["Send a template instead: POST /v0/conversations/{conversation_id}/template."]
        ),
    ]
    """
    One sentence saying what to change to make the request succeed, specific
    to this case, for example "Send a template instead: POST
    /v0/conversations/{conversation_id}/template." For `unsupported_content`
    it says what to send instead over plain HTTP. Written for developers and
    coding agents alike. Do not parse it; it may be reworded at any time.

    """
    doc_url: Annotated[
        str, Field(examples=["https://api.flow.engineer/docs/errors/outside_window"])
    ]
    """
    The documentation page for this error's type, `https://api.flow.engineer/docs/errors/<type>`. It says what the error means, why it happens and how to fix it, with code.
    """
    param: str | None = None
    """
    The request parameter the error is about, as a dotted path (`kind`, `telegram.is_big`, `buttons`, `cards[1].header.type`, `limit`).
    """
    retry_after: int | None = None
    """
    Seconds to wait before retrying, for errors that clear by themselves.
    """
    channel: Literal["telegram", "whatsapp", "imessage", "sms"] | None = None
    """
    The conversation's channel, on errors about what it takes (`unsupported_content`) and its windows (`outside_window`).
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
    /v0/sandbox/keys` passed its `expires_at`; `permission`, for a send
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
    (`permission`). Connecting your own WhatsApp number (`POST
    /v0/senders`): `whatsapp_token_malformed`, `whatsapp_token_rejected`,
    `whatsapp_app_secret_malformed` and `whatsapp_number_not_in_account`
    (`invalid_request`), and `whatsapp_number_taken`,
    `whatsapp_account_taken` and `whatsapp_number_managed` (`permission`).
    Simulated conversations (`permission`): `test_mode_only`,
    `not_simulated`, `simulated_contact` and `simulated_conversation_limit`.
    For a message that failed after it was queued (`message.failed`):
    `sandbox_contact_left` (`permission`), `window_closed` and
    `queued_too_long` (`outside_window`), and
    `channel_timeout_unknown_outcome` (`channel_error`: the channel never
    confirmed the send, so it may or may not have arrived). iMessage
    (`permission`): `imessage_not_granted` (the account has no access to Flow's shared
    line: sign in at flow.engineer to start the free trial). Paid plans
    (`permission`): `plan_people_limit` (a send to a person the account's
    plan holds: the plan had no room for new people on that channel when
    they wrote; see `Account.people`, and `GET /v0/app`'s `plans` for the
    bigger plan). `plan_ended` (`authentication` for a live key,
    `permission` for a live send: the account's paid plan ended, so its
    live keys and sends are paused until the workspace owner chooses a
    plan again; test keys keep working).
    `imessage_only` (retired 27 Oct 2026; no longer sent: shared lines
    fall back to SMS/RCS).
    iMessage (`unsupported_content`): `group_unsupported` (a reaction, typing or a
    read receipt in a group conversation; `param` `kind`) and
    `not_on_sms` (an edit or unsend of a message that went by SMS or RCS;
    `param` `kind`). SMS (`unsupported_content`): `no_mms` (media to a
    number without MMS; `param` `media`).
    Edits and unsends (`unsupported_content`): `edit_window_closed` and
    `unsend_window_closed` (the message is older than the channel allows
    for the change) and `first_message_not_editable` (iMessage: the message
    that started the conversation). From typing and
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


class CallReceivedEvent(EventBase):
    """
    iMessage only. A contact tried to FaceTime one of your lines. The line
    cannot take calls, so nothing is answered. `conversation` is the direct conversation with the contact, made if it is
    new (with `conversation.started`, `via` `inbound`). A call is not a
    message: it does not count toward plan caps on people, and it does not
    open the conversation for a reply-only line (a send there before the
    contact writes is a start, refused with `403 permission` unless
    `Sender.imessage.can_initiate` is on). Phone calls forwarded by
    `Sender.imessage.call_forwarding` send no event. Delivered only to webhook
    endpoints that list `call.received` in `events`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["call.received"]
    """
    Always `call.received`.
    """
    data: CallData
    conversation: ConversationRef


class ContactDeletedEvent(EventBase):
    """
    A contact was deleted with `DELETE /v0/contacts/{contact_id}`: their address,
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


class ContactLeftEvent(EventBase):
    """
    A person on a shared sender (the sandbox) joined another app, or the other
    mode of your app, by sending its join message. Nothing more reaches you from
    them, and sends to them fail with `permission` (`channel_code`
    `sandbox_contact_left`), until they send your join message again, which starts
    a new `conversation.started`. The contact and their history are kept;
    `conversation` is the conversation they left.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["contact.left"]
    """
    Always `contact.left`.
    """
    data: ContactLeftData
    conversation: ConversationRef


class ConversationStartedEvent(EventBase):
    """
    A new conversation began. Sent before the first `message.received` of a new
    contact, or, when you started the conversation (`data.via` `outbound`), with
    your first send to the contact. A sandbox join (`data.via` `sandbox_join`) also starts one: the
    sandbox bot's confirmation ("You're connected to <your app>") is sent by Flow
    itself, not by your app, and counts against no allowance. Then the join
    message reaches your app as the contact's first `message.received`, after
    this event, with the code taken out: the words before `(ref <code>)`,
    trimmed (`Hi Sandbox app`), or `Hi` when nothing is left; a Telegram link's
    start arrives as `/start`. Answer it like any first message. Joining again
    in a conversation that already exists sends no new `conversation.started`;
    the join message is still delivered as a `message.received`.

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
            MessageReceivedEvent | MessageSentEvent | MessageDeliveredEvent | MessageReadEvent | MessageFailedEvent | ReactionAddedEvent | ReactionRemovedEvent | TypingStartedEvent | TypingStoppedEvent | ConversationStartedEvent | ConversationWindowClosingEvent | SenderStatusChangedEvent | TemplateStatusChangedEvent | ContactDeletedEvent | ContactLeftEvent | CallReceivedEvent,
            Field(discriminator="type"),
        ]
    ]
    has_more: bool
    """
    Whether more committed events follow this page.
    """


class File(BaseModel):
    """
    A stored file. Send it by `file_id` as a basic message's `media`, a voice note or a header.
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
    Its Flow URL (`https://api.flow.engineer/v0/files/{file_id}`), which redirects to the bytes for an authenticated request.
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


class FileBlockedMessage(BaseModel):
    """
    Inbound only. The contact sent a file that Flow did not keep: it failed the
    malware scan, its real type is one Flow does not pass on (programs, web
    pages), it could not be scanned, or it is larger than the channel lets Flow
    download. The file is not stored and has no `url`; what is known about it is
    here. Images, audio and video are not scanned; documents (PDF, Office,
    archives) are, and one Flow could not scan arrives with `reason`
    `scan_failed`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["file_blocked"]
    """
    Always `file_blocked`.
    """
    reason: Literal["malware", "type_not_allowed", "scan_failed", "too_large"]
    """
    Why the file was not kept: `malware` (the scan found something), `type_not_allowed`, `scan_failed` (the scanner could not check it; ask the contact to send it again), or `too_large`.
    """
    media_type: Literal["image", "video", "document", "audio"] | None = None
    """
    What kind of file the channel said it was.
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


class Group(BaseModel):
    """
    Group conversations only (iMessage): the group chat as Flow saw it last.
    People who join or leave change `participants` without an event; Flow
    updates the list when the group next writes. The channel's own group ID is
    never exposed: use the conversation's ID.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    name: str | None = None
    """
    The group chat's name, when it has one.
    """
    participants: list[GroupParticipant]
    """
    The people in the group other than your line, each a contact on the channel (made the first time Flow sees them, like a one-to-one contact).
    """


class GroupParticipant(BaseModel):
    """
    One person in a group chat.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    contact: Annotated[str, Field(examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])]
    """
    A contact ID, `ct_` and a ULID.
    """
    address: ContactAddress
    name: str | None = None
    """
    The person's display name, as the channel reports it. May be missing.
    """


class ImessageSender(BaseModel):
    """
    iMessage senders only: what the line can do beyond replying in iMessage.
    Set by the line and the account's plan (the Outbound add-on is bought in
    the Flow dashboard, `https://flow.engineer/dashboard/plans?plan=dedicated`); absent
    on other channels.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    fallback: bool
    """
    Whether messages to a contact who cannot get iMessage go by SMS or RCS
    instead. The network is chosen for each message when it is sent, never
    by your app; the message's `network` says which one carried it.
    Included on every iMessage line, Flow's shared line (the free trial and
    the Shared plan) and dedicated lines alike. Off only on a line that
    lacks it: then a message to a contact who is not on iMessage fails
    (`message.failed`). A message that goes by SMS or RCS
    shows no `imessage.styles`, `imessage.subject` or effect, and edits
    and unsends of it answer `422 unsupported_content` with
    `channel_code` `not_on_sms` (see `Message.network`).

    """
    call_forwarding: CallForwarding | None = None
    can_initiate: bool
    """
    Whether the line may write first: start a conversation with
    `POST /v0/messages` with a contact who has not messaged it. Off (the
    default), the line only replies and a start answers `403 permission`.
    Writing first is available on dedicated lines only, with the Outbound
    add-on bought in the Flow dashboard (always `false` on shared lines); a line that starts
    conversations spends its new-contact budget (`limits`), which grows
    during warm-up.

    """


class ImessageStyle(BaseModel):
    """
    One styled range of an iMessage text.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    start: int
    """
    Where the range starts, in UTF-16 code units from the start of `text`.
    """
    length: int
    """
    How long the range is, in UTF-16 code units.
    """
    style: Literal["bold", "italic", "underline", "strikethrough", "big", "small", "shake", "nod", "explode", "ripple", "bloom", "jitter"]
    """
    The style. `big` and `small` set the text's size; `shake`, `nod`, `explode`, `ripple`, `bloom` and `jitter` animate it.
    """


class ListMessage(BaseModel):
    """
    WhatsApp's list message, sent only (`POST
    /v0/conversations/{conversation_id}/list`): the text, a button that opens
    the list, and up to 10 rows in sections. A tap on a row arrives as a
    `button_reply` message whose `button_id` is the row's `id` and whose
    `label` is its title. Row `id`s are unique across the list; a repeated one
    is refused with `400 invalid_request`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["list"] = "list"
    """
    Always `list`. Optional on its endpoint; required where no URL names the kind.
    """
    header: str | None = None
    """
    A title shown above the text, 1 to 60 characters.
    """
    text: str
    """
    The message's text, sent exactly as written, 1 to 4096 characters.
    """
    button: str
    """
    The label of the button that opens the list, 1 to 20 characters.
    """
    sections: list[ListSection]
    """
    1 to 10 sections, in order, with at most 10 rows in all.
    """
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as an inline reply to an earlier message in the same
    conversation (Telegram, WhatsApp and iMessage show it quoted). SMS has no
    inline replies: there it answers `422 unsupported_content` with `param`
    `reply_to`. Refused with `404 not_found` (`param` `reply_to`) when the
    target is not a message in this conversation, and with `400
    invalid_request` (`param` `reply_to`) when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    metadata: dict[str, str] | None = None


class ListKind(ListMessage):
    """
    A `list` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`ListMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["list"]
    """
    Always `list`. Optional on its endpoint; required where no URL names the kind.
    """


class ListRow(BaseModel):
    """
    One option of a list.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    id: str
    """
    Your ID for the row, returned in `button_reply` as `button_id`. 1 to 200 characters, unique across the list.
    """
    title: str
    """
    The row's title, 1 to 24 characters, returned in `button_reply` as `label`.
    """
    description: str | None = None
    """
    A line under the title, at most 72 characters.
    """


class ListSection(BaseModel):
    """
    One section of a list.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    title: str | None = None
    """
    The section's title, 1 to 24 characters. Required when the list has more than one section.
    """
    rows: list[ListRow]
    """
    The section's rows, in order.
    """


class LocationMessage(BaseModel):
    """
    A place, in either direction (`POST
    /v0/conversations/{conversation_id}/location` sends one; Telegram and
    WhatsApp). Inbound, a location the contact shared.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["location"] = "location"
    """
    Always `location`. Optional on its endpoint; required where no URL names the kind.
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
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as an inline reply to an earlier message in the same
    conversation (Telegram, WhatsApp and iMessage show it quoted). SMS has no
    inline replies: there it answers `422 unsupported_content` with `param`
    `reply_to`. Refused with `404 not_found` (`param` `reply_to`) when the
    target is not a message in this conversation, and with `400
    invalid_request` (`param` `reply_to`) when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    metadata: dict[str, str] | None = None


class LocationKind(LocationMessage):
    """
    A `location` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`LocationMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["location"]
    """
    Always `location`. Optional on its endpoint; required where no URL names the kind.
    """


class Media(BaseModel):
    """
    One image, video, document or audio file. When sending, give exactly one of
    `url` (an HTTPS URL Flow fetches; Flow neither stores nor scans it, and on
    Telegram a document by URL works for PDF and ZIP files) or `file_id` (from
    `POST /v0/files`). Each channel takes files up to its own size: Telegram
    50 MB, WhatsApp and iMessage 100 MB, SMS (MMS) 5 MB; a larger file answers
    `422 unsupported_content` with `param` `media`. SMS carries images, audio
    and video, never documents (`param` `media.type`), and only from numbers
    with MMS (`channel_code` `no_mms`).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    type: Literal["image", "video", "document", "audio"]
    """
    What kind of file it is.
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
    filename: str | None = None
    """
    The file's name, shown for documents and taken only with `type` `document` (on another type it answers `422 unsupported_content` with `param` `media.filename`). On Telegram it works only with `file_id`: Telegram names a document sent by `url` itself, so `filename` with `url` answers `422 unsupported_content` with `param` `media.filename`.
    """
    mime_type: str | None = None
    """
    Inbound only. The real type, checked from the file's first bytes.
    """
    size_bytes: int | None = None
    """
    Inbound only. The file's size.
    """


class Message(BaseModel):
    """
    One message in or out of a conversation, with its kind and content and its
    delivery status. What you send is what the contact gets: Flow never
    converts a message into another kind.

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
    from_: Annotated[
        str | None, Field(alias="from", examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])
    ] = None
    """
    Inbound messages only, on every channel. The contact who wrote it; in a group conversation, which participant. Absent on your own messages.
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
        MessageContent1 | MessageContent2 | MessageContent3 | MessageContent4 | MessageContent5 | MessageContent6 | MessageContent7 | MessageContent8 | MessageContent9 | MessageContent10 | MessageContent11 | MessageContent12 | MessageContent13 | MessageContent14 | MessageContent15 | MessageContent16,
        Field(discriminator="kind"),
    ]
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """
    network: Literal["imessage", "sms", "rcs"] | None = None
    """
    iMessage channel only: the network that carried the message. `imessage`,
    or `sms` or `rcs` when the contact could not get iMessage and the line
    fell back to SMS or RCS (`Sender.imessage.fallback`, included on every
    iMessage line). The
    network is chosen for each message when it is sent, never by your app.
    Set on inbound messages, and on your messages once the channel reports it
    (in `message.sent`, `message.delivered` or `message.failed`, as
    `data.message.network`); absent before that and on other channels. A
    message that went by `sms` or `rcs` showed no `imessage.styles`, no
    `imessage.subject` and no effect, and edits and unsends of it answer `422
    unsupported_content` with `channel_code` `not_on_sms`.

    """
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
    replies to inline (a Telegram or WhatsApp reply; on iMessage, the thread's
    root message). Absent when the message is not a reply or the quoted
    message is not known to Flow.

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


class MessageContent1(BasicKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["basic"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent13(EditMessage):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["edit"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent15(ButtonReplyMessage):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["button_reply"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent16(FileBlockedMessage):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["file_blocked"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent3(ButtonsKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["buttons"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent4(ListKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["list"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent5(CarouselKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["carousel"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent7(ContactCardKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["contact_card"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent8(LocationKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["location"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

    """


class MessageContent9(EffectKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["effect"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

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


class PeopleLimits(BaseModel):
    """
    The account's plan caps on people, and what is used now. A person counts
    once in a window, with their first inbound message in it on that channel's
    sender, whether one-to-one or in a group chat. Replies count: a person
    your app replies to is one of the people counted. Group members who never
    write, and calls, do not count. On a dedicated iMessage line, the line's
    own daily limit of different people counts everyone it messages, replies
    and starts alike (`Account.plan`). A person past a cap is
    **held**: their messages are kept but not delivered to your app, and are
    delivered once a place frees or the window rolls over. Absent when the
    account's plan has no people caps. These numbers are the source of truth
    for the caps; they are settings and can change.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    per: Literal["channel", "account"]
    """
    `channel`: each channel has its own caps (every plan today). `account`: one set of caps over all channels, with no `channel` on its entry.
    """
    channels: list[ChannelPeople]
    """
    One entry per channel the caps apply to (one entry without `channel` when `per` is `account`).
    """


class PeopleWindow(BaseModel):
    """
    One capped window and how many people it has used.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    window: Literal["total", "day", "month"]
    """
    `total`: since the account began (never resets). `day`: the UTC day. `month`: the UTC calendar month.
    """
    limit: int
    """
    How many people may write in the window.
    """
    used: int
    """
    How many distinct people wrote in the window so far.
    """
    resets_at: datetime | None = None
    """
    When the window rolls over and `used` starts again. Absent for `total`.
    """


class PlanAddOn(BaseModel):
    """
    One add-on on sale.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    add_on: Literal["outbound"]
    """
    The add-on: `outbound`, writing first on a dedicated iMessage line.
    """
    name: Annotated[str, Field(examples=["Outbound"])]
    """
    The add-on's name as the dashboard shows it.
    """
    usd_per_month: Annotated[int, Field(examples=[40])]
    """
    The price in US dollars a month, on top of the plan.
    """
    plans: list[str]
    """
    The plans it can be added to.
    """
    includes: str
    """
    One sentence saying what the add-on gives.
    """
    url: Annotated[
        str, Field(examples=["https://flow.engineer/dashboard/plans?plan=dedicated"])
    ]
    """
    The dashboard's Plans dialog where it is added.
    """


class PlanCatalog(BaseModel):
    """
    The Flow Messaging plans on sale, the add-on, the account's plan now, and
    where to buy. Plans are self-serve and live at once (Dedicated after
    Flow's review of the line): only the workspace owner buys or changes one,
    in the Flow dashboard (Settings → Usage and billing, or `upgrade_url`); an
    API key cannot. Prices and caps are today's; the caps that apply to this
    account now are in `Account.people`. When a trial or plan is full, give
    `upgrade_url` to the person who owns the workspace. Present on every
    answer of the current service.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    current: Annotated[str, Field(examples=["free"])]
    """
    The account's plan now, as in `Account.plan` (`free` is the free trial).
    """
    next: Literal["shared", "dedicated"] | None = None
    """
    The plan that lifts the account's caps next: `shared` from the free trial, `dedicated` from Shared. Absent when no bigger plan is on sale.
    """
    upgrade_url: Annotated[
        str, Field(examples=["https://flow.engineer/dashboard/plans?plan=shared"])
    ]
    """
    The Flow dashboard's Plans dialog, with `next` picked (`?plan=shared`, `?plan=dedicated`), or with nothing picked when there is no `next`. Only the workspace owner can buy there.
    """
    offers: list[PlanOffer]
    """
    The plans on sale, smallest first.
    """
    add_ons: list[PlanAddOn]
    """
    The add-ons on sale, each bought on top of a plan.
    """


class PlanOffer(BaseModel):
    """
    One plan on sale.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    plan: Literal["shared", "dedicated"]
    """
    The plan's value in `Account.plan`.
    """
    name: Annotated[str, Field(examples=["Shared"])]
    """
    The plan's name as the dashboard shows it.
    """
    usd_per_month: Annotated[int, Field(examples=[25])]
    """
    The price in US dollars a month, billed monthly.
    """
    people: list[PlanPeopleCap]
    """
    The plan's caps on different people, per channel: Shared's on Flow's shared senders, Dedicated's on its own iMessage line (on Flow's shared senders Dedicated has Shared's caps). An empty list is no cap.
    """
    includes: str
    """
    One sentence saying what the plan gives.
    """
    url: Annotated[
        str, Field(examples=["https://flow.engineer/dashboard/plans?plan=shared"])
    ]
    """
    The dashboard's Plans dialog with this plan picked.
    """


class PlanPeopleCap(BaseModel):
    """
    How many different people may write in one window, per channel.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    window: Literal["day", "month"]
    """
    `day`: the UTC day. `month`: the UTC calendar month.
    """
    limit: int
    """
    How many different people.
    """


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


class ReactionEventData(BaseModel):
    """
    A reaction the contact added or removed.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    from_: Annotated[
        str | None, Field(alias="from", examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])
    ] = None
    """
    The contact who reacted, where the channel reports it (in a group conversation, which participant).
    """
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """
    emoji: str
    """
    The emoji (iMessage tapbacks are mapped to their closest emoji).
    """


class ReactionMessage(BaseModel):
    """
    A reaction to a message, in either direction (`POST
    /v0/conversations/{conversation_id}/reaction` sends one). Set `emoji` to
    `null` to remove your reaction. Inbound reactions also arrive as
    `reaction.added` and `reaction.removed` events.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["reaction"] = "reaction"
    """
    Always `reaction`. Optional on its endpoint; required where no URL names the kind.
    """
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """
    emoji: str | None
    """
    One emoji, or `null` to remove your reaction (on iMessage, only one you sent). On Telegram only its reaction emoji (listed on the endpoint; with U+FE0F or a skin tone, sent as the listed emoji); any other answers `422 unsupported_content` with `param` `emoji`.
    """
    telegram: ReactionTelegramOptions | None = None


class ReactionKind(ReactionMessage):
    """
    A `reaction` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`ReactionMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["reaction"]
    """
    Always `reaction`. Optional on its endpoint; required where no URL names the kind.
    """


class MessageContent10(ReactionKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["reaction"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

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


class ReactionTelegramOptions(BaseModel):
    """
    Telegram only. On another channel the block answers `422
    unsupported_content` with `param` `telegram`; an unknown key `400
    invalid_request`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    is_big: bool | None = None
    """
    Show the reaction with a large animation.
    """


class ReadMessage(BaseModel):
    """
    A read receipt, sent only (`POST /v0/conversations/{conversation_id}/read`;
    a `read` piece in a webhook reply or on the stream does the same).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["read"] = "read"
    """
    Always `read`. Optional on its endpoint; required where no URL names the kind.
    """
    up_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    WhatsApp only. The latest inbound message to mark read (default the latest inbound message). iMessage marks the whole conversation read, so `up_to` there answers `422 unsupported_content` with `param` `up_to`.
    """


class ReadKind(ReadMessage):
    """
    A `read` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`ReadMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["read"]
    """
    Always `read`. Optional on its endpoint; required where no URL names the kind.
    """


class MessageContent12(ReadKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["read"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

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
    Your ID for the button, returned in `button_reply` as `button_id`: 1 to 64
    bytes (Telegram's limit for a button's data), so at most 64 ASCII
    characters and fewer for other characters. Labels may repeat; the ID is
    what tells the taps apart, so buttons that share a label (a "Details" on
    every card) get their own IDs, such as `details:listing-17`.

    """
    label: str
    """
    The button's text. WhatsApp shows at most 20 characters.
    """


class SandboxAllowance(BaseModel):
    """
    What the app may still send on the shared sandbox senders for free. Present
    only on apps that have one: apps made with `POST /v0/sandbox/keys`
    (`anonymous`, one allowance per app), and apps of people who signed in
    (`signed_in`, one allowance per person: every app the person owns or claimed
    draws on the same contacts and messages, so the counts here are the
    person's, over all those apps). Only messages your agent sends count, on the
    channels in `channels`; inbound messages are free. A contact counts once it
    joins an app on a sandbox sender, and keeps counting after it leaves. Sends
    past the allowance answer `403 permission` with `channel_code`
    `sandbox_allowance_used`; a join past `contacts.limit` is refused in the
    chat. Absent on an account with the free trial (your own account, from
    your first sign-in), which replaces it, and on paid plans.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    tier: Literal["anonymous", "signed_in"]
    """
    `anonymous`: an app made without an account, whose keys expire. `signed_in`: an app of a person who signed in (with a Flow account).
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
    `POST /v0/device/authorizations`. Shown once; keep it with the key. It
    stops working once the app is claimed.

    """
    claim_url: Annotated[
        str, Field(examples=["https://api.flow.engineer/admin/claim#token=fct_..."])
    ]
    """
    A page where a person signs in to Flow and claims the app in the browser, without the CLI. It holds the claim token, so treat it like one. The claim hands out no key and revokes the app's keys unless the person ticks "Keep my agent's current key working"; afterwards they make keys on the dashboard's Keys page.
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
    `POST /v0/test/conversations`; it never touches a network).

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
      (`POST /v0/senders`). They wait at most 72 hours after Flow accepted
      them; older ones fail with `outside_window` (`channel_code`
      `queued_too_long`) in `message.failed` instead of going out late.
    - `banned`: it cannot send or receive: the channel banned it, you
      disconnected it (`DELETE /v0/senders/{sender_id}`), or its bot or line was
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
    imessage: ImessageSender | None = None
    setup: SenderSetup | None = None
    join_code: Annotated[
        str | None, Field(examples=["Hi Sandbox app (ref brave-otter-40718263)"])
    ] = None
    """
    Shared senders only. The whole message a contact sends to this sender to join your app: `Hi `, the app's name (`there` when it has none), then the app's `sandbox_join_code` (from `GET /v0/app`) in brackets after `ref`, for example `Hi Sandbox app (ref brave-otter-40718263)`. Show it to testers as is; a link that fills it in (wa.me, sms:) carries it URL-encoded. Any message of at most 160 characters that ends with `(ref <code>)` joins, so a tester may change the words before the brackets.

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
    The sender's current budget for starting conversations, and how fast it sends.
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
    messages_per_second: Annotated[float | None, Field(examples=[1])] = None
    """
    The sender's pacing: how many messages a second it takes on average,
    replies included, with short bursts allowed above it. A send past it
    answers `429 rate_limited` with `retry_after`. A shared sandbox
    sender's pacing is shared by every app that uses it. Absent for
    simulated senders, which are not paced.

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
    whatsapp_phone_number_id: Annotated[str | None, Field(examples=["106540352242922"])] = (
        None
    )
    """
    WhatsApp only, and required there. The phone number ID of your number (WhatsApp Manager, or App Dashboard > WhatsApp > API Setup), not the phone number itself.
    """
    whatsapp_business_account_id: Annotated[
        str | None, Field(examples=["102290129340398"])
    ] = None
    """
    WhatsApp only, and required there. The ID of the WhatsApp Business Account the number is in.
    """
    whatsapp_access_token: str | None = None
    """
    WhatsApp only, and required there. A system user access token of your
    business (it starts with `EAA`) that never expires, with
    `whatsapp_business_messaging` and `whatsapp_business_management`, and
    your WhatsApp Business Account and Meta app assigned to the system
    user. Stored encrypted; never returned.

    """
    whatsapp_app_secret: str | None = None
    """
    WhatsApp only, and required there. The App secret of your Meta app (App settings > Basic, 32 hexadecimal characters); Meta signs the number's webhooks with it. Stored encrypted; never returned.
    """
    whatsapp_registration_pin: str | None = None
    """
    WhatsApp only, optional. Give it only when the number is not registered
    for the Cloud API yet: Flow registers the number with this six-digit
    two-step verification PIN (the number's current PIN, if it has one).
    Meta allows 10 registrations per number in 72 hours. Stored encrypted;
    never returned.

    """


class SenderSetup(BaseModel):
    """
    Only in the answer to `POST /v0/senders` that connected a WhatsApp number:
    what you still set in your own Meta app, which Flow cannot set for you.
    Flow already points the number's webhooks at `callback_url` (Meta's
    phone-number-level override); entering the same URL in your app makes its
    field subscriptions apply. The verify token is shown only in this answer
    (connecting the number again shows it again); keep it like a password.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    callback_url: Annotated[
        str,
        Field(
            examples=["https://api.flow.engineer/ingress/whatsapp/snd_01J9ZK3N5B6VQ1M2X4C7R8T9WA"]
        ),
    ]
    """
    The callback URL to enter in your Meta app (App Dashboard > WhatsApp > Configuration > Webhook).
    """
    verify_token: str
    """
    The verify token to enter with the callback URL.
    """
    webhook_fields: Annotated[
        list[str],
        Field(
            examples=[["messages", "message_template_status_update", "phone_number_quality_update", "account_update", "business_capability_update", "template_category_update", "account_alerts"]]
        ),
    ]
    """
    The webhook fields to subscribe in the same place.
    """
    steps: list[str]
    """
    The steps in your Meta app, in order, as plain sentences to show a person.
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
      (`POST /v0/senders`). They wait at most 72 hours after Flow accepted
      them; older ones fail with `outside_window` (`channel_code`
      `queued_too_long`) in `message.failed` instead of going out late.
    - `banned`: it cannot send or receive: the channel banned it, you
      disconnected it (`DELETE /v0/senders/{sender_id}`), or its bot or line was
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
    provider: str
    """
    Where they signed in: `flow` (a Flow account, flow.engineer: every sign-in
    today). `github` and `google` are sign-ins made on the Messaging API itself
    before Flow accounts. More may be added later, so treat a value you do not
    know as a sign-in elsewhere rather than an error.

    """


class SimulatedButtonTap(BaseModel):
    """
    The simulated contact taps a reply button of a buttons or carousel message
    your app sent in this conversation, or a row of a list. Name the message
    and the button's (or row's) `id`; Flow fills in the label, and the received
    message is a `button_reply` with the tapped button's `label` (a row's
    title). A channel that shows no buttons has nothing to tap: the contact
    answers in words, as a `basic` turn.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["button_reply"]
    """
    Always `button_reply`.
    """
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    The buttons, carousel or list message your app sent, which must have reached the contact (its `message.sent`).
    """
    button_id: str
    """
    The `id` of the tapped reply button or list row.
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
        BasicKind | VoiceKind | LocationKind | ContactCardKind | SimulatedButtonTap,
        Field(discriminator="kind"),
    ]
    """
    What a simulated contact sends in one turn, as a message kind with `kind`
    (required): `basic` (`text` and/or `media` by `file_id`), `voice` (by
    `file_id`), `location`, `contact_card`, or `button_reply` (a tap on a reply
    button, or on a list row, of a message your app sent). Fields a contact
    cannot send (`reply_to` and `metadata` inside the kind, channel blocks,
    `link_preview`, `url`) and other kinds answer `400 invalid_request`.

    """
    from_: Annotated[
        str | None, Field(alias="from", examples=["ct_01JB8ZB2J4K6N8Q0S2V4W6Y8A0"])
    ] = None
    """
    Simulated group conversations only, and required there. The participant who writes this turn (a `contact` in the conversation's `group.participants`); another contact answers `400 invalid_request` with `param` `from`. Refused the same way on one-to-one conversations.
    """
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    A message of this conversation the contact replies to inline, on channels with inline replies (Telegram, WhatsApp, iMessage; on SMS it answers `400 invalid_request`). The received message shows it in `reply_to`.
    """


class SmsSegments(BaseModel):
    """
    SMS text messages only: how the text travels as SMS. Carriers bill and
    deliver SMS in segments: 160 GSM-7 characters fit one segment (153 each
    when split), but a single character outside GSM-7 (an emoji, curly quotes,
    most non-Latin letters) makes the whole text UCS-2, 70 characters in one
    segment (67 each when split). An SMS send may use at most 10 segments:
    1530 GSM-7 characters (fewer when it uses GSM-7's two-unit characters such
    as `{` or `€`), or 670 when it holds an emoji or other character outside
    GSM-7; a longer text is refused with `400 invalid_request`. Absent on MMS
    and on other channels.

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
    Whether the number sends and receives MMS (images, audio and video). Without it, a basic message with `media` answers `422 unsupported_content` with `param` `media` and `channel_code` `no_mms`.
    """
    quiet_hours: QuietHours | None = None


class StartConversationTarget(BaseModel):
    """
    Where a start goes. Part of every `StartConversationRequest`.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    sender: Annotated[str, Field(examples=["snd_01JB8Z4Q3V6W0R2N7C5H1M9K4T"])]
    """
    A sender ID, `snd_` and a ULID.
    """
    to: Recipient
    consent: Consent | None = None
    """
    SMS only. The contact's consent, required when they have never texted any of your SMS numbers; recorded on the contact. On another channel it answers `422 unsupported_content` with `param` `consent`.
    """


class StartBasicMessage(StartConversationTarget, BasicMessage):
    """
    A start whose first message is a basic message (`kind` `basic`).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["basic"]
    """
    Always `basic`. Optional on `POST /v0/conversations/{conversation_id}/basic`; required where no URL names the kind (webhook replies, the stream, starts, a message's `content`).
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
    Server to client. A `send` or `start` frame was refused (with its `ref`), or the stream itself was refused or failed (without `ref`; the server then closes the socket with a 4000-range close code, `4401` for `authentication`, see `GET /v0/stream`).
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
        MessageReceivedEvent | MessageSentEvent | MessageDeliveredEvent | MessageReadEvent | MessageFailedEvent | ReactionAddedEvent | ReactionRemovedEvent | TypingStartedEvent | TypingStoppedEvent | ConversationStartedEvent | ConversationWindowClosingEvent | SenderStatusChangedEvent | TemplateStatusChangedEvent | ContactDeletedEvent | ContactLeftEvent | CallReceivedEvent,
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
    Client to server. Sends one message into a conversation, the same as the
    endpoint of its `kind` (`POST /v0/conversations/{conversation_id}/<kind>`,
    or `PATCH` and `DELETE /v0/messages/{message_id}` for `edit` and
    `unsend`); `ref` is also the idempotency key. Frames into one conversation
    go out in the order accepted, in line with the conversation's other sends.
    The frame's `type` is the frame's own type; the message's kind is
    `message.kind`.

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
    message: Annotated[
        BasicKind | VoiceKind | ButtonsKind | ListKind | CarouselKind | TemplateKind | ContactCardKind | LocationKind | EffectKind | ReactionKind | TypingKind | ReadKind | EditMessage | UnsendMessage,
        Field(
            discriminator="kind",
            examples=[{"kind": "basic", "text": "Here are the sizes we have."}, {"kind": "buttons", "text": "Which size?", "buttons": [{"id": "size_s", "label": "Small"}, {"id": "size_m", "label": "Medium"}]}],
        ),
    ]
    """
    One message to send where no URL names the kind: a piece of a webhook
    reply (`WebhookReply`) or the `message` of a stream `send` frame. `kind`
    is required and selects the shape; the fields and channel rules are the
    same as on the kind's endpoint (`edit` and `unsend` as on `PATCH` and
    `DELETE /v0/messages/{message_id}`, with the target in `message_id`).

    """


class StreamStartFrame(BaseModel):
    """
    Client to server. Same as `POST /v0/messages` (a `basic` or `template` message with `kind`, `sender` and `to`); `ref` is also the idempotency key.
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
    message: Annotated[
        StartBasicMessage | StartTemplateMessage, Field(discriminator="kind")
    ]
    """
    The first message from one of your senders to a contact: a `basic` or a
    `template` message, with `kind` saying which (required here), plus
    `sender`, `to` and, on SMS, `consent`. A field not listed for the kind is
    refused with `400 invalid_request` naming it in `param`, never ignored; a
    `kind` other than `basic` or `template` answers `422 unsupported_content`
    with `param` `kind`. On iMessage the sender must be able to write first
    (`Sender.imessage.can_initiate`, available on dedicated lines with the
    Outbound add-on); otherwise the
    start answers `403 permission`. A start always makes a `direct`
    conversation: there is no way to start a group. There are no scheduled
    sends: to start a conversation later, wait in your own code and send then.

    """


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
    One JSON frame on the `/v0/stream` WebSocket. The server sends `event`, `ack`,
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
    Meta's reason, when the template was rejected: its code, then `: ` and
    Meta's words when it sent some, such as
    `INVALID_FORMAT: The template has placeholders next to each other.`
    `rejection` holds the same in parts, with Meta's recommendation.

    """
    rejection: TemplateRejection | None = None
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
    example: Annotated[str | None, Field(examples=["A-1042"])] = None
    """
    For a `url` button whose link ends in `{{1}}`, a realistic sample value
    for the end of the link (what you will pass in `params.buttons` when
    sending), for WhatsApp's review: Flow shows the reviewers the link with
    the sample in place. That link is at most 2000 characters, and the sample
    has no spaces or line breaks. Left out, Flow sends a placeholder sample
    instead. Not taken on other buttons.

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


class TemplateCardParams(BaseModel):
    """
    The values for one card of a carousel template.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    card_index: int
    """
    The card's position in the template, from 0.
    """
    header: TemplateHeaderParam | None = None
    """
    The card's image or video (`kind` `image` or `video`, by `url` or `file_id`).
    """
    body: list[str] | None = None
    """
    Values for the card body's `{{1}}`, `{{2}}`, ... in order.
    """
    buttons: list[TemplateButtonParam] | None = None
    """
    Values for the card's buttons that take one (URL suffixes, quick-reply payloads).
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
    examples: Annotated[list[str] | None, Field(examples=[["Maria", "A-1042"]])] = None
    """
    For a body or a text header with placeholders, a realistic sample value
    for each placeholder, in order (`{{1}}` first). WhatsApp's reviewers read
    the template with these values, and a template whose samples do not look
    real is often rejected or moved to another category, so give them for
    every new template. Exactly one per placeholder; each 1 to 60 characters
    in a header and 1 to 1024 in a body, with no line breaks, tabs or more
    than four spaces in a row. Left out, Flow sends WhatsApp placeholder
    samples (`x1`, `x2`, ...) instead. Not taken on footers, buttons parts,
    media headers or text without placeholders.

    """
    buttons: list[TemplateButton] | None = None
    """
    For `buttons`, the buttons in order.
    """


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


class TemplateMessage(BaseModel):
    """
    A WhatsApp message template, sent only (`POST
    /v0/conversations/{conversation_id}/template`, or `POST /v0/messages` to
    start a conversation). Required to start a WhatsApp conversation or to
    write after the 24-hour window closed. The template must be `approved`.

    A media card carousel template (marketing category) is sent the same way,
    with one entry per card in `params.cards`. Inside the 24-hour window a
    carousel needs no template: send a `carousel` message.

    Flow's shared WhatsApp sandbox sender takes no templates of your own; it
    sends one template of Flow's, listed by `GET
    /v0/templates?sender=<that sender>` with a test key. It reads "Time-sensitive
    update from {{1}}: {{2}} Reply to this message to continue." with a "Tell me
    more" button. Flow fills `{{1}}` with your app's name; give only your message,
    as the one value in `params.body`. The message must be one line, with no
    tabs and at most four spaces in a row, or the send answers `422
    unsupported_content` (`channel_code` `template_value_not_taken`). Each
    contact who joined your app can get it at most once in any 24 hours; a
    second answers `429 rate_limited` (`channel_code` `flow_template_limit`,
    with `retry_after`).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["template"] = "template"
    """
    Always `template`. Optional on its endpoint; required where no URL names the kind (and on `POST /v0/messages`).
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
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as an inline reply to an earlier message in the same
    conversation (Telegram, WhatsApp and iMessage show it quoted). SMS has no
    inline replies: there it answers `422 unsupported_content` with `param`
    `reply_to`. Refused with `404 not_found` (`param` `reply_to`) when the
    target is not a message in this conversation, and with `400
    invalid_request` (`param` `reply_to`) when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    metadata: dict[str, str] | None = None


class StartTemplateMessage(StartConversationTarget, TemplateMessage):
    """
    A start whose first message is a WhatsApp template (`kind` `template`).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["template"]
    """
    Always `template`. Optional on its endpoint; required where no URL names the kind (and on `POST /v0/messages`).
    """


class TemplateKind(TemplateMessage):
    """
    A `template` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`TemplateMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["template"]
    """
    Always `template`. Optional on its endpoint; required where no URL names the kind (and on `POST /v0/messages`).
    """


class MessageContent6(TemplateKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["template"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

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
    cards: list[TemplateCardParams] | None = None
    """
    Carousel templates only. Values for each card's header, body placeholders and buttons.
    """


class TemplateRejection(BaseModel):
    """
    Why Meta rejected the template, as Meta's template status update said it.
    Present only while the template is `rejected`; each field only when Meta sent
    it.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    code: Annotated[str | None, Field(examples=["INVALID_FORMAT"])] = None
    """
    Meta's reason code, such as `INVALID_FORMAT`, `INCORRECT_CATEGORY` or `ABUSIVE_CONTENT`.
    """
    title: Annotated[str | None, Field(examples=["FORMATTING"])] = None
    """
    Meta's heading for the problem.
    """
    description: Annotated[
        str | None,
        Field(examples=["The template has placeholders next to each other."]),
    ] = None
    """
    Meta's words on what is wrong with the template.
    """
    recommendation: Annotated[
        str | None, Field(examples=["Add words between the placeholders."])
    ] = None
    """
    Meta's suggestion for fixing the template before submitting it again.
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
    The simulated contact's display name, as a channel would report it. Not with `group`.
    """
    group: TestGroupRequest | None = None


class TestGroupParticipant(BaseModel):
    """
    One simulated person in a simulated group.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    address: TestContactAddress | None = None
    name: str | None = None
    """
    The participant's display name.
    """


class TestGroupRequest(BaseModel):
    """
    `imessage` only: make a simulated group conversation (`type` `group`)
    instead of a one-to-one one, with these participants. Not with `contact`
    or `name`. Each turn names the participant who writes (`from` on
    `POST /v0/test/conversations/{conversation_id}/inbound`). Another channel
    answers `400 invalid_request` with `param` `group`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    name: str | None = None
    """
    The group chat's name. Leave it out for an unnamed group.
    """
    participants: list[TestGroupParticipant]
    """
    The people in the group other than your line. Each becomes a simulated contact; a participant without `address` gets a made-up one.
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
    acceptance time. In the event log (`GET /v0/events`,
    `GET /v0/events/{event_id}`, the stream), it is when the first endpoint
    accepted the event, and it is absent until one has (always, for an app
    with no webhook endpoints).

    """


class TranscriptEntry(Message):
    """
    One message of a simulated conversation, as a `Message`. A sent message's
    `content` is exactly what the simulated contact sees: Flow converts
    nothing.

    """

    model_config = ConfigDict(
        extra="allow",
    )


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


class TypingImessageOptions(BaseModel):
    """
    iMessage only. On another channel the block answers `422
    unsupported_content` with `param` `imessage`; an unknown key `400
    invalid_request`.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    duration_seconds: int | None = None
    """
    How long to show the indicator, 1 to 60 seconds, unless a message goes first.
    """


class TypingMessage(BaseModel):
    """
    The typing indicator, sent only (`POST
    /v0/conversations/{conversation_id}/typing`; a `typing` piece in a webhook
    reply or on the stream does the same). It shows the indicator, which
    clears itself when your next message goes or after a few seconds.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["typing"] = "typing"
    """
    Always `typing`. Optional on its endpoint; required where no URL names the kind.
    """
    imessage: TypingImessageOptions | None = None


class TypingKind(TypingMessage):
    """
    A `typing` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`TypingMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["typing"]
    """
    Always `typing`. Optional on its endpoint; required where no URL names the kind.
    """


class MessageContent11(TypingKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["typing"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

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


class UnsendMessage(BaseModel):
    """
    Removes one of your sent messages from the contact's chat, as a kind: a
    piece of a webhook reply or on the stream, and the `content` of the message
    that carries an unsend (`DELETE /v0/messages/{message_id}` over HTTP,
    whose rules apply).

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["unsend"]
    """
    Always `unsend`.
    """
    message_id: Annotated[str, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])]
    """
    A message ID, `msg_` and a ULID.
    """


class MessageContent14(UnsendMessage):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["unsend"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

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


class VoiceMessage(BaseModel):
    """
    A voice note, in either direction (`POST
    /v0/conversations/{conversation_id}/voice`). When sending, give `url` or
    `file_id` of an audio file. Inbound voice notes always come with the audio
    file (`url`, `file_id`), and usually with a `transcript` of what was said:
    iMessage's own on iMessage, else Flow's when the app's `transcription`
    setting is on (the default). `transcript_source` says which. A voice note
    Flow could not transcribe in time (it waits at most 20 seconds), or one
    over Flow's limits, arrives without a transcript; the audio is always there.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["voice"] = "voice"
    """
    Always `voice`. Optional on its endpoint; required where no URL names the kind.
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
    reply_to: Annotated[str | None, Field(examples=["msg_01JB8ZD4M6P8R0T2V4X6Z8B0C2"])] = (
        None
    )
    """
    Send this as an inline reply to an earlier message in the same
    conversation (Telegram, WhatsApp and iMessage show it quoted). SMS has no
    inline replies: there it answers `422 unsupported_content` with `param`
    `reply_to`. Refused with `404 not_found` (`param` `reply_to`) when the
    target is not a message in this conversation, and with `400
    invalid_request` (`param` `reply_to`) when the target never reached the
    channel (for example, it failed). If the target fails after the send was
    accepted, the reply goes out as a normal message.

    """
    metadata: dict[str, str] | None = None
    duration_seconds: float | None = None
    """
    Inbound only. The voice note's length.
    """
    transcript: str | None = None
    """
    Inbound only. What was said, when the voice note has a transcript (see `transcript_source`). Absent when there is none.
    """
    transcript_source: Literal["channel", "flow"] | None = None
    """
    Inbound only, with `transcript`. Who made the transcript. `channel`, the channel's own (iMessage's); `flow`, Flow's speech-to-text (the app's `transcription` setting).
    """


class VoiceKind(VoiceMessage):
    """
    A `voice` message with `kind` given, as in a message's `content`, a webhook reply or a stream frame (`VoiceMessage` with `kind` required).
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["voice"]
    """
    Always `voice`. Optional on its endpoint; required where no URL names the kind.
    """


class MessageContent2(VoiceKind):
    """
    A message's content: one kind object, in either direction, with `kind`
    (always present here) saying which. It is exactly what was sent or
    received, except `metadata`, which is kept once, at the message's own
    `metadata`, and not repeated here.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["voice"]
    """
    The kinds of message. A closed list: a new kind arrives only with a new API
    version. Each kind has its own schema (`BasicMessage`, `VoiceMessage`, ...)
    and, where it can be sent over HTTP, its own endpoint of the same name
    (`POST /v0/conversations/{conversation_id}/<kind>`, with `contact-card` for
    `contact_card`). `edit` and `unsend` are sent over HTTP with `PATCH` and
    `DELETE /v0/messages/{message_id}`, and are kinds in webhook replies, on
    the stream and in a message's `content`. `button_reply` and `file_blocked`
    are inbound only.

    Received from a contact: `basic`, `voice`, `button_reply`, `reaction`,
    `location`, `contact_card` and `file_blocked`. Sent: every kind but
    `button_reply` and `file_blocked`.

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
    events: list[Literal["message.received", "message.sent", "message.delivered", "message.read", "message.failed", "reaction.added", "reaction.removed", "typing.started", "typing.stopped", "conversation.started", "conversation.window_closing", "sender.status_changed", "template.status_changed", "contact.deleted", "contact.left", "call.received"]]
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
    events: list[Literal["message.received", "message.sent", "message.delivered", "message.read", "message.failed", "reaction.added", "reaction.removed", "typing.started", "typing.stopped", "conversation.started", "conversation.window_closing", "sender.status_changed", "template.status_changed", "contact.deleted", "contact.left", "call.received"]]
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
    events: list[Literal["message.received", "message.sent", "message.delivered", "message.read", "message.failed", "reaction.added", "reaction.removed", "typing.started", "typing.stopped", "conversation.started", "conversation.window_closing", "sender.status_changed", "template.status_changed", "contact.deleted", "contact.left", "call.received"]] | None = (
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
    The optional body of your answer to a `message.received` delivery. `reply`
    is one message or a list of up to 11, sent in order into the event's
    conversation through the send gate: each piece is a kind object
    (`OutboundKind`, with `kind`), so a text plus 10 carousel cards sent one by
    one fits. A non-empty string, as `reply` or as an item of the list, is a
    basic message: `{"reply": "Hi"}` is short for `{"reply": {"kind":
    "basic", "text": "Hi"}}`. Leave `reply` out, set it to `null`, or answer
    `{}`, an empty body or any body that is not a JSON object (such as `OK`)
    to send nothing now; that is not an error.

    A JSON object whose `reply` does not match this shape (a piece that is not
    a kind object or a string, an unknown `kind`, an empty list, more than 11
    pieces), or a body that starts with `{` but is not valid JSON, sends
    nothing at all (no piece of a list goes out) and is recorded on the
    delivery as an `invalid_request` error with the reason; the delivery
    counts as delivered and is not retried. A piece the send gate refuses (for
    example a `carousel` on Telegram, `422 unsupported_content`) is reported
    as a `message.failed` event.

    """

    model_config = ConfigDict(
        extra="allow",
    )
    reply: str | list[str | BasicKind | VoiceKind | ButtonsKind | ListKind | CarouselKind | TemplateKind | ContactCardKind | LocationKind | EffectKind | ReactionKind | TypingKind | ReadKind | EditMessage | UnsendMessage] | BasicKind | VoiceKind | ButtonsKind | ListKind | CarouselKind | TemplateKind | ContactCardKind | LocationKind | EffectKind | ReactionKind | TypingKind | ReadKind | EditMessage | UnsendMessage | None = (
        None
    )
    """
    One message, or a list of 1 to 11 sent in order. A non-empty string is a basic message's text. `null` sends nothing.
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
