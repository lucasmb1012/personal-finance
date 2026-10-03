# Data Pipeline Principles

These principles guide every component that ingests, transforms, or stores data: the mailbox synchronizer, the notification and statement parsers, the ledger, and future reports. A change that weakens one of them needs a recorded decision in [DECISIONS.md](DECISIONS.md).

Each principle states the rule, how the project applies it today, and what is still missing.

## 1. Idempotency

**Rule:** Processing the same input twice leaves the same state as processing it once. Re-running a step is always safe.

**Today:** Statements are keyed by the SHA-256 of their source file, so a second load stores nothing. An account can hold only one statement per period end, which also rejects a different copy of the same statement. Migrations are recorded in `schema_migrations` and applied once.

**Missing:** Notifications will be keyed by their message identifier when they are ingested.

## 2. Determinism

**Rule:** The same inputs, profiles, and code produce the same outputs. Parsing and mapping do not depend on the clock, the network, the order of files, or floating-point arithmetic.

**Today:** The parsing engines and the ledger mapping are pure functions of positioned words and a profile. Amounts are exact decimals. The only time-dependent values are audit timestamps such as `loaded_at`.

**Missing:** Stored records do not say which version of a profile produced them, so a profile change, such as a new transfer pattern, is applied only by reloading. A profile fingerprint per statement would make that visible.

## 3. Incrementality

**Rule:** Each run processes only what is new since the last run, and a full rebuild produces the same result as the sum of incremental runs.

**Today:** Loading skips statements that are already stored. Rebuilding the database from the raw files gave the same result as loading them incrementally.

**Missing:** The loader parses a file before it checks whether that file is already stored. Mailbox synchronization will use the Gmail history API to fetch only changes since the last checkpoint.

## 4. State management and checkpoints

**Rule:** Progress is recorded durably, in the same database as the data, and a checkpoint advances only after the work it covers is committed.

**Today:** The stored statements and applied migrations are the pipeline's state. There is no separate progress file.

**Missing:** Mailbox synchronization needs a checkpoint table that holds the last processed history identifier. That checkpoint must be updated in the same transaction as the records it covers.

## 5. Delivery semantics

**Rule:** Assume at-least-once delivery from every source, and make processing idempotent so the result is effectively once. Never design for exactly-once delivery.

**Today:** Statements can be downloaded or loaded more than once without duplicates.

**Missing:** Gmail polling, Pub/Sub, and webhooks may all deliver the same change more than once or out of order. Their consumers must deduplicate by message identifier, and a notification must later be matched to the statement entry for the same transaction, so that one purchase is never counted twice.

## 6. Atomicity and consistency

**Rule:** A unit of work is stored completely or not at all, and the database enforces the invariants it can express.

**Today:** A statement, its balances, and its transactions are written in one database transaction, and each migration runs in its own transaction. A statement that fails any reconciliation check is rejected rather than stored partially. Foreign keys, unique constraints, and check constraints guard the schema.

**Missing:** The rule that a checking statement's transactions add up to its closing balance minus its opening balance is checked while parsing, not by the database.

## 7. Order and time

**Rule:** Results never depend on the order in which inputs arrive. Each date keeps its meaning: a calendar date stays a date, an instant is stored with its time zone, and every report states which date it groups by.

**Today:** Continuity checks order statements by period, not by load order, so a statement obtained late slots into place. Transaction dates are calendar dates. Card activity is reported by billing period, because installment entries carry the original purchase date.

**Missing:** Notifications state a local time without an offset and must be stored as `timestamptz` using the message's date header, as recorded in the transaction cases.

## 8. Recoverability

**Rule:** Everything derived can be rebuilt from preserved raw inputs. Raw inputs are kept unchanged, and a failure can be repaired by re-running a step.

**Today:** Original statement files are kept unchanged in the ignored `data/raw/` directory. The database was dropped and rebuilt from them with identical results.

**Missing:** Backups of the raw files and the database volume, and a retention policy for them, are Stage 4 exit criteria.

## 9. Observability

**Rule:** Every run reports what it did: how much it processed, skipped, and rejected, and why. Problems are detected by checks, not by noticing missing numbers. Messages and logs never echo private content.

**Today:** Loading reports loaded, already stored, and failed counts, and the reason for each failure. Reconciliation checks validate each statement, and `store check` reports continuity breaks across statements.

**Missing:** A persistent record of runs, with start time, counts, and outcome, that shows when the pipeline last ran successfully.

## 10. Data contracts and schema

**Rule:** Each boundary has an explicit, validated shape: provider profile, parsed record, ledger model, and database schema. An input that does not match is rejected with an actionable error, and every schema change is versioned.

**Today:** Profiles are validated when they are loaded, and errors name keys without echoing values. Parsed statements and ledger records are typed, immutable dataclasses. The database schema changes only through numbered migrations, and the ledger model documents its sign and identity invariants.

**Missing:** A version for the profile format, and contract tests that check each fictional example profile against the engines.
