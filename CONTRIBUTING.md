# Contributing

## Contribution contract

This is a public repository. Contributions must contain no real financial data, personally identifiable information, credentials, account numbers, copied emails, or screenshots of real accounts. Examples and test fixtures must be invented and visibly synthetic.

Read [docs/DATA_POLICY.md](docs/DATA_POLICY.md) and [docs/GIT.md](docs/GIT.md) before your first change.

## Workflow

1. Start from an up-to-date `main` and create a focused branch, such as `feat/csv-validation` or `docs/data-policy`.
2. Make one coherent change. Keep unrelated refactors separate.
3. Add or update tests and documentation where behavior or decisions change.
4. Run the relevant checks:

   ```sh
   uv run python -m unittest discover -s tests
   git diff --check
   git status --short
   ```

5. Inspect exactly what will be committed:

   ```sh
   git diff --cached --check
   git diff --cached --name-only
   git diff --cached
   ```

6. Use a Conventional Commit-style message: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `build:`, or `chore:` followed by an imperative summary.
7. Open a pull request against `main` using the provided template.

## Pull-request standard

A pull request should be small enough to review, have a clear purpose, include test evidence, and describe its data/privacy impact. A change must not merge when its data origin is unclear, it introduces an unreviewed dependency or service, it lacks appropriate tests, or its CI checks fail.

The repository owner is the required reviewer while the project is maintained by one person. If GitHub branch protection is enabled, configure `main` to require a passing status check and a pull request before merge. GitHub may not permit self-approval on a personal repository; in that case, use the PR as an auditable review record and merge only after completing the template.
