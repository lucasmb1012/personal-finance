"""Layout-independent helpers: grouping words into lines and reading values."""

import re
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal

from personal_finance.statements.models import Line, StatementFormatError, Word
from personal_finance.statements.profiles import AmountFormat


def group_lines(words: Iterable[Word], tolerance: float) -> list[Line]:
    """Group words whose tops differ by at most ``tolerance`` points into lines."""
    ordered = sorted(words, key=lambda word: (word.page, word.top, word.x0))
    lines: list[Line] = []
    current: list[Word] = []
    for word in ordered:
        if current and (
            word.page != current[0].page or word.top - current[0].top > tolerance
        ):
            lines.append(Line(tuple(sorted(current, key=lambda item: item.x0))))
            current = []
        current.append(word)
    if current:
        lines.append(Line(tuple(sorted(current, key=lambda item: item.x0))))
    return lines


def parse_amount(text: str, amount_format: AmountFormat) -> Decimal:
    """Return ``text`` as an exact decimal, following the profile's separators."""
    thousands = re.escape(amount_format.thousands)
    decimal = re.escape(amount_format.decimal)
    grouped = rf"-?\d{{1,3}}(?:{thousands}\d{{3}})*(?:{decimal}\d+)?"
    plain = rf"-?\d+(?:{decimal}\d+)?"
    value = text.strip()
    if not (re.fullmatch(grouped, value) or re.fullmatch(plain, value)):
        raise StatementFormatError("A value in an amount position is not an amount.")
    value = value.replace(amount_format.thousands, "")
    return Decimal(value.replace(amount_format.decimal, "."))


def is_amount(text: str, amount_format: AmountFormat) -> bool:
    try:
        parse_amount(text, amount_format)
    except StatementFormatError:
        return False
    return True


def parse_date(text: str, date_format: str, period_end: date | None = None) -> date:
    """Parse a date; when the format has no year, infer it from ``period_end``.

    A statement period can cross a year boundary, so a day and month later than
    the period end belong to the previous year.
    """
    if "%y" in date_format or "%Y" in date_format:
        return datetime.strptime(text, date_format).date()
    if period_end is None:
        raise StatementFormatError("A date without a year needs a statement period.")
    for year in (period_end.year, period_end.year - 1):
        try:
            parsed = datetime.strptime(f"{text} {year}", f"{date_format} %Y").date()
        except ValueError:
            continue
        if parsed <= period_end:
            return parsed
    raise StatementFormatError("A date does not fall within the statement period.")
