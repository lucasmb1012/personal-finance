"""Parse local statement files and report whether each one reconciles.

Usage: python -m personal_finance.statements [--profiles PATH] [--profile NAME] FILE...

The PDF password is read from the STATEMENT_PDF_PASSWORD environment variable
or prompted for once. Output stays on the local terminal; it includes amounts
from failed checks, so do not paste it into public artifacts.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

from personal_finance.statements.column_table import parse_column_table
from personal_finance.statements.line_patterns import parse_line_patterns
from personal_finance.statements.models import Check, Word
from personal_finance.statements.pdf import read_words
from personal_finance.statements.profiles import (
    DEFAULT_LINE_TOLERANCE,
    ColumnTableProfile,
    Profile,
    load_profiles,
)
from personal_finance.statements.reconciliation import reconcile_account_statement
from personal_finance.statements.text import group_lines

DEFAULT_PROFILES = Path("secrets/statement_profiles.toml")
PASSWORD_VARIABLE = "STATEMENT_PDF_PASSWORD"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m personal_finance.statements")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--profile", help="profile name; detected per file when omitted")
    parser.add_argument("files", nargs="+", type=Path)
    arguments = parser.parse_args(argv)

    profiles = load_profiles(arguments.profiles)
    password = os.environ.get(PASSWORD_VARIABLE) or getpass.getpass("PDF password: ") or None

    failures = 0
    for path in arguments.files:
        try:
            words = read_words(path, password)
            profile = _select(profiles, arguments.profile, words)
            checks, entries = _parse(profile, words)
        except Exception as error:  # Report and continue with the next file.
            print(f"{path.name}: error: {type(error).__name__}: {error}")
            failures += 1
            continue
        failed = [check for check in checks if not check.passed]
        failures += bool(failed)
        print(
            f"{path.name}: profile {profile.name}, {entries} entries, "
            f"{len(checks) - len(failed)}/{len(checks)} checks passed"
        )
        for check in failed:
            print(f"    FAILED {check.name}: stated {check.expected}, computed {check.actual}")
    return 1 if failures else 0


def _select(profiles: dict[str, Profile], name: str | None, words: list[Word]) -> Profile:
    if name is not None:
        return profiles[name]
    text = "\n".join(line.text for line in group_lines(words, DEFAULT_LINE_TOLERANCE))
    for profile in profiles.values():
        if profile.detect.search(text):
            return profile
    raise ValueError("No profile matches this file.")


def _parse(profile: Profile, words: list[Word]) -> tuple[list[Check], int]:
    if isinstance(profile, ColumnTableProfile):
        statement = parse_column_table(words, profile)
        return list(reconcile_account_statement(statement)), len(statement.entries)
    parts = parse_line_patterns(words, profile)
    checks = [check for part in parts for check in part.checks]
    return checks, sum(len(part.entries) for part in parts)


if __name__ == "__main__":
    sys.exit(main())
