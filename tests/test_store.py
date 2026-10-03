"""Tests for the PostgreSQL adapter.

They run only when PERSONAL_FINANCE_TEST_DATABASE names a disposable database,
whose public schema they drop and recreate. Run them with
`uv run --env-file .env python -m unittest discover -s tests`.
"""

import os
import unittest
from datetime import date
from decimal import Decimal

from personal_finance.ledger.statements import statement_record
from statement_fixtures import example_profile
from test_ledger import card_words, checking_words

TEST_DATABASE = os.environ.get("PERSONAL_FINANCE_TEST_DATABASE")


@unittest.skipUnless(TEST_DATABASE, "PERSONAL_FINANCE_TEST_DATABASE is not set")
class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        import psycopg

        from personal_finance.store import database

        if TEST_DATABASE == os.environ.get("PGDATABASE"):
            self.fail("The test database must not be the ledger database.")
        self.database = database
        self.connection = psycopg.connect(dbname=TEST_DATABASE, autocommit=True)
        self.connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        self.assertEqual(["0001_ledger"], database.migrate(self.connection))

    def tearDown(self) -> None:
        self.connection.close()

    def test_migrations_apply_once(self) -> None:
        self.assertEqual([], self.database.migrate(self.connection))

    def test_saving_a_statement_is_idempotent(self) -> None:
        record = statement_record(checking_words(), example_profile("example_checking"))

        self.assertTrue(self.database.save_statement(self.connection, record, "a.pdf", "f" * 64))
        self.assertFalse(self.database.save_statement(self.connection, record, "a.pdf", "f" * 64))
        count, total = self.connection.execute("SELECT count(*), sum(amount) FROM transactions").fetchone()
        self.assertEqual((4, Decimal("1170.50")), (count, total))

    def test_reads_balances_back_for_continuity_checks(self) -> None:
        card = statement_record(card_words(), example_profile("example_card"))
        self.database.save_statement(self.connection, card, "card.pdf", "c" * 64)

        ((account, balances),) = self.database.period_balances(self.connection).items()

        self.assertEqual("credit_card", account.kind)
        self.assertEqual(
            [(date(2026, 3, 31), "EUR", Decimal("120.00"), Decimal("242.50"))],
            [(b.period_end, b.currency, b.opening, b.closing) for b in balances],
        )

    def test_monthly_flows_separate_transfers(self) -> None:
        card = statement_record(card_words(), example_profile("example_card"))
        self.database.save_statement(self.connection, card, "card.pdf", "c" * 64)

        rows = self.connection.execute(
            "SELECT currency, month, income, spending, transfers FROM monthly_flows"
            " WHERE currency = 'EUR' ORDER BY month"
        ).fetchall()

        self.assertEqual(
            [
                ("EUR", date(2026, 1, 1), None, Decimal("-200.00"), None),
                ("EUR", date(2026, 3, 1), None, Decimal("-42.50"), Decimal("120.00")),
            ],
            rows,
        )


if __name__ == "__main__":
    unittest.main()
