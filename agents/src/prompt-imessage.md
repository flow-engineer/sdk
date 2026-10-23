Connect this project to Flow's Messaging API and send me an iMessage from its code.

My test key goes in `.env` as `{{env.api_key}}`, and I add it myself. If `.env` has no `{{env.api_key}}`, add an empty `{{env.api_key}}=` line, make sure `.env` is in `.gitignore`, and ask me to paste my key from the Flow dashboard into the file. Wait for me.

{{> prompt-imessage-steps}}
