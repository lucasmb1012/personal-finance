# Data Policy

## Public repository rule

No real financial or personal data may enter Git, issues, pull requests, releases, documentation, screenshots, logs, or test fixtures.

This includes bank and card exports, brokerage statements, transaction CSVs, invoices, account balances, account identifiers, email bodies, email metadata, OAuth tokens, API keys, addresses, phone numbers, and screenshots derived from a real account.

## Generic public artifacts

Public artifacts describe financial sources generically. Do not name the operator's banks, card products, or other details that reveal where the operator holds accounts.

## Local-data workflow

- Real data may be processed locally when the operator explicitly requests it; it never enters the repository.
- Store private inputs only under an ignored directory such as `data/` or outside this checkout.
- Store OAuth client secrets and tokens under `secrets/` or outside this checkout. `.gitignore` matches `credentials.json` and `token.json` by name only.
- Keep configuration in local `.env` files; commit only a value-free example if one becomes necessary.
- Make fixtures from invented records with clearly fictional names, dates, amounts, and identifiers.
- Favor aggregate or generated outputs for demonstrations. Never rely on simple redaction of a real record.

## Before every commit

Run the checks below and read their output:

```sh
git status --short
git diff --cached --name-only
git diff --cached
```

If a change contains data of uncertain origin, do not stage or publish it. Ask before proceeding.
