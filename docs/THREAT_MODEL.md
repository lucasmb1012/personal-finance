# Threat Model — Email Notification and Statement Ingestion

**Scope:** the Gmail adapter that reads the operator's own mailbox to discover card-transaction notifications and statement attachments, and the statement parser that reads those PDF files locally.
**Status:** revised 2026-09-26. Revisit before each change to access scope, storage, or retention.

## Assets

- OAuth client secret and OAuth tokens.
- Email content and metadata.
- Statement PDF files and their passwords.
- Transactions derived from notifications.
- The identity of the operator's financial institutions.

## Consent

The operator runs the OAuth consent flow on their own machine for their own account. No third-party mailboxes are accessed.

## Threats and safeguards

| Threat | Safeguard | Status |
| --- | --- | --- |
| Secrets or tokens are committed. | Store them under `secrets/` or outside the checkout; review staged files before every commit. Ignore rules are defense in depth only. | In place |
| Another local user or process reads the token. | Write the token file with owner-only permissions (`0600`). | In place |
| Access is broader than needed. | Request only the `gmail.readonly` scope; never send, modify, or delete mail. | In place |
| Real email content enters the repository through fixtures, tests, logs, or documentation. | Synthetic fixtures only, never redacted copies; search returns message IDs without fetching bodies. | In place |
| Public artifacts reveal where the operator holds accounts. | Generic documentation; search queries load from an ignored local file under `secrets/`, and the repository ships only a fictional example. | In place |
| Forged emails imitating a financial institution inject fake transactions. | Accept only messages whose `Authentication-Results` header reports `dmarc=pass`. | Planned |
| Parsing patterns quote notification wording and reveal the institution. | A generic parsing engine loads institution-specific patterns from ignored local profiles under `secrets/`; tests use a fictional institution. | Planned |
| Statement layouts in parsing code reveal the institution. | Statement engines load titles, column positions, and patterns from an ignored local profile under `secrets/`; tests use a fictional profile and synthetic words. | In place |
| A statement's password protection is relied on. | The password is a short number, so a stolen file can be opened by trying every combination. Statement files are treated as unprotected sensitive data: they stay under the ignored `data/` directory with owner-only permissions. | In place |
| The statement password leaks. | The parser reads it from an environment variable or a prompt; it is never written to the repository or to a profile. | In place |
| A statement is parsed incompletely and transactions go missing. | Every parse produces reconciliation checks against the balances and totals the statement states; a failed check marks the file for review. | In place |
| A token is leaked or stolen. | Revoke the app's access in the Google account, delete the local token, and follow [SECURITY.md](../SECURITY.md). | Documented |

## Accepted risks

- On the operator's explicit request, a coding agent may read local data. Content read that way is sent to the agent's provider; it never enters the repository.
- During the notification survey, a few sample emails were stored as `.eml` files under the ignored `data/raw/` directory with owner-only permissions. They stay local until a retention policy is decided.
- During the statement survey, sample statement PDFs were stored under `data/raw/statements/` with owner-only permissions, under the same terms.
- Statement parser output printed to the terminal includes amounts from failed checks. It stays on the operator's machine.

## Open items

- A retention policy for email content and statement files.
- Storing the statement password in the operating system's credential store before automating statement ingestion.
