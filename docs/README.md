# docs

Source of https://docs.flow.engineer (Mintlify). Not published itself: Mintlify skips `README.md`.

- `docs.json`: site config, navigation, SEO and the agent instructions added to every Markdown page.
- `index.mdx`, `quickstart.mdx`, `coding-agents.mdx`, `pricing.mdx`, `concepts/`, `guides/`, `frameworks/`: the pages.
- `api-reference/introduction.mdx` plus the endpoint pages Mintlify generates from `openapi.yaml`, a copy of `../openapi/openapi.yaml` (the spec is the single source; Mintlify builds only this folder, so it is a real file, and `scripts/check-spec-drift.sh` fails when it differs).
- `errors/` and `mcp.md`: the error pages (one per error type; each error's `doc_url` links here) and the hosted MCP server page.
- `skill.md`: the agent skill served at `/skill.md`.
- `compare/`: the comparison pages. Every claim they make about another product lives in `compare/claims.yaml` (claim, source URL, date checked, pages) and is marked on the page with `{/* claim: <id> */}`. `scripts/check-compare.sh` (run by `scripts/local-checks.sh`) fails when a claim was last checked more than 90 days ago, and warns 14 days before that; `scripts/check-compare.sh --fetch` also flags sources that are gone. When you re-verify, update the claim, the page and its "Last verified" line.
- `logo/`: placeholder text marks.

Mintlify also serves `/llms.txt`, `/llms-full.txt` and a `.md` version of every page; nothing to build for those.

## Preview and check

```bash
cd docs
npx mint dev            # http://localhost:3000
npx mint broken-links   # internal links
npx mint validate       # strict build, includes the OpenAPI spec
```

Every page starts with one sentence saying what it is for, then a runnable snippet. Give each page a `title`, `description` and `keywords` in its frontmatter; they become the search snippet and the `llms.txt` entry.
