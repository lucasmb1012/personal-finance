"""PostgreSQL access: connection, migrations, and ledger reads and writes.

Connection settings come from the standard PostgreSQL environment variables
(PGHOST, PGPORT, PGUSER, PGDATABASE, PGPASSWORD), never from code.
"""

from collections import defaultdict
from importlib import resources

import psycopg
from psycopg.types.json import Jsonb

from personal_finance.ledger.categories import CategoryRule, categorize
from personal_finance.ledger.models import AccountKey, PeriodBalance, StatementRecord

MIGRATIONS_PACKAGE = "personal_finance.store.migrations"


def connect() -> psycopg.Connection:
    return psycopg.connect()


def migrate(connection: psycopg.Connection) -> list[str]:
    """Apply every migration not yet recorded, each in its own transaction."""
    with connection.transaction():
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version text PRIMARY KEY,"
            " applied_at timestamptz NOT NULL DEFAULT now())"
        )
    applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
    files = sorted(
        (item for item in resources.files(MIGRATIONS_PACKAGE).iterdir() if item.name.endswith(".sql")),
        key=lambda item: item.name,
    )
    done = []
    for item in files:
        version = item.name.removesuffix(".sql")
        if version in applied:
            continue
        with connection.transaction():
            connection.execute(item.read_text(encoding="utf-8"))
            connection.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        done.append(version)
    return done


def save_statement(
    connection: psycopg.Connection, record: StatementRecord, source_name: str, source_sha256: str
) -> bool:
    """Store a statement and its transactions; return False if it was already stored."""
    with connection.transaction():
        if connection.execute(
            "SELECT 1 FROM statements WHERE source_sha256 = %s", (source_sha256,)
        ).fetchone():
            return False
        account_id = _account_id(connection, record.account)
        statement_id = connection.execute(
            "INSERT INTO statements (account_id, source_sha256, source_name, profile,"
            " period_start, period_end, checks_passed)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (
                account_id,
                source_sha256,
                source_name,
                record.profile,
                record.period_start,
                record.period_end,
                record.checks_passed,
            ),
        ).fetchone()[0]
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO statement_balances (statement_id, currency, opening, closing)"
                " VALUES (%s, %s, %s, %s)",
                [(statement_id, b.currency, b.opening, b.closing) for b in record.balances],
            )
            cursor.executemany(
                "INSERT INTO transactions (statement_id, account_id, line, occurred_on,"
                " description, amount, currency, is_transfer, balance_after, installment,"
                " installments, details)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    (
                        statement_id,
                        account_id,
                        t.line,
                        t.occurred_on,
                        t.description,
                        t.amount,
                        t.currency,
                        t.is_transfer,
                        t.balance_after,
                        t.installment,
                        t.installments,
                        Jsonb(dict(t.details)),
                    )
                    for t in record.transactions
                ],
            )
    return True


def period_balances(connection: psycopg.Connection) -> dict[AccountKey, list[PeriodBalance]]:
    """Return every stored statement balance, grouped by account."""
    rows = connection.execute(
        "SELECT a.institution, a.kind, a.reference, s.period_start, s.period_end,"
        " b.currency, b.opening, b.closing"
        " FROM statement_balances b"
        " JOIN statements s ON s.id = b.statement_id"
        " JOIN accounts a ON a.id = s.account_id"
        " ORDER BY a.id, b.currency, s.period_end"
    ).fetchall()
    grouped: dict[AccountKey, list[PeriodBalance]] = defaultdict(list)
    for institution, kind, reference, start, end, currency, opening, closing in rows:
        grouped[AccountKey(institution, kind, reference)].append(
            PeriodBalance(start, end, currency.strip(), opening, closing)
        )
    return dict(grouped)


def apply_categories(connection: psycopg.Connection, rules: tuple[CategoryRule, ...]) -> int:
    """Recompute every transaction's category in one transaction; return how many changed."""
    with connection.transaction():
        rows = connection.execute("SELECT id, description, amount, category FROM transactions").fetchall()
        changes = [
            (category, identifier)
            for identifier, description, amount, current in rows
            if (category := categorize(rules, description, amount)) != current
        ]
        with connection.cursor() as cursor:
            cursor.executemany("UPDATE transactions SET category = %s WHERE id = %s", changes)
    return len(changes)


def _account_id(connection: psycopg.Connection, account: AccountKey) -> int:
    row = connection.execute(
        "INSERT INTO accounts (institution, kind, reference) VALUES (%s, %s, %s)"
        " ON CONFLICT (institution, kind, reference) DO UPDATE SET reference = EXCLUDED.reference"
        " RETURNING id",
        (account.institution, account.kind, account.reference),
    ).fetchone()
    return row[0]
