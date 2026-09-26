# Security and Data Disclosure Policy

## Reporting

Do not open a public issue for a suspected exposure of financial data, credentials, or personal information. Contact the repository owner privately through GitHub instead.

Include the affected file or commit, the type of data, whether it was pushed, and whether access credentials may be valid. Do not reproduce sensitive values in the report.

## Immediate response

1. Stop committing and pushing the affected material.
2. Revoke or rotate exposed credentials with the relevant provider.
3. Remove the data from the working tree and repository history as appropriate.
4. Assess forks, clones, releases, and caches: a public push cannot be assumed recoverable.
5. Document the remediation without restating the exposed values.

Git ignore rules reduce accidental staging; they are not a security control or a substitute for review.
