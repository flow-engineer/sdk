// Facts the CLI states. They are also in agents/facts.json, the agent docs' one
// source (cli_tagline, sign_in, dashboard_url); test/unit/agent-facts.test.ts fails when they differ.

/** What the CLI is for, after its name and version in `--help`. */
export const CLI_TAGLINE = "Telegram, iMessage and WhatsApp for AI agents.";

/** The sign-in a person uses to keep a sandbox app. */
export const SIGN_IN = "a Flow account (flow.engineer: Google, GitHub or an email link)";

/** The Flow dashboard, where signed-in people manage their apps and keys. */
export const DASHBOARD_URL = "https://flow.engineer/dashboard";
