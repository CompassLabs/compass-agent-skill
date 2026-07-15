# Compass capability map

> **Names are version-specific — this maps *what Compass can do* to *where to look*, not exact syntax.** Get the real names from the live surface:
> - **[CLI]** `compass --help` (product groups) · `compass <group> --help` (its subcommands) · `compass --usage` (every command + flag in one shot)
> - **[MCP]** the connected tool list + each tool's JSON schema (tool names mirror the API operation ids, e.g. `v2_earn_vaults`)
>
> Treat every name below as a **pointer**, not gospel. Groups, subcommands, and tool names have been renamed and restructured across releases.

## How to go from intent to a command / tool

1. Enumerate the surface — **[CLI]** `compass --help`; **[MCP]** the connected tool list.
2. Pick the group / tool family matching the user's intent (table below).
3. List the actions — **[CLI]** `compass <group> --help`; **[MCP]** the tools in that family (e.g. `v2_credit_*`).
4. Read the params — **[CLI]** `compass <group> <command> --help` (nested `--a.b.c`); **[MCP]** the tool's JSON schema (nested objects).

## Intent → capability area

| User wants… | Capability area | Notes |
|-------------|-----------------|-------|
| Earn yield — deposit/withdraw in vaults (ERC‑4626 / Morpho), Aave, or Pendle; list markets; positions | **Earn / yield** | one `manage`-style command does deposit *and* withdraw across venue types, chosen via a nested `--venue.*` flag (vault / Aave / Pendle) |
| Lend / borrow against collateral; repay | **Credit / lending** | |
| Perpetual futures — open/close long-short, market/limit orders | **Perps** | group name has changed across versions — find it via `compass --help`. Orders are *prepare → sign → execute* |
| Buy / sell tokenized equities (stocks) | **Tokenized equities** | group has been renamed across versions. *quote → order → sign → submit* |
| Pay gas on the user's behalf (sponsor) | **Gas sponsorship** | |
| Move tokens in/out of a product account, or swap within it | the per-product `transfer` / `swap` commands | |
| Auth / who am I / configure | **auth**, `whoami`, `configure` (TUI) | |
| Browse commands interactively | `explore` (TUI — not for non-interactive agents) | |
| Portfolio risk math | `risk-recipes` (prints formulas) | |

## Version-independent patterns

These hold regardless of exact names:

**Account prerequisites — check deployment, create if missing.** `credit`, `earn`, and `tokenized-equities` each act through a per-product smart account (a Safe) that must be **deployed** (and, for credit/earn, funded) first. Its address is **deterministic/counterfactual** — Compass returns it even when nothing is deployed there, so don't read "an address came back" (or zero balances) as "it exists." Check on-chain deployment (`cast code <account-address>` → `0x` = not created); if undeployed, run the group's `create-account` + `transfer`, then act. One-time per owner per product per chain. **Perps (`global-markets-perps`) has no product account** — it trades on Hyperliquid: one-time `enable-unified-account` + `deposit` (not `create-account`).

**Multi-action → one bundle.** For any goal needing more than one action (rebalance, move between vaults, swap-then-deposit), use the product's **bundle**-style command (takes an `--actions '[…]'` list) to combine them into a **single atomic transaction**. Don't chain separate signed txs. There is no `rebalance` command — a rebalance *is* a bundle. See `recipes.md`.

**Prepare → sign → submit.** Some actions return EIP-712 / order data for the user to sign, then a second command submits the signature:
- perps order commands → sign → the perps **`execute`** command
- the equities **`order`** command → sign → its **order-submit** command
- any action with the **gas-sponsorship** flag → sign → the **gas-sponsorship prepare** command

**Read-only vs action.** List / markets / positions / balances / quote commands are read-only — show the result. Deposit / borrow / order / manage / bundle commands return an unsigned tx or EIP-712 → complete it with the user's key (`cast` — see `signing.md`); compass never signs.
