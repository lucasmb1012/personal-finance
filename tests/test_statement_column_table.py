"""Tests for the column-table statement engine and balance reconciliation."""

import unittest
from dataclasses import replace
import re
from datetime import date
from decimal import Decimal

from personal_finance.statements import (
    StatementFormatError,
    parse_column_table,
    reconcile_account_statement,
)
from personal_finance.statements.models import Word
from statement_fixtures import example_profile, left_aligned, right_aligned

DEBIT_EDGE, CREDIT_EDGE, BALANCE_EDGE = 430.0, 510.0, 580.0


def row(
    top: float,
    day: str,
    description: str,
    *,
    page: int = 1,
    reference: str | None = None,
    debit: str | None = None,
    credit: str | None = None,
    balance: str | None = None,
) -> list[Word]:
    # The date sits one point above the description, as in real layouts.
    words = left_aligned(day, 20, top - 1, page) + left_aligned(description, 70, top, page)
    if reference is not None:
        words += left_aligned(reference, 310, top, page)
    for text, edge in ((debit, DEBIT_EDGE), (credit, CREDIT_EDGE), (balance, BALANCE_EDGE)):
        if text is not None:
            words.append(right_aligned(text, edge, top, page))
    return words


def header(top: float, page: int = 1) -> list[Word]:
    return left_aligned("DATE DESCRIPTION REFERENCE DEBIT CREDIT BALANCE", 20, top, page)


def statement_words() -> list[Word]:
    """A fictional statement whose period crosses a year boundary, over two pages."""
    return [
        *left_aligned("EXAMPLE BANK CHECKING STATEMENT", 20, 10),
        *left_aligned("FROM 20/12/2025 TO 19/01/2026", 20, 20),
        *header(40),
        *row(60, "20/12", "OPENING BALANCE", balance="1,000.00"),
        *row(70, "22/12", "COFFEE SHOP FICTION", debit="4.50"),
        *row(80, "22/12", "BOOKSTORE IMAGINARY", reference="000123", debit="25.00", balance="970.50"),
        *row(90, "05/01", "SALARY EXAMPLE CORP", credit="2,000.00", balance="2,970.50"),
        *left_aligned("END OF PAGE", 20, 100),
        *row(110, "01/01", "NOT A TABLE ROW"),
        *header(40, page=2),
        *row(60, "10/01", "RENT FICTIONAL", page=2, debit="800.00", balance="2,170.50"),
        *row(70, "19/01", "CLOSING BALANCE", page=2, balance="2,170.50"),
    ]


class TestParseColumnTable(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = example_profile("example_checking")

    def test_reads_period_balances_and_entries(self) -> None:
        statement = parse_column_table(statement_words(), self.profile)

        self.assertEqual(date(2025, 12, 20), statement.period_start)
        self.assertEqual(date(2026, 1, 19), statement.period_end)
        self.assertEqual(Decimal("1000.00"), statement.opening_balance)
        self.assertEqual(Decimal("2170.50"), statement.closing_balance)
        self.assertEqual(
            ["COFFEE SHOP FICTION", "BOOKSTORE IMAGINARY", "SALARY EXAMPLE CORP", "RENT FICTIONAL"],
            [entry.description for entry in statement.entries],
        )

    def test_assigns_amounts_to_columns_by_position(self) -> None:
        entries = parse_column_table(statement_words(), self.profile).entries

        self.assertEqual((Decimal("4.50"), None, None), (entries[0].debit, entries[0].credit, entries[0].balance))
        self.assertEqual((None, Decimal("2000.00")), (entries[2].debit, entries[2].credit))
        self.assertEqual({"reference": "000123"}, dict(entries[1].extra))

    def test_infers_the_year_across_a_year_boundary(self) -> None:
        entries = parse_column_table(statement_words(), self.profile).entries

        self.assertEqual(date(2025, 12, 22), entries[0].date)
        self.assertEqual(date(2026, 1, 5), entries[2].date)

    def test_rejects_a_statement_without_balance_rows(self) -> None:
        words = [word for word in statement_words() if word.text != "CLOSING"]

        with self.assertRaisesRegex(StatementFormatError, "opening or closing"):
            parse_column_table(words, self.profile)

    def test_reads_balances_from_a_summary_line(self) -> None:
        profile = replace(
            self.profile,
            opening_balance=None,
            closing_balance=None,
            summary=re.compile(r"^SUMMARY (?P<opening>[\d,.]+) TO (?P<closing>[\d,.]+)$"),
        )
        words = [
            *left_aligned("EXAMPLE BANK CHECKING STATEMENT", 20, 10),
            *left_aligned("FROM 20/12/2025 TO 19/01/2026", 20, 20),
            *header(40),
            *row(70, "22/12", "COFFEE SHOP FICTION", debit="4.50"),
            *row(80, "22/12", "BOOKSTORE IMAGINARY", debit="25.00", balance="970.50"),
            *left_aligned("END OF PAGE", 20, 100),
            *left_aligned("SUMMARY 1,000.00 TO 970.50", 20, 120),
        ]

        statement = parse_column_table(words, profile)

        self.assertEqual((Decimal("1000.00"), Decimal("970.50")), (statement.opening_balance, statement.closing_balance))
        self.assertEqual(2, len(statement.entries))
        self.assertTrue(all(check.passed for check in reconcile_account_statement(statement)))

    def test_rejects_a_statement_without_its_summary_line(self) -> None:
        profile = replace(self.profile, opening_balance=None, closing_balance=None, summary=re.compile("^NEVER$"))

        with self.assertRaisesRegex(StatementFormatError, "summary"):
            parse_column_table(statement_words(), profile)

    def test_rejects_text_in_an_amount_column_without_echoing_it(self) -> None:
        words = statement_words() + row(80, "22/12", "", page=2, debit="SECRET")

        with self.assertRaises(StatementFormatError) as context:
            parse_column_table(words, self.profile)

        self.assertIn("'debit'", str(context.exception))
        self.assertNotIn("SECRET", str(context.exception))


class TestReconcileAccountStatement(unittest.TestCase):
    def setUp(self) -> None:
        self.statement = parse_column_table(statement_words(), example_profile("example_checking"))

    def test_every_stated_balance_matches(self) -> None:
        checks = reconcile_account_statement(self.statement)

        self.assertEqual(4, len(checks))
        self.assertTrue(all(check.passed for check in checks))

    def test_a_missing_entry_fails_only_its_balance_check(self) -> None:
        entries = self.statement.entries
        statement = replace(self.statement, entries=(entries[1], *entries[2:]))

        failed = [check.name for check in reconcile_account_statement(statement) if not check.passed]

        self.assertEqual(["balance after entry 1"], failed)
