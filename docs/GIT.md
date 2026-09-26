# Git Field Guide

Git is both an execution tool and an inspection tool. Start by asking Git what is true before asking it to change anything.

## Daily orientation

| Question | Command | What it tells you |
| --- | --- | --- |
| Where am I and what changed? | `git status --short --branch` | Current branch, relation to remote, changed files. |
| What changed but is not staged? | `git diff` | The exact working-tree patch. |
| What will be committed? | `git diff --cached` | The exact staged patch. |
| Which files are staged? | `git diff --cached --name-only` | A concise staging inventory. |
| What is recent history? | `git log --oneline --decorate -10` | Recent commits and branch pointers. |
| Who changed a line? | `git blame path/to/file.py` | Commit and author for each line. |
| Why was a string introduced? | `git log -S 'text' -- path/to/file.py` | Commits that added or removed it. |

## Safe change loop

```sh
git switch main
git pull --ff-only
git switch -c feat/short-description
# edit and test
git diff
git add path/to/intentional-file
git diff --cached --check
git diff --cached
git commit -m "feat: short imperative summary"
```

Push the branch and open a pull request. Consult the PR template rather than treating the merge as a formality.

## Before staging or publishing

For this repository, the three commands below are mandatory because they make accidental data disclosure visible:

```sh
git status --short
git diff --cached --name-only
git diff --cached
```

`git add -p` is preferable to broad staging because it asks you to review each hunk. Do not use `git add .` by habit.

## Useful recovery, with care

- Undo an unstaged edit to one file: first inspect `git diff -- path/to/file`; then use `git restore path/to/file` only if you intend to discard it.
- Unstage while preserving the edit: `git restore --staged path/to/file`.
- Find a lost reference: `git reflog`. Inspect the candidate commit before restoring anything.
- Repair a commit already pushed: prefer a new corrective commit or `git revert <commit>`; do not rewrite shared history.

Never run `reset --hard`, `clean`, force-push, or history rewriting commands until you understand their scope and have confirmed any uncommitted work is safe.
