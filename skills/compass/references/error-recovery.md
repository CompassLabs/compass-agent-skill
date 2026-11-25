# Compass error recovery (CLI + MCP)

Most first-run **[CLI]** failures are flag-parsing or auth, not the API — diagnose with the table below. The **[MCP]** surface takes typed JSON, so the flag-parsing classes can't happen; its distinct failure modes are in "[MCP] failure modes" at the end. The `HTTP 4xx/5xx` rows apply to both.

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `error unmarshalling json response body: invalid character 'b' …` on a flag | An **optional** string flag was parsed as JSON (older CLI versions only) | JSON-quote just that flag: `--chain '"base"'`. The message says "response body" but it's actually flag parsing. Recent builds accept plain values. |
| API returns `Unknown token symbol` though the symbol is correct | A **required** flag was over-quoted, sending literal `"USDC"` | Drop the quotes on required/enum flags: `--borrow-token USDC` |
| `unknown command`/`unknown flag` for something you expected | Name is wrong for this version (groups/subcommands change between releases) | Re-list from the binary: `compass --help`, `compass <group> --help`, `compass --usage`. If behind the latest release, update the CLI and retry |
| `unknown flag: --foo` | Inferred a flag name that doesn't exist | Re-read `compass <cmd> --help`; look for the **nested** form (`--venue.vault.foo`) |
| `missing required flag: --foo` | Required flag absent | Add it; check the doc for nested required flags |
| `HTTP 401 … API key missing or invalid` | Auth not set or wrong var | `export COMPASS_API_KEY_AUTH=…` (note the `_AUTH` suffix) and re-run |
| `HTTP 422` | Request body validation | Read the response for which field failed; nested objects often need a type discriminator (e.g. `{"type":"VAULT", …}`) |
| `HTTP 4xx` (other) | Domain logic: insufficient balance, bad address, etc. | Surface verbatim to the user — usually actionable |
| `HTTP 5xx` | Backend issue | Retry once with `--debug`; if persistent, surface to user |
| `command not found: --foo` (zsh) | Trailing whitespace after a `\` line-continuation broke parsing | Re-run as a single line, or strip trailing spaces |
| `-o table` shows a tiny scalar table, hides the list | `table` doesn't unwrap the envelope `{total, …, items:[…]}` | Use `--jq '.items'` (or the real array key) |
| A metavar like `--amount from_token` looks like required syntax | It's generator noise from an OpenAPI example | Ignore the metavar; read the **Description**; pass the real value |

## JSON-quoting: default to plain

- **Default to plain values.** Recent CLI builds list enum options in `--help` (e.g. `--chain base`) and accept them directly.
- **Older versions** parsed *optional* string query-param flags as JSON (`json.Unmarshal` on the raw value), so a bare word failed with "unmarshalling json response body". Only then, JSON-quote just that flag: `--chain '"base"'`.
- **Required** and **enum** flags always take plain values — never quote them. Over-quoting (`--token-in '"USDC"'`) sends a literal `"USDC"` → confusing "Unknown token symbol" 422.
- Flags that historically hit the optional-flag bug: `--chain`, `--asset-symbol`, `--underlying-symbol`, `--category`, `--search`, `--interval`, `--range`, `--asset`.

## Quick health checks

```bash
compass version                 # is it installed?
compass whoami                  # is auth working?
compass <group> <cmd> --dry-run …   # what request would this send?
compass <group> <cmd> --debug …     # full request/response to stderr
```

## [MCP] failure modes

The MCP tools take typed JSON, so the flag-quoting / `-o table` classes above can't happen. What does come up:

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Tool result truncated / "exceeds maximum tokens" | An unfiltered **read** returned a huge payload (full market catalog, or a balance/positions read on a spam-airdropped account) | Re-call with the tool's filters — `limit`/`offset`, `provider`, `chain`, `asset_symbol`, `search` — to return only the rows you need |
| `401` | The `X-API-Key` header on the server registration is missing/invalid | Re-add the server with a valid key: `claude mcp add … --header "X-API-Key: …"` |
| `422` / other `4xx` with a message | Request/domain validation (bad discriminator, thin-liquidity slippage, wrong trade flow…) | Read the `{error, message}` body — it's specific (e.g. "raise slippage_bps", "Wrong trade flow") — and adjust the params |
| Want to "preview" before running | There's no `--dry-run` on MCP | Action tools return the **unsigned** tx/EIP-712 *without broadcasting* — inspect it before the user signs; that is the preview |
| The user says there is no signing panel | Their client does not render MCP Apps views (terminal agents do not), or the result is a payload the panel does not cover (perps typed data, a tokenized equity order) | Sign by hand: `signing.md`, section 2 |
| "The signing link expired" / "This request is no longer available" | A signing request lives 15 minutes from when the tool built it | Call the tool again and have the user sign the new request |
| The panel says the step returned nothing to sign | The result has no payload, typically `transaction: null` from `*_create_account` on an account that already exists | Nothing to do; continue with the next step |
| A hash came back but the position or balance has not changed | A hash means sent, not succeeded: the transaction is pending or it reverted | Read positions/balances again after a short wait; if still unchanged, have the user check the hash on a block explorer and surface the revert reason |
| The user wants to change the request after the panel appeared | The panel signs only the payload the server built | Call the tool again with the new arguments; never edit a payload by hand |
| A tool name from this skill isn't listed | Tool names track the live API and can be renamed | Trust the actually-connected tool list + the server's on-connect instructions |
