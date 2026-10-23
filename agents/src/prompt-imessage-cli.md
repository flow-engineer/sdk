Connect this project to Flow's Messaging API and send me an iMessage from its code. Do the setup for me.

The code reads my Flow Messaging test key from `{{env.api_key}}` in the project's `.env`; you don't need to see the key yourself. Check that the line is there by its name only (for example `grep -q '^{{env.api_key}}=.' .env`), never by printing the file. If it isn't there, run `npx {{package}}@latest login`: it opens my browser to sign in to Flow, and once I approve it writes the key to `.env` itself (and adds `.env` to `.gitignore`). Wait for me to approve, then check that `.env` is in `.gitignore`.

{{> prompt-imessage-steps}}
