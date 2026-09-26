# Threat Model — Email Notification Ingestion

**Scope:** the Gmail adapter that reads the operator's own mailbox to discover card-transaction notifications.
**Status:** initial version, 2026-09-25. Revisit before each change to access scope, storage, or retention.

## Assets

- OAuth client secret and OAuth tokens.
- Email content and metadata.
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
| A token is leaked or stolen. | Revoke the app's access in the Google account, delete the local token, and follow [SECURITY.md](../SECURITY.md). | Documented |

## Accepted risks

- On the operator's explicit request, a coding agent may read local data. Content read that way is sent to the agent's provider; it never enters the repository.

## Open items

- A retention policy for email content.
