"""Tests for the PostgreSQL adapter.

They run only when PERSONAL_FINANCE_TEST_DATABASE names a disposable database,
whose public schema they drop and recreate. Run them with
`uv run --env-file .env python -m unittest discover -s tests`.
"""

import os
import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal

from personal_finance.ledger.categories import load_category_rules
from personal_finance.ledger.statements import statement_record
from statement_fixtures import example_profile
from test_categories import EXAMPLE_RULES
from test_ledger import card_words, checking_words, grouped_card_words

TEST_DATABASE = os.environ.get("PERSONAL_FINANCE_TEST_DATABASE")


@unittest.skipUnless(TEST_DATABASE, "PERSONAL_FINANCE_TEST_DATABASE is not set")
class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        import psycopg

        from personal_finance.store import database

        if TEST_DATABASE == os.environ.get("PGDATABASE"):
            self.fail("The test database must not be the ledger database.")
        self.database = database
        self.psycopg = psycopg
        self.connection = psycopg.connect(dbname=TEST_DATABASE, autocommit=True)
        self.connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        self.assertEqual(
            ["0001_ledger", "0002_categories", "0003_statement_identity"],
            database.migrate(self.connection),
        )

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

    def test_monthly_flows_separate_transfers_and_bill_cards_by_period(self) -> None:
        card = statement_record(card_words(), example_profile("example_card"))
        self.database.save_statement(self.connection, card, "card.pdf", "c" * 64)

        rows = self.connection.execute(
            "SELECT currency, month, income, spending, transfers FROM monthly_flows"
            " WHERE currency = 'EUR' ORDER BY month"
        ).fetchall()

        self.assertEqual(
            [("EUR", date(2026, 3, 1), None, Decimal("-242.50"), Decimal("120.00"))],
            rows,
        )

    def test_categories_are_applied_idempotently_and_reported(self) -> None:
        card = statement_record(card_words(), example_profile("example_card"))
        self.database.save_statement(self.connection, card, "card.pdf", "c" * 64)
        rules = load_category_rules(EXAMPLE_RULES)

        self.assertEqual(1, self.database.apply_categories(self.connection, rules))
        self.assertEqual(0, self.database.apply_categories(self.connection, rules))
        rows = self.connection.execute(
            "SELECT category, spending FROM monthly_categories WHERE currency = 'EUR' ORDER BY category"
        ).fetchall()

        self.assertEqual(
            [("food:restaurants", Decimal("-12.50")), ("uncategorized", Decimal("-230.00"))],
            rows,
        )


    def test_one_period_may_hold_one_statement_per_profile(self) -> None:
        card = statement_record(card_words(), example_profile("example_card"))
        grouped = statement_record(grouped_card_words(), example_profile("example_grouped_card"))
        copy = replace(card, profile="example_card")

        self.assertTrue(self.database.save_statement(self.connection, card, "card.pdf", "c" * 64))
        self.assertTrue(self.database.save_statement(self.connection, grouped, "grouped.pdf", "d" * 64))
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            self.database.save_statement(self.connection, copy, "card-copy.pdf", "e" * 64)

    def test_transfer_flags_are_recomputed_from_profile_rules(self) -> None:
        card = statement_record(card_words(), example_profile("example_card"))
        self.database.save_statement(self.connection, card, "card.pdf", "c" * 64)
        rule = example_profile("example_card").account
        dated = replace(rule, transfers=(replace(rule.transfers[0], since=date(2026, 3, 3)),))

        self.assertEqual(1, self.database.apply_transfers(self.connection, {"example_card": dated}))
        self.assertEqual(0, self.database.apply_transfers(self.connection, {"example_card": dated}))
        self.assertEqual(1, self.database.apply_transfers(self.connection, {"example_card": rule}))
        with self.assertRaisesRegex(ValueError, "example_card"):
            self.database.apply_transfers(self.connection, {})


if __name__ == "__main__":
    unittest.main()
