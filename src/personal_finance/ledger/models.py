"""Records of the core financial model.

Invariants:

- Amounts are exact decimals, never floating-point values.
- A transaction amount is signed from the operator's point of view: money in
  or a credit is positive, money out or a charge is negative. On a credit card
  statement a purchase is therefore negative and a payment positive.
- A statement balance is stated as the institution states it: the funds in an
  account, or the amount owed on a card.
- Accounts are identified by institution pseudonym, kind, and at most the last
  four digits of their number; full numbers are never stored.
- A transfer moves money between the operator's own accounts. It is kept, but
  it is neither income nor spending.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class AccountKey:
    institution: str
    kind: str
    reference: str


@dataclass(frozen=True)
class Balance:
    """A statement's opening and closing balance in one currency."""

    currency: str
    opening: Decimal
    closing: Decimal


@dataclass(frozen=True)
class Transaction:
    line: int
    occurred_on: date
    description: str
    amount: Decimal
    currency: str
    is_transfer: bool = False
    balance_after: Decimal | None = None
    installment: int | None = None
    installments: int | None = None
    details: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StatementRecord:
    """A reconciled statement mapped to the model, ready to be stored."""

    account: AccountKey
    profile: str
    period_start: date | None
    period_end: date
    balances: tuple[Balance, ...]
    transactions: tuple[Transaction, ...]
    checks_passed: int


@dataclass(frozen=True)
class PeriodBalance:
    """The part of a stored statement that continuity checks need."""

    period_start: date | None
    period_end: date
    currency: str
    opening: Decimal
    closing: Decimal


@dataclass(frozen=True)
class ContinuityIssue:
    """A break between two consecutive statements of one account and currency.

    ``kind`` is ``balance`` when the opening balance differs from the previous
    closing balance, which means a statement is missing or was misread;
    ``gap`` when periods are not contiguous but the balances still chain,
    which is expected when an institution skips a period with nothing to bill;
    and ``overlap`` when two periods overlap.
    """

    kind: str
    currency: str
    previous: PeriodBalance
    current: PeriodBalance
