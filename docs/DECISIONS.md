# Decision Log

This log records decisions that are expensive to reverse, affect privacy, or shape the public project. Add a new entry when a decision is made; do not rewrite history to make old decisions look current.

## 2026-09-25 — Public repository with a local-data boundary

**Decision:** Keep the repository public, while excluding real data and credentials from version control. Commit only synthetic examples.

**Rationale:** The code and engineering process are useful portfolio artifacts. Financial records are not.

**Consequences:** Privacy review is required for every change. Documentation and tests need fabricated data. A data exposure requires immediate remediation.

## 2026-09-25 — Start with Python and uv; defer infrastructure

**Decision:** Use Python 3.13+ and `uv`. Do not select a database, cloud provider, or application framework until a concrete stage requires it.

**Rationale:** The project is at foundation stage; early infrastructure choices would be speculative.

**Consequences:** The early delivery stages focus on a clean domain model, file ingestion, validation, and tests.

## 2026-09-25 — Explicit local processing of real financial data

**Decision:** Real financial data may be processed locally when the operator explicitly requests it and the task requires it. It must never enter the repository: version control, code, tests, fixtures, documentation, issues, or pull requests.

**Rationale:** The application needs to operate on the operator's financial records, while the public repository must remain free of sensitive data.

**Consequences:** Access to sensitive local data requires explicit operator direction. Public artifacts continue to use only fictional fixtures.

## 2026-09-25 — Gmail read-only client libraries

**Decision:** Use Google's Python OAuth and Gmail API client libraries for the Gmail adapter.

**Rationale:** They are Google's official, maintained libraries for OAuth and the Gmail API, and the authentication flow has been validated locally with them. Gmail access is required for transaction notification discovery.

**Consequences:** OAuth client secrets and tokens must be stored under `secrets/` or outside the checkout; `.gitignore` matches `credentials.json` and `token.json` by name only. The token file is written with owner-only permissions. The adapter requests the Gmail read-only scope.

## 2026-09-25 — Prioritize email notification ingestion

**Decision:** Move email notification ingestion ahead of spreadsheet ingestion in the roadmap.

**Rationale:** Card-transaction notification emails are the primary source of records.

**Consequences:** The email stage keeps its original safeguards: a threat model ([THREAT_MODEL.md](THREAT_MODEL.md)), least-privilege access, a retention policy, and secure credential handling are exit criteria.

## 2026-09-25 — Keep financial institutions out of public artifacts

**Decision:** Public artifacts describe financial sources generically and do not name the operator's banks, card products, or similar details.

**Rationale:** Combined with the owner's public identity, institution names reveal where the operator holds accounts.

**Consequences:** Documentation uses generic guidelines. Provider-specific details must not be committed: Gmail search queries load from `secrets/gmail_searches.toml`, and the repository ships only a fictional example in `examples/`.
