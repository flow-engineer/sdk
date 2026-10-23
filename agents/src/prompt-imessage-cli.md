Connect this project to Flow's Messaging API and send me an iMessage from its code. Do the setup for me.

Get my test key with `npx {{package}}@latest login`. It opens my browser to sign in to Flow; wait for me to approve. It writes `{{env.api_key}}` to `.env`; make sure `.env` is in `.gitignore`. If `.env` already has a `{{env.api_key}}`, use it and skip the sign-in.

{{> prompt-imessage-steps}}
