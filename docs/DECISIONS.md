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
