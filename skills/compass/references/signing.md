# Signing & broadcasting compass output

`compass` is **non-custodial**: every action command returns something **unsigned** — either an **unsigned transaction** `{to, data, value, chainId}` or **EIP-712 typed data**. The CLI never holds keys, signs, or broadcasts. This is how to complete that last step with the **user's own key**, using [Foundry's `cast`](https://book.getfoundry.sh/cast/).

> **Keys stay with the user.** Sign from an **encrypted keystore** or a **hardware wallet** — never paste a raw private key on the command line (it leaks into shell history and the `ps` process list). Set a keystore up once:
> ```bash
> cast wallet import my-wallet --interactive   # paste the key once → stored encrypted; thereafter use --account my-wallet
> ```
> For real funds prefer `--ledger` / `--trezor` over any software key.

## Which path? Look at what the command returned

| compass returned… | What you do | Tool |
|-------------------|-------------|------|
| **Unsigned transaction** `{to, data, value, chainId}` — deposit, borrow, manage, transfer, bundle… | sign a transaction, then broadcast it | `cast send`, or `cast mktx` + `cast publish` |
| **EIP-712 typed data** — perps & equities orders, gas-sponsorship | sign a message off-chain, feed the signature to the **second** compass command | `cast wallet sign` |

## A. Unsigned transaction → sign + broadcast

Pass compass's `data` hex in the `[SIG]` position — `cast` accepts raw calldata there (no function signature needed).

**Default — sign without broadcasting (most non-custodial), then let the user push it:**
```bash
cast mktx <to> <data> --value <value> --rpc-url "$RPC_URL" --account my-wallet   # → 0x<signedRawTx>
# hand 0x<signedRawTx> back to the user, or broadcast it on their explicit OK:
cast publish 0x<signedRawTx> --rpc-url "$RPC_URL"
```

**Or sign + broadcast in one step — only after the user confirms (this spends funds and is irreversible):**
```bash
cast send <to> <data> --value <value> --rpc-url "$RPC_URL" --account my-wallet
```
- `--value` is only needed when compass's `value` is non-zero.
- `cast` reads chain id, nonce, and gas from `--rpc-url`; the user supplies an RPC for the tx's `chainId` (e.g. `$BASE_RPC_URL`).
- If time has passed since the command ran, re-fetch the unsigned tx from compass before broadcasting (nonce / gas can drift).

## B. EIP-712 typed data → sign, then submit via compass

Save compass's EIP-712 JSON verbatim to a file, sign it, then feed the signature into the **second** compass command. (Command names are version-specific — confirm via `--help`.)
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
`cast wallet sign` also accepts the JSON inline (`--data '<json>'`, skip `--from-file`) — a file is cleaner for large payloads.

## Always confirm before spending

Broadcasting (`cast send` / `cast publish`) and submitting a signed order move real funds and cannot be undone. Preview with compass `--dry-run` first, tell the user exactly what will happen, and proceed only on an explicit go-ahead.

## No Foundry installed? web3.py fallback

```python
# Unsigned tx: build an EIP-1559 dict (type=2) from compass's JSON, then:
signed = Account.sign_transaction(tx, key)          # key from the user's secret store — never hard-code
w3.eth.send_raw_transaction(signed.raw_transaction)
w3.eth.wait_for_transaction_receipt(signed.hash)
# EIP-712: Account.sign_typed_data(...) → pass the signature to the second compass command
```
