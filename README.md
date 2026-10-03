# Personal Finance

> A privacy-first, open-source personal-finance data platform. This repository is a portfolio project; it must never contain real financial data, credentials, or personal identifiers.

## Project brief

The project will turn personally owned financial exports into a local, inspectable data model and useful reports. The primary sources are card-transaction notification emails and the monthly statements that arrive as email attachments; spreadsheet exports follow. The intended outcome is a repeatable workflow for ingesting data, validating it, and producing analysis without turning private records into repository assets.

The repository is public by design. Real data stays on the operator's machine or in explicitly approved private services; only synthetic fixtures may be committed.

## Current stage

**Stages 1 and 2 in progress.** A read-only Gmail adapter authenticates locally and lists the IDs of notification emails that match locally configured searches. A statement parser reads PDF statements with generic engines driven by local profiles and checks every result against the balances and totals the statement states. Reconciled statements are mapped to a core model of accounts, statements, and signed transactions, stored in a local PostgreSQL database, and chained to detect missing statements. The delivery roadmap lives in [docs/ROADMAP.md](docs/ROADMAP.md).

## Operating principles

- Privacy is a product requirement, not an afterthought.
- Start with local, reproducible workflows and introduce services only when their value is proven.
- Prefer small, documented decisions over speculative architecture.
- Keep the public repository useful: examples and tests use invented, sanitized data only.
- Make every change reviewable, tested, and traceable through Git.

## Technology decisions

| Area | Decision | Why |
| --- | --- | --- |
| Language | Python 3.13+ | A strong fit for data processing and the project's existing foundation. |
| Package/dependency tooling | `uv` | Fast, reproducible environments and lockfiles. |
| Tests | Standard-library `unittest` initially | No extra dependency is needed for the current scope. Revisit when needs justify it. |
| Email access | Google's Gmail API and OAuth client libraries, read-only scope | Official, maintained libraries; least-privilege access to the mailbox. |
| Statement PDFs | `pdfplumber` | Word positions recover table columns; opens password-protected files. |
| Database | PostgreSQL in Docker Compose, `psycopg`, plain SQL migrations | Exact decimals and time zones; runs the same on any host with Docker. |
| Data boundary | Local files outside Git; synthetic committed fixtures only | Preserves public portfolio value without exposing private records. |
| Architecture | Evolve from validated use cases | Avoids committing early to a cloud provider or framework. |

Decisions that materially affect the project belong in [docs/DECISIONS.md](docs/DECISIONS.md).

## Getting started

Prerequisites: Python 3.13 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run python -m unittest discover -s tests
```

The local database needs Docker. Copy `.env.example` to `.env`, set a password, then:

```sh
docker compose up -d
uv run --env-file .env python -m personal_finance.store migrate
uv run --env-file .env python -m personal_finance.store load data/raw/statements/...
uv run --env-file .env python -m personal_finance.store check
uv run --env-file .env python -m personal_finance.store report
```

With `.env` loaded, the test suite also runs the database tests against the disposable database it names.

Do not place real exports, statements, credentials, or copied emails in this checkout. Read [docs/DATA_POLICY.md](docs/DATA_POLICY.md) before working with any financial source.

## Working in the repository

- [Contributing guide](CONTRIBUTING.md): branches, commits, tests, and pull requests.
- [Git field guide](docs/GIT.md): safe commands to inspect, understand, and recover work.
- [Roadmap](docs/ROADMAP.md): staged delivery plan and exit criteria.
- [Data policy](docs/DATA_POLICY.md): non-negotiable privacy rules.
- [Threat model](docs/THREAT_MODEL.md): risks and safeguards for email and statement ingestion.
- [Security policy](SECURITY.md): how to report a suspected disclosure.
- [Agent instructions](AGENTS.md): repository rules for Codex and other coding agents.

## Scope boundaries

This is not financial advice, a bank connection service, or a public dataset. Its public artifacts are code, documentation, schemas, and deliberately fictional examples.
