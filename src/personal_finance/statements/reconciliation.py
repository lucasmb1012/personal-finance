"""Reconciliation checks that confirm a statement was read completely."""

from personal_finance.statements.models import AccountStatement, Check


def reconcile_account_statement(statement: AccountStatement) -> tuple[Check, ...]:
    """Replay every entry from the opening balance and compare each stated balance.

    After a mismatch the running balance restarts from the stated one, so each
    failed check points at the rows since the previous stated balance.
    """
    checks: list[Check] = []
    running = statement.opening_balance
    for number, entry in enumerate(statement.entries, start=1):
        running += (entry.credit or 0) - (entry.debit or 0)
        if entry.balance is not None:
            checks.append(Check(f"balance after entry {number}", entry.balance, running))
            running = entry.balance
    checks.append(Check("closing balance", statement.closing_balance, running))
    return tuple(checks)
