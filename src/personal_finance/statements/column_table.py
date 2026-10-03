"""Parse account statements laid out as tables whose columns are found by position.

Amounts in a debit column and a credit column look identical as text, so each
word is assigned to a column by the horizontal position of one of its edges.
"""

from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal

from personal_finance.statements.models import (
    AccountEntry,
    AccountStatement,
    Line,
    StatementFormatError,
    Word,
)
from personal_finance.statements.profiles import ColumnTableProfile
from personal_finance.statements.text import group_lines, parse_amount, parse_date

AMOUNT_COLUMNS = ("debit", "credit", "balance")


def parse_column_table(words: Iterable[Word], profile: ColumnTableProfile) -> AccountStatement:
    """Return the account statement described by ``words``."""
    lines = group_lines(words, profile.line_tolerance)
    period_start, period_end = _period(lines, profile)
    opening: Decimal | None = None
    closing: Decimal | None = None
    entries: list[AccountEntry] = []

    in_table = False
    for number, line in enumerate(lines, start=1):
        if profile.header.search(line.text):
            in_table = True
            continue
        if profile.footer.search(line.text):
            in_table = False
            continue
        if not in_table or not profile.row_start.search(line.words[0].text):
            continue

        entry = _entry(line, number, profile, period_end)
        if profile.opening_balance and profile.opening_balance.search(entry.description):
            opening = _required_balance(entry, "opening_balance")
        elif profile.closing_balance and profile.closing_balance.search(entry.description):
            closing = _required_balance(entry, "closing_balance")
        else:
            entries.append(entry)

    if profile.summary is not None:
        opening, closing = _summary(lines, profile)
    if opening is None or closing is None:
        raise StatementFormatError(
            f"Profile {profile.name!r} found no opening or closing balance row."
        )
    return AccountStatement(period_start, period_end, opening, closing, tuple(entries))


def _period(lines: list[Line], profile: ColumnTableProfile) -> tuple[date, date]:
    for line in lines:
        match = profile.period.search(line.text)
        if match:
            start = datetime.strptime(match["start"], profile.period_date_format).date()
            end = datetime.strptime(match["end"], profile.period_date_format).date()
            return start, end
    raise StatementFormatError(f"Profile {profile.name!r} found no statement period.")


def _summary(lines: list[Line], profile: ColumnTableProfile) -> tuple[Decimal, Decimal]:
    assert profile.summary is not None
    for line in lines:
        if match := profile.summary.search(line.text):
            return (
                parse_amount(match["opening"], profile.amount_format),
                parse_amount(match["closing"], profile.amount_format),
            )
    raise StatementFormatError(f"Profile {profile.name!r} found no summary line.")


def _entry(
    line: Line, number: int, profile: ColumnTableProfile, period_end: date
) -> AccountEntry:
    cells: dict[str, list[str]] = {}
    for word in line.words:
        column = _column_for(word, profile)
        if column is None:
            raise StatementFormatError(
                f"Line {number} has a word outside every column of profile {profile.name!r}."
            )
        cells.setdefault(column, []).append(word.text)

    texts = {column: " ".join(values) for column, values in cells.items()}
    amounts: dict[str, Decimal | None] = {}
    for column in AMOUNT_COLUMNS:
        text = texts.get(column)
        try:
            amounts[column] = None if text is None else parse_amount(text, profile.amount_format)
        except StatementFormatError:
            raise StatementFormatError(
                f"Line {number} has a non-amount in the {column!r} column."
            ) from None

    return AccountEntry(
        date=parse_date(texts["date"], profile.date_format, period_end),
        description=texts.get("description", ""),
        debit=amounts["debit"],
        credit=amounts["credit"],
        balance=amounts["balance"],
        extra={
            column: text
            for column, text in texts.items()
            if column not in ("date", "description", *AMOUNT_COLUMNS)
        },
    )


def _column_for(word: Word, profile: ColumnTableProfile) -> str | None:
    for column in profile.columns:
        edge = word.x0 if column.anchor == "x0" else word.x1
        if column.minimum <= edge < column.maximum:
            return column.name
    return None


def _required_balance(entry: AccountEntry, key: str) -> Decimal:
    if entry.balance is None:
        raise StatementFormatError(f"The {key!r} row has no balance.")
    return entry.balance
