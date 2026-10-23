Connect this project to Flow's Messaging API and send me an iMessage from its code.

The code reads my Flow Messaging test key from `{{env.api_key}}` in the project's `.env`; you don't need to see the key yourself. Check that the line is there by its name only (for example `grep -q '^{{env.api_key}}=.' .env`), never by printing the file. If it isn't there, make sure `.env` is in `.gitignore`, then ask me for my test key (it's on the Get started page of the Flow dashboard, {{dashboard_url}}) and give me this one line to save it myself, run in the project's folder:

    echo '{{env.api_key}}=<paste your key>' >> .env

Wait until I say it's saved (or, if I give you the key here, save it to `.env` for me).

{{> prompt-imessage-steps}}
