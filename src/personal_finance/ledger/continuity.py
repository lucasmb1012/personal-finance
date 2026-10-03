"""Chain consecutive statements to find missing or misread ones."""

from collections.abc import Iterable
from datetime import timedelta
from itertools import groupby

from personal_finance.ledger.models import ContinuityIssue, PeriodBalance


def check_continuity(balances: Iterable[PeriodBalance]) -> list[ContinuityIssue]:
    """Compare each statement of one account with the previous one in its currency.

    A period may start on the previous period's end date or the day after;
    institutions differ on which day the boundary belongs to.
    """
    issues: list[ContinuityIssue] = []
    ordered = sorted(balances, key=lambda balance: (balance.currency, balance.period_end))
    for currency, group in groupby(ordered, key=lambda balance: balance.currency):
        previous = None
        for current in group:
            if previous is not None:
                issue = _compare(currency, previous, current)
                if issue is not None:
                    issues.append(issue)
            previous = current
    return issues


def _compare(
    currency: str, previous: PeriodBalance, current: PeriodBalance
) -> ContinuityIssue | None:
    if current.opening != previous.closing:
        return ContinuityIssue("balance", currency, previous, current)
    if current.period_start is None:
        return None
    if current.period_start < previous.period_end:
        return ContinuityIssue("overlap", currency, previous, current)
    if current.period_start > previous.period_end + timedelta(days=1):
        return ContinuityIssue("gap", currency, previous, current)
    return None
