"""Load statements into the local database and check what was loaded.

Usage:
    python -m personal_finance.store migrate
    python -m personal_finance.store load [--profiles PATH] FILE...
    python -m personal_finance.store check
    python -m personal_finance.store categorize [--rules PATH]
    python -m personal_finance.store report [--months N] [--by account|category]

Connection settings come from the PostgreSQL environment variables; run with
`uv run --env-file .env`. The PDF password is read from STATEMENT_PDF_PASSWORD
or prompted for once. Output includes real amounts: keep it on the local
terminal and out of public artifacts.
"""

import argparse
import getpass
import hashlib
import os
import sys
from pathlib import Path

from personal_finance.ledger.categories import load_category_rules
from personal_finance.ledger.continuity import check_continuity
from personal_finance.ledger.statements import statement_record
from personal_finance.statements.__main__ import DEFAULT_PROFILES, PASSWORD_VARIABLE, _select
from personal_finance.statements.pdf import read_words
from personal_finance.statements.profiles import load_profiles
from personal_finance.store.database import (
    apply_categories,
    connect,
    migrate,
    period_balances,
    save_statement,
)

DEFAULT_RULES = Path("secrets/categories.toml")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m personal_finance.store")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate")
    load = commands.add_parser("load")
    load.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    load.add_argument("files", nargs="+", type=Path)
    commands.add_parser("check")
    categorize = commands.add_parser("categorize")
    categorize.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    report = commands.add_parser("report")
    report.add_argument("--months", type=int, default=12)
    report.add_argument("--by", choices=("account", "category"), default="account")
    arguments = parser.parse_args(argv)

    with connect() as connection:
        if arguments.command == "migrate":
            applied = migrate(connection)
            print(f"Applied migrations: {', '.join(applied) or 'none'}")
            return 0
        if arguments.command == "load":
            return _load(connection, arguments.profiles, arguments.files)
        if arguments.command == "check":
            return _check(connection)
        if arguments.command == "categorize":
            return _categorize(connection, arguments.rules)
        if arguments.by == "category":
            return _category_report(connection, arguments.months)
        return _report(connection, arguments.months)


def _load(connection, profiles_path: Path, files: list[Path]) -> int:
    profiles = load_profiles(profiles_path)
    password = os.environ.get(PASSWORD_VARIABLE) or getpass.getpass("PDF password: ") or None
    loaded = skipped = failed = 0
    for path in files:
        try:
            words = read_words(path, password)
            record = statement_record(words, _select(profiles, None, words))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if save_statement(connection, record, path.name, digest):
                loaded += 1
            else:
                skipped += 1
        except Exception as error:  # Report and continue with the next file.
            print(f"{path.name}: error: {type(error).__name__}: {error}")
            failed += 1
    print(f"Loaded {loaded}, already stored {skipped}, failed {failed}.")
    return 1 if failed else 0


def _check(connection) -> int:
    problems = 0
    for account, balances in period_balances(connection).items():
        issues = check_continuity(balances)
        label = f"{account.institution} {account.kind} {account.reference}"
        print(f"{label}: {len(balances)} statement balances, {len(issues)} breaks")
        for issue in issues:
            problems += issue.kind != "gap"
            print(
                f"    {issue.kind} {issue.currency}: "
                f"{issue.previous.period_start}..{issue.previous.period_end} closes {issue.previous.closing}, "
                f"{issue.current.period_start}..{issue.current.period_end} opens {issue.current.opening}"
            )
    return 1 if problems else 0


def _categorize(connection, rules_path: Path) -> int:
    changed = apply_categories(connection, load_category_rules(rules_path))
    rows = connection.execute(
        "SELECT coalesce(category, 'uncategorized'), count(*) FROM transactions"
        " WHERE NOT is_transfer GROUP BY 1 ORDER BY 2 DESC"
    ).fetchall()
    print(f"Changed {changed} categories. Non-transfer transactions per category:")
    for category, count in rows:
        print(f"    {category:<40} {count:>6}")
    return 0


def _category_report(connection, months: int) -> int:
    rows = connection.execute(
        "SELECT currency, category, sum(income), sum(spending), sum(transactions)"
        " FROM monthly_categories"
        " WHERE month >= date_trunc('month', current_date) - make_interval(months => %s)"
        " GROUP BY currency, category ORDER BY currency, coalesce(sum(spending), 0), category",
        (months,),
    ).fetchall()
    print(f"{'cur':<3} {'category':<40} {'income':>14} {'spending':>14} {'n':>5}")
    for currency, category, income, spending, count in rows:
        print(f"{currency:<3} {category:<40} {income or 0:>14,} {spending or 0:>14,} {count:>5}")
    return 0


def _report(connection, months: int) -> int:
    rows = connection.execute(
        "SELECT institution, kind, reference, currency, month, income, spending, transfers, net,"
        " transactions FROM monthly_flows"
        " WHERE month >= date_trunc('month', current_date) - make_interval(months => %s)"
        " ORDER BY institution, kind, reference, currency, month",
        (months,),
    ).fetchall()
    header = f"{'account':<34} {'cur':<3} {'month':<7} {'income':>14} {'spending':>14} {'transfers':>14} {'net':>14} {'n':>4}"
    print(header)
    for institution, kind, reference, currency, month, income, spending, transfers, net, count in rows:
        print(
            f"{institution + ' ' + kind + ' ' + reference:<34} {currency:<3} {month:%Y-%m} "
            f"{income or 0:>14,} {spending or 0:>14,} {transfers or 0:>14,} {net:>14,} {count:>4}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
