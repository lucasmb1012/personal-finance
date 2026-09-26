# Agent Instructions

These rules apply to Codex and every automated coding agent working in this repository.

## Non-negotiable data boundary

- Never read, print, commit, upload, summarize, or transform real financial records, credentials, personal identifiers, emails, tokens, or exports.
- Treat local `data/`, `private/`, `secrets/`, `.env*`, and files ignored by Git as sensitive. Do not inspect them unless the user explicitly asks and the action is necessary.
- Use synthetic, clearly fictional fixtures for tests and examples. A fixture must not be a redacted copy of a real record.
- Before staging changes, run `git diff --cached --check` and inspect `git diff --cached --name-only`.
- If private data may have been committed, stop work, do not push, and follow `SECURITY.md`.

## Engineering rules

- Keep all repository prose, identifiers, code comments, and user-facing messages in English.
- Make the smallest coherent change. Do not introduce a database, cloud service, framework, or dependency without a documented need and decision.
- Keep domain logic separate from file or provider adapters as the implementation emerges.
- Add or update tests for behavior changes. Run the relevant test command before handing off work.
- Record durable architecture, security, and data-model decisions in `docs/DECISIONS.md`.

## Git and review rules

- Work on a focused branch; never commit directly to `main`.
- Use Conventional Commit-style messages: `type: imperative summary` (for example, `feat: add CSV import validation`).
- Do not amend, force-push, reset, or discard user changes unless explicitly requested.
- Open a pull request using `.github/PULL_REQUEST_TEMPLATE.md`; it must explain privacy impact and test evidence.
- Consult `docs/GIT.md` before an unfamiliar Git operation. Prefer inspection commands before mutation.
