# Compass CLI error recovery

Most first-run failures are flag-parsing or auth, not the API. Diagnose with this table before retrying.

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
