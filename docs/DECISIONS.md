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

## 2026-09-26 — Survey notification formats before defining the transaction model

**Decision:** Collect and document every notification format, and the fields each one carries, before defining the Stage 1 transaction model.

**Rationale:** Real notifications carry fields and variations that were not anticipated, such as a second currency with a different number format and account-based rather than card-based identifiers. A model designed before the survey would likely need reshaping.

**Consequences:** Stage 1 follows the notification survey instead of preceding it. The survey runs locally on real data under the explicit-processing decision; only generic findings and synthetic fixtures enter the repository.

## 2026-09-26 — Mailbox synchronization: polling first, push later

**Decision:** Synchronize the mailbox in three steps. First, poll for changes since the last synchronization using the Gmail history API. Later, add push notifications through a Google Cloud Pub/Sub pull subscription. Eventually, add a push subscription that delivers to an HTTPS endpoint (a webhook). All three triggers call the same synchronization routine.

**Rationale:** Polling needs no public endpoint or cloud resource and runs on the operator's computer. It is also required regardless of the trigger: backfill, recovery after downtime, and missed push notifications all depend on catching up from the last known position. Real-time delivery adds little value for personal finance, but the push steps are a deliberate learning goal (message queues, event delivery, idempotency, retries, and exposing a secured service). A pull subscription delivers events in near real time without exposing an endpoint, so it is an intermediate step before the webhook.

**Consequences:** The synchronization routine must be idempotent and must track its last processed position. The push steps require a Pub/Sub topic, a Gmail watch that is renewed at least every seven days, and, for the webhook, a public authenticated endpoint. Each push step needs its own threat model update before implementation. Polling remains in place as the catch-up path after push is added.

## 2026-09-26 — Run locally first; defer cloud hosting

**Decision:** Run the system on the operator's computer. Cloud hosting may be considered later, together with the webhook step.

**Rationale:** Local execution keeps financial data on the operator's machine and needs no cloud account setup beyond the existing OAuth client. A webhook requires an always-on public endpoint, so cloud hosting and the webhook are evaluated together.

**Consequences:** Synchronization only runs while the computer is on and catches up when it resumes. Moving to the cloud will require a separate decision covering where financial data is stored, who can access it, encryption, and cost.

## 2026-09-26 — PostgreSQL as the transactional database

**Decision:** Use PostgreSQL as the transactional database, running locally. This decision selects the engine; it does not introduce the database yet. The installation method, schema, and migration strategy are decided when Stage 4 starts.

**Rationale:** The requirements come from the data and the planned architecture:

- Timestamps with time zones: notifications state local times without an offset, while message headers use UTC or other offsets, and the local offset changes with daylight saving time. `timestamptz` stores unambiguous instants.
- Exact amounts in more than one currency: amounts arrive in whole units in one currency and with two decimals in another. `numeric` stores them exactly; floating-point types are ruled out.
- An immutable event record next to derived records: `jsonb` can hold raw event payloads, and unique constraints enforce idempotent ingestion by message identifier.
- Concurrent processes: a synchronizer, a parser, and later a push listener write at the same time.
- A path to cloud hosting: managed PostgreSQL is widely available, so a later move does not require changing engines.
- Learning value: PostgreSQL is a widely used production database, which serves the project's portfolio goal.

Alternatives considered:

- SQLite: a single file with no server, included with Python, and sufficient for one user. Rejected because it allows only one writer at a time and has no native time-zone-aware timestamp or exact decimal types. It would need a migration once concurrent processes or hosting arrive.
- DuckDB: an embedded analytical database, suited to reporting rather than frequent small writes. It may complement PostgreSQL for Stage 5 analysis.
- MySQL: offers no advantage over PostgreSQL for these requirements.
- Document databases such as MongoDB: financial records are relational and benefit from enforced constraints between tables.

**Consequences:** This supersedes the database deferral in the 2026-09-25 infrastructure entry. Local development will need a PostgreSQL server, which adds setup, upgrades, and backups to the operator's responsibilities. Backup and retention guidance becomes part of Stage 4. Money is never stored as a floating-point value.

## 2026-09-26 — Pseudonymous institutions and local provider profiles

**Decision:** Refer to financial institutions in public artifacts as Bank A, Bank B, and so on, and never record which real institution each pseudonym stands for. Describe notification wording instead of quoting it. Parse notifications with a generic engine that loads each institution's sender, subjects, sentence patterns, and amount formats from an ignored local profile under `secrets/`. Tests use a fictional institution's profile.

**Rationale:** Quoted notification wording or parsing patterns in public code would identify the institution through a simple web search, which defeats the decision to keep institutions out of public artifacts. Knowing the institution gives a scammer a credible script for targeted phishing, and published information cannot be withdrawn, so hiding it is the reversible choice. A profile-driven engine also lets a second institution be added by writing a profile rather than new code.

**Consequences:** The engine must be flexible enough to express each institution's formats. If a later institution cannot be expressed as a profile, a private companion repository for provider-specific parsers will be evaluated. Publishing an institution-specific parser would require a new decision.

## 2026-09-26 — Keep the repository public; private companion repository as a future option

**Decision:** Keep the repository public. A split into a public engine plus a private companion repository for provider profiles and notes remains a possible future scenario, not a current plan.

**Rationale:** Keeping institutions hidden raised the question of whether the privacy work costs more than a public repository is worth. The options considered were:

- Public (chosen): the project's value as a portfolio lies in its engineering decisions, architecture, and privacy practices, which are visible only if the repository is public. Most of the privacy cost is structural and would be paid anyway: real data stays out of any hosted repository, synthetic fixtures are good practice, and provider profiles are needed to support a second institution. The remaining cost, generic documentation and pseudonyms, is small.
- Private: somewhat faster, and notes could name institutions. However, the project could not be shown publicly, and making it public later would expose its entire history. It would have to be republished as a new, clean repository.
- Public engine with a private companion repository: combines both benefits, but maintaining and versioning two repositories together is too much overhead at this stage.

**Consequences:** The data boundary and pseudonym rules continue to apply to every public artifact. The companion repository will be reconsidered if privacy work materially slows progress, if an institution cannot be expressed as a local profile, or if deployment configuration would reveal institution details.

## 2026-09-26 — pdfplumber for reading statement PDFs

**Decision:** Use `pdfplumber` to read account and card statements delivered as PDF files. Only the PDF adapter (`personal_finance/statements/pdf.py`) imports it.

**Rationale:** Statements are tables. In plain extracted text a debit and a credit look identical, so parsing depends on each word's position on the page, which `pdfplumber` provides. It also opens password-protected files. Alternatives considered:

- `pypdf`: lighter, but it extracts text without positions, which loses the table columns.
- `PyMuPDF`: faster, but its AGPL license is restrictive, and speed does not matter at a few files per month.

**Consequences:** The dependency brings `pdfminer.six`, `pypdfium2`, and `Pillow` with it. The parsing engines work on positioned words rather than PDF objects, so the library can be replaced by rewriting only the adapter.

## 2026-09-26 — Statement parsing: generic engines, local profiles, and reconciliation

**Decision:** Parse statements with two generic engines driven by local profiles, as decided for notifications:

- A column-table engine for account statements: each word is assigned to a column by the horizontal position of its left or right edge.
- A line-pattern engine for card statements: each entry is one text line matched by a pattern with named fields, grouped into sections and parts (for example, one part per currency).

Profiles hold the institution's titles, column positions, patterns, and number formats in `secrets/statement_profiles.toml`; the repository ships a fictional example. Every parse also produces reconciliation checks: account balances are replayed from the opening balance and compared with each stated balance, and card entries are summed and compared with each stated total and with the amount due.

**Rationale:** A statement's layout identifies its institution, so the reasoning of the pseudonymous-institutions decision applies. The two techniques covered every statement surveyed. Reconciliation turns an unrecognized line into a failed check instead of a silently missing transaction, which matters more than parsing speed or convenience.

**Consequences:** Parsing output keeps named fields as the statement states them; mapping them to the transaction model is Stage 1 work. A layout change shows up as failed checks, and the profile is updated locally. Tests use synthetic words and a generated PDF, never a real statement.
