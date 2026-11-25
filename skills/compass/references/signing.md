# Signing & broadcasting compass output

Compass is **non-custodial**: every action, whether you built it with the **[CLI]** or an **[MCP]** tool, returns something **unsigned**, either an **unsigned transaction** `{to, data, value, chainId}` or **EIP-712 typed data**. Neither surface holds keys, signs, or broadcasts. The user completes that last step with their **own wallet or key**. There are two ways, and which one applies depends on the surface:

| Where you are | What came back | How the user signs |
|---------------|----------------|--------------------|
| **[MCP]**, the client shows the signing panel | `transaction` or `eip_712` | In the panel (section 1). The default on MCP |
| **[MCP]**, perps or a tokenized equity order | Hyperliquid `typed_data`, an order message | By hand (section 2): the panel does not cover these payloads |
| **[MCP]**, the user says there is no panel | anything | By hand (section 2) |
| **[CLI]** | anything | By hand (section 2) |

## 1. [MCP] The signing panel

On clients that render MCP Apps views (Claude's chat apps, for example), every tool whose result has a `transaction` or an `eip_712` field also shows the user a **signing panel** next to that result. The server's on-connect instructions carry a "SIGNING PANEL" paragraph when it is on.

What the user sees: the panel opens a Compass signing page in their browser. The page shows what the request does (action, amounts, tokens, chain, owner, and a warning when funds go to someone other than the owner), and only the expected account can sign it. They connect their wallet, sign, and the panel reports the outcome back into the chat.

What you do:

1. **Call the tool.** Tell the user in a line or two what the request does and that the panel is waiting for them. Do not paste the payload or any signing command.
2. **Wait for a user message** with the outcome:
   - **Transaction** → a transaction hash. It means the transaction was **sent**, not that it succeeded: it can still be pending or revert. Continue the flow from it and confirm with a positions or balances read before relying on it.
   - **Typed data** (gas sponsorship) → the signer and a signature. Pass the signature and the **same** typed data to the gas-sponsorship prepare tool. That returns the transaction a sponsor sends, with a panel of its own.
3. **Then** build the next step.

Things that come up:

| Situation | What to do |
|-----------|------------|
| The user says the link expired or the request is no longer available | A request lives 15 minutes from when it was built. Call the tool again |
| The user wants a different amount, token or recipient | Call the tool again with new arguments. Never retype or edit a payload: the panel signs only what the server built |
| The result has `transaction: null` | Nothing to sign (the account already exists). Move on |
| The user pastes a hash themselves | Normal for a smart-contract wallet, whose transaction the page cannot match to the request. Treat it like any other hash |
| The user says there is no panel | Their client does not render it (terminal agents do not). Use section 2 |
| A perps action or a tokenized equity order | No panel for these. Use section 2 |

**Do not ask the user to sign by hand unless they tell you the panel is missing.**

## 2. By hand, with `cast`

For the **[CLI]**, and for **[MCP]** where there is no panel. This uses [Foundry's `cast`](https://book.getfoundry.sh/cast/); the only difference between the backends is that the "second command" for EIP-712 flows is a tool call on MCP rather than a shell command.

> **Keys stay with the user.** Sign from an **encrypted keystore** or a **hardware wallet**, never paste a raw private key on the command line (it leaks into shell history and the `ps` process list). Set a keystore up once:
> ```bash
> cast wallet import my-wallet --interactive   # paste the key once → stored encrypted; thereafter use --account my-wallet
> ```
> For real funds prefer `--ledger` / `--trezor` over any software key.

### Which path? Look at what came back

| compass returned… | What you do | Tool |
|-------------------|-------------|------|
| **Unsigned transaction** `{to, data, value, chainId}`: deposit, borrow, manage, transfer, bundle… | sign a transaction, then broadcast it | `cast send`, or `cast mktx` + `cast publish` |
| **EIP-712 typed data**: perps and tokenized equity orders, gas sponsorship | sign a message off-chain, feed the signature to the **second** compass command or tool | `cast wallet sign` |

### A. Unsigned transaction → sign + broadcast

Pass compass's `data` hex in the `[SIG]` position: `cast` accepts raw calldata there (no function signature needed).

**Default: sign without broadcasting (most non-custodial), then let the user push it:**
```bash
cast mktx <to> <data> --value <value> --rpc-url "$RPC_URL" --account my-wallet   # → 0x<signedRawTx>
# hand 0x<signedRawTx> back to the user, or broadcast it on their explicit OK:
cast publish 0x<signedRawTx> --rpc-url "$RPC_URL"
```

**Or sign + broadcast in one step, only after the user confirms (this spends funds and is irreversible):**
```bash
cast send <to> <data> --value <value> --rpc-url "$RPC_URL" --account my-wallet
```
- `--value` is only needed when compass's `value` is non-zero.
- `cast` reads chain id, nonce, and gas from `--rpc-url`; the user supplies an RPC for the tx's `chainId` (e.g. `$BASE_RPC_URL`).
- If time has passed since the command ran, re-fetch the unsigned tx from compass before broadcasting (nonce / gas can drift).

### B. EIP-712 typed data → sign, then submit via compass

Save compass's EIP-712 JSON verbatim to a file, sign it, then feed the signature into the **second** compass command or tool. (Names are version-specific: confirm via `--help` or the tool list.)
```bash
# a perps/equities order or a gas-sponsored action returns EIP-712 JSON → save it as td.json
cast wallet sign --data --from-file td.json --account my-wallet      # → 0x<signature>
```
Then submit:
```bash
compass <perps-group> execute --action '<from prepare>' --nonce <n> --signature 0x<signature>   # perps
# equities:        the order-submit command takes the signature
# gas-sponsorship: the gas-sponsorship prepare command takes --signature with --sender = the sponsor
```
`cast wallet sign` also accepts the JSON inline (`--data '<json>'`, skip `--from-file`); a file is cleaner for large payloads.

### Always confirm before spending

Broadcasting (`cast send` / `cast publish`) and submitting a signed order move real funds and cannot be undone. Preview first (**[CLI]** `--dry-run`; **[MCP]** read the returned payload), tell the user exactly what will happen, and proceed only on an explicit go-ahead.

### No Foundry installed? web3.py fallback

```python
# Unsigned tx: build an EIP-1559 dict (type=2) from compass's JSON, then:
signed = Account.sign_transaction(tx, key)          # key from the user's secret store — never hard-code
w3.eth.send_raw_transaction(signed.raw_transaction)
w3.eth.wait_for_transaction_receipt(signed.hash)
# EIP-712: Account.sign_typed_data(...) → pass the signature to the second compass command
```
