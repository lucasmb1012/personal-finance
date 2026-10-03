"""Map parsed statements to the core model.

Only statements that pass every reconciliation check are mapped: a failed check
means an entry may be missing, and a missing entry must not reach the ledger.
"""

import re
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal

from personal_finance.ledger.models import AccountKey, Balance, StatementRecord, Transaction
from personal_finance.statements.column_table import parse_column_table
from personal_finance.statements.line_patterns import parse_line_patterns
from personal_finance.statements.models import (
    AccountStatement,
    Check,
    Line,
    StatementFormatError,
    StatementPart,
    Word,
)
from personal_finance.statements.profiles import (
    AccountRule,
    ColumnTableProfile,
    LinePatternProfile,
    Profile,
)
from personal_finance.statements.reconciliation import reconcile_account_statement
from personal_finance.statements.text import group_lines

ENTRY_FIELDS = ("date", "description", "installment", "installments")


class UnreconciledStatementError(ValueError):
    """A statement failed reconciliation checks and was not mapped."""


def statement_record(words: Iterable[Word], profile: Profile) -> StatementRecord:
    """Parse, reconcile, and map one statement."""
    words = list(words)
    rule = _rule(profile)
    lines = group_lines(words, profile.line_tolerance)
    account = AccountKey(rule.institution, rule.kind, _reference(lines, profile.name, rule))
    if isinstance(profile, ColumnTableProfile):
        statement = parse_column_table(words, profile)
        checks = reconcile_account_statement(statement)
        _require_passed(checks)
        return _account_record(statement, profile.name, account, rule, len(checks))
    parts = parse_line_patterns(words, profile)
    checks = tuple(check for part in parts for check in part.checks)
    _require_passed(checks)
    period_start, period_end = _card_period(lines, profile)
    return StatementRecord(
        account=account,
        profile=profile.name,
        period_start=period_start,
        period_end=period_end,
        balances=tuple(_card_balance(part) for part in parts if _has_balance(part)),
        transactions=_card_transactions(parts, rule),
        checks_passed=len(checks),
    )


def _rule(profile: Profile) -> AccountRule:
    if profile.account is None:
        raise ValueError(f"Profile {profile.name!r} has no account table.")
    return profile.account


def _reference(lines: Sequence[Line], profile_name: str, rule: AccountRule) -> str:
    if rule.reference is None:
        return profile_name
    for line in lines:
        if match := rule.reference.search(line.text):
            digits = re.sub(r"\D", "", match["reference"])
            if len(digits) >= 4:
                return rule.aliases.get(digits[-4:], digits[-4:])
    raise StatementFormatError(f"Profile {profile_name!r} found no account reference.")


def _require_passed(checks: Sequence[Check]) -> None:
    failed = [check.name for check in checks if not check.passed]
    if failed:
        raise UnreconciledStatementError(f"Failed checks: {', '.join(failed)}.")


def _is_transfer(description: str, rule: AccountRule) -> bool:
    return any(pattern.search(description) for pattern in rule.transfers)


def _account_record(
    statement: AccountStatement,
    profile_name: str,
    account: AccountKey,
    rule: AccountRule,
    checks_passed: int,
) -> StatementRecord:
    transactions = []
    for line, entry in enumerate(statement.entries, start=1):
        if entry.credit is None and entry.debit is None:
            continue
        amount = (entry.credit or Decimal(0)) - (entry.debit or Decimal(0))
        transactions.append(
            Transaction(
                line=line,
                occurred_on=entry.date,
                description=entry.description,
                amount=amount,
                currency=rule.currency,
                is_transfer=_is_transfer(entry.description, rule),
                balance_after=entry.balance,
                details=dict(entry.extra),
            )
        )
    return StatementRecord(
        account=account,
        profile=profile_name,
        period_start=statement.period_start,
        period_end=statement.period_end,
        balances=(Balance(rule.currency, statement.opening_balance, statement.closing_balance),),
        transactions=tuple(transactions),
        checks_passed=checks_passed,
    )


def _card_period(lines: Sequence[Line], profile: LinePatternProfile) -> tuple[date, date]:
    if profile.period is None or profile.period_date_format is None:
        raise ValueError(f"Profile {profile.name!r} has no statement period pattern.")
    for line in lines:
        if match := profile.period.search(line.text):
            start = datetime.strptime(match["start"], profile.period_date_format).date()
            end = datetime.strptime(match["end"], profile.period_date_format).date()
            return start, end
    raise StatementFormatError(f"Profile {profile.name!r} found no statement period.")


def _has_balance(part: StatementPart) -> bool:
    return part.grand_total is not None and "previous_billed" in part.values


def _card_balance(part: StatementPart) -> Balance:
    assert part.grand_total is not None
    return Balance(part.currency, part.values["previous_billed"], part.grand_total)


def _card_transactions(parts: Sequence[StatementPart], rule: AccountRule) -> tuple[Transaction, ...]:
    transactions = []
    line = 0
    for part in parts:
        for entry in part.entries:
            line += 1
            if not entry.billed:
                continue
            description = str(entry.fields.get("description") or "")
            occurred_on = entry.fields.get("date")
            if not isinstance(occurred_on, date):
                raise StatementFormatError(f"Part {part.name!r} has an entry without a date.")
            transactions.append(
                Transaction(
                    line=line,
                    occurred_on=occurred_on,
                    description=description,
                    amount=-entry.amount,
                    currency=part.currency,
                    is_transfer=_is_transfer(description, rule),
                    installment=_integer(entry.fields.get("installment")),
                    installments=_integer(entry.fields.get("installments")),
                    details={
                        name: str(value)
                        for name, value in entry.fields.items()
                        if name not in ENTRY_FIELDS and value is not None
                    },
                )
            )
    return tuple(transactions)


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) else None
