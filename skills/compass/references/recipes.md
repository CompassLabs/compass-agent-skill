# Compass patterns

> **Patterns, not exact syntax.** Command and flag *names* change between versions — always resolve them from the binary. The blocks below are **illustrative shapes**: angle-bracket placeholders (`<earn-group>`, `<manage-cmd>`) mean "find the real name via `--help`". Flags shown are typical but confirm them too.
>
> **[MCP] equivalence.** These recipes are written as CLI commands, but each maps 1:1 to an MCP tool call: the `<group> <command>` is a tool name (e.g. `v2_earn_bundle`) and every `--flag value` / `--flag.nested value` is a JSON field (`{"actions":[…]}`). Same order of operations (read → account → build → sign), same `action_type` bundle bodies — you just pass JSON instead of flags and read JSON back instead of using `--jq` / `-o toon`.

## The loop for every action

```bash
compass --help                          # which product groups exist
compass <group> --help                  # which command does the action
compass <group> <command> --help        # exact flags (watch for nested --a.b.c)
compass <group> <command> … --dry-run   # verify the request shape, no API call
compass <group> <command> …             # run → sign the unsigned tx / EIP-712 with the user's key (see signing.md)
```

Pass plain values by default; JSON-quote a single flag only if it errors with `unmarshalling json response body` (older versions). Read-only results you show directly; action results (unsigned tx / EIP-712) go to the user's wallet — the CLI never signs. How to actually sign (the `cast` commands for each output type) and broadcast: see `signing.md`.

## Deposit into a yield venue
Inputs the `manage`-style command needs: a **venue** (vault address, Aave token, or Pendle market — usually a nested `--venue.*` flag), an **action** (deposit/withdraw), an **amount**, the **owner**, the **chain**. Find a venue first via the vault/market listing command.
> Prereq: deposits move funds from the user's **Earn Account** — create + fund it first if needed.
```bash
# illustrative — confirm names/flags via --help
compass <earn-group> <list-vaults> --chain base --asset-symbol USDC --order-by tvl_usd --direction desc --jq '.vaults'
compass <earn-group> <manage> --venue.vault.vault-address 0x<v> --action DEPOSIT --amount 100 --owner 0x<o> --chain base
```

## Rebalance / any multi-step → ONE bundle  ⭐
Build the action list and submit it as a single atomic transaction (one signature) via the product's bundle command. The `action_type` values (`V2_MANAGE`, `V2_SWAP`, …) are API-level and more stable than CLI names.
```bash
compass <earn-group> <bundle> --owner 0x<o> --chain base --actions '[
  {"body":{"action_type":"V2_MANAGE","venue":{"type":"VAULT","vault_address":"0x<A>"},"action":"WITHDRAW","amount":"100"}},
  {"body":{"action_type":"V2_SWAP","token_in":"USDC","token_out":"AUSD","amount_in":"100","slippage":"0.5"}},
  {"body":{"action_type":"V2_MANAGE","venue":{"type":"VAULT","vault_address":"0x<B>"},"action":"DEPOSIT","amount":"100"}}
]'
# → ONE unsigned tx for the whole rebalance. There is no rebalance command; this bundle is the rebalance.
```

## Borrow / repay (credit)
Inputs: owner, chain, collateral token, borrow/repay token, amount. Prereq: a Credit Account (create + fund). Combine e.g. borrow+swap or repay+withdraw atomically with the credit bundle command. Each action returns an unsigned tx.

## Leverage — loop / unloop (credit)  ⭐
Open a leveraged position in ONE tx: the loop command supplies your initial collateral, then borrows → swaps → re-supplies for several iterations to reach a target leverage. Unloop reverses it. Prereq: a Credit Account already holding the initial collateral (create + fund first).

- **Protocol.** The same loop/unloop commands cover Aave (default), Morpho (needs the market's `market-id`), and Euler. Euler positions are keyed by an **EVK vault pair** (a collateral vault + a borrow vault, from the euler-markets listing) plus an optional **sub-account** id (0–255) that isolates each position with its own health — pass those extra flags only for Euler. Confirm the exact flag names via `--help`.
- **Sizing.** Give the initial collateral amount (already in the account) plus a target: a **multiplier** (total exposure = multiplier × initial) and/or a per-iteration **loan-to-value** expressed **in percent** and kept under the market's max borrow LTV. The response `preview` reports the achieved multiplier, projected LTV, and health factor before you sign.
- **Embedded swap → broadcast promptly.** Every iteration swaps the borrowed token back to collateral at a *live* quote, so the returned tx carries a min-out that goes stale within seconds. Broadcast right after building, and give the swap room with a max-slippage of ~1% — a tight 0.5% often misses min-out and reverts the whole atomic tx.
- **Closing (unloop).** Omit the target-multiplier for a **full unwind** — debt is cleared exactly (accrued interest included) and all pair collateral is withdrawn back to the account; pass `1` to clear debt but leave collateral supplied, or a value `>1` to delever partway. A near-liquidation position that can't unwind in one tx takes an allow-partial flag, then a second unloop from lower leverage.
- **Reading it back.** Open loops show in the credit **positions** command (Euler reports per-sub-account health). The dedicated **looped-positions** command is Aave/Morpho-only — an Euler loop returns `[]` there, so read Euler leverage from positions instead.

```bash
# illustrative — confirm names/flags via --help; broadcast promptly (live swap quote)
compass <credit-group> loop --owner 0x<o> --chain base --collateral-token USDC --borrow-token WETH \
  --initial-collateral-amount 10 --multiplier 2 --loan-to-value 70 --max-slippage-percent 1
  # Euler also needs: --collateral-vault 0x<c> --borrow-vault 0x<b> --sub-account-id <n>
compass <credit-group> unloop --owner 0x<o> --chain base --collateral-token USDC --borrow-token WETH \
  --max-slippage-percent 1            # omit target-multiplier → full close (Euler: same vault pair + sub-account)
```
Each returns an unsigned tx → sign + broadcast with the user's key (see `signing.md`).

## Perps order — prepare → sign → execute
One-time: enable the perps account, deposit USDC (and approve a builder fee if you'll use one). Then an order command (market/limit) **prepares** EIP-712 → user signs → submit via the perps **`execute`** command. Order inputs: owner, asset ticker (e.g. `AAPL`), side (`buy`/`sell`), size, optional slippage. Read-only: opportunities, positions, candles, activity.
```bash
compass <perps-group> <market-order> --owner 0x<o> --asset AAPL --side buy --size 10 --slippage-percent 1
# user signs the returned EIP-712, then:
compass <perps-group> execute --action '<from prepare>' --nonce <n> --signature 0x<sig>
```

## Tokenized equity order — quote → order → sign → submit
Quote (read-only) → order (returns an order message + hash) → user signs off-chain → submit via the order-submit command. Track via order-status; cancel via the cancel command. Prereq: create the account once.

## Gas-sponsored action (sponsor pays gas)
Add the gas-sponsorship flag to an action to get EIP-712 instead of a tx → user signs → submit to the **gas-sponsorship prepare** command with the sponsor as sender → sponsor broadcasts and pays gas.

## Risk / portfolio analysis
`compass risk-recipes` prints the formulas (LLTV cascade, jump-to-default, vault correlation, withdrawable share of TVL) with jq snippets. LLTV cascade is the one to get right: Morpho ships LLTV as a uint256 scaled by 1e18, and bad debt is continuous (`1 − 1/newLtv`), not a binary trip-flag.
