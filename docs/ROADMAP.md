# Roadmap

The roadmap is intentionally stage-based. A stage is complete only when its exit criteria are met; it is not a promise of dates or a commitment to premature technology choices.

## Stage 0 — Foundation

**Goal:** Make public collaboration, privacy, and development workflow safe and legible.

**Exit criteria:** repository documentation, data policy, Git/PR workflow, and initial package checks are in place.

## Stage 1 — Core financial model

**Goal:** Define a minimal domain model for accounts, transactions, categories, dates, amounts, and currencies.

**Exit criteria:** documented invariants; synthetic fixtures; parsing-independent unit tests; explicit treatment of transfers, duplicates, and invalid values.

## Stage 2 — Email notification and statement ingestion

**Goal:** Discover and parse card-transaction notification emails from the operator's mailbox with read-only access, and parse the monthly statements that arrive as email attachments for backfill and reconciliation.

**Exit criteria:** a reviewed [threat model](THREAT_MODEL.md); explicit consent flow; least-privilege access; secure credential handling; a documented retention policy for email content; provider-specific details kept out of public artifacts; parsing tests using only synthetic notifications and statements; statement parsing verified by reconciliation checks.

## Stage 3 — Local spreadsheet ingestion

**Goal:** Import one well-defined spreadsheet format from a local ignored directory.

**Exit criteria:** schema validation, actionable import errors, idempotent behavior, provenance metadata, and tests using only synthetic files.

## Stage 4 — Storage and query workflow

**Goal:** Persist validated records locally and provide repeatable queries.

**Exit criteria:** a documented storage decision, migrations or versioning strategy, reproducible local setup, and backup/retention guidance.

## Stage 5 — Reports and analysis

**Goal:** Produce useful, explainable summaries such as cash flow, category trends, and reconciliation checks.

**Exit criteria:** outputs are reproducible from synthetic data; calculation assumptions are documented; tests cover key financial edge cases.
