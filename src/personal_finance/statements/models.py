"""Records produced by the statement parsing engines."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class StatementFormatError(ValueError):
    """A statement does not match the layout its profile describes.

    Messages name profile keys and positions but never echo statement content.
    """


@dataclass(frozen=True)
class Word:
    """A word extracted from a statement page, with its horizontal extent."""

    text: str
    x0: float
    x1: float
    top: float
    page: int


@dataclass(frozen=True)
class Line:
    """Words that share a baseline on one page, ordered left to right."""

    words: tuple[Word, ...]

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)


@dataclass(frozen=True)
class Check:
    """A reconciliation check: a value the statement states versus a computed one."""

    name: str
    expected: Decimal
    actual: Decimal

    @property
    def passed(self) -> bool:
        return self.expected == self.actual


@dataclass(frozen=True)
class AccountEntry:
    """One row of an account statement table."""

    date: date
    description: str
    debit: Decimal | None
    credit: Decimal | None
    balance: Decimal | None
    extra: Mapping[str, str]


@dataclass(frozen=True)
class AccountStatement:
    """An account statement: a period, its balances, and the rows between them."""

    period_start: date
    period_end: date
    opening_balance: Decimal
    closing_balance: Decimal
    entries: tuple[AccountEntry, ...]


@dataclass(frozen=True)
class PatternEntry:
    """A statement line matched by an entry pattern, with typed named fields."""

    section: str
    billed: bool
    amount: Decimal
    fields: Mapping[str, object]


@dataclass(frozen=True)
class StatementPart:
    """One part of a line-pattern statement, such as the portion in one currency."""

    name: str
    currency: str
    entries: tuple[PatternEntry, ...]
    checks: tuple[Check, ...]
