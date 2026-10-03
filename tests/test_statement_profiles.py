"""Tests for statement profile loading and value helpers."""

import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from personal_finance.statements import StatementFormatError, load_profiles
from personal_finance.statements.models import Word
from personal_finance.statements.profiles import (
    AmountFormat,
    ColumnTableProfile,
    LinePatternProfile,
)
from personal_finance.statements.text import group_lines, parse_amount, parse_date
from statement_fixtures import EXAMPLE_PROFILES

DOTS = AmountFormat(thousands=".", decimal=",")
COMMAS = AmountFormat(thousands=",", decimal=".")


class TestLoadProfiles(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        self.path = Path(self._directory.name) / "profiles.toml"

    def load(self, text: str):
        self.path.write_text(text, encoding="utf-8")
        return load_profiles(self.path)

    def test_loads_the_fictional_example(self) -> None:
        profiles = load_profiles(EXAMPLE_PROFILES)

        self.assertIsInstance(profiles["example_checking"], ColumnTableProfile)
        self.assertIsInstance(profiles["example_card"], LinePatternProfile)
        self.assertEqual(["domestic", "foreign"], [part.name for part in profiles["example_card"].parts])

    def test_loads_account_rules_and_card_periods(self) -> None:
        profiles = load_profiles(EXAMPLE_PROFILES)
        checking, card = profiles["example_checking"].account, profiles["example_card"]

        self.assertEqual(("Example Bank", "checking", "EUR"), (checking.institution, checking.kind, checking.currency))
        self.assertTrue(checking.transfers[0].search("CARD PAYMENT 0000"))
        self.assertIsNone(card.account.reference)
        self.assertEqual("%d/%m/%Y", card.period_date_format)

    def test_a_summary_line_replaces_balance_rows(self) -> None:
        example = EXAMPLE_PROFILES.read_text(encoding="utf-8")
        text = example.replace(
            "opening_balance = '^OPENING BALANCE$'\nclosing_balance = '^CLOSING BALANCE$'\n",
            "summary = '^SUMMARY (?P<opening>[\\d,.]+) TO (?P<closing>[\\d,.]+)$'\n",
        )
        self.assertNotEqual(example, text)

        profile = self.load(text)["example_checking"]

        self.assertIsNone(profile.opening_balance)
        self.assertIsNotNone(profile.summary)

    def test_rejects_an_unknown_account_kind(self) -> None:
        text = EXAMPLE_PROFILES.read_text(encoding="utf-8").replace('kind = "checking"', 'kind = "vault"')

        with self.assertRaisesRegex(ValueError, "unknown kind"):
            self.load(text)

    def test_rejects_missing_profiles_table(self) -> None:
        with self.assertRaisesRegex(ValueError, r"\[profiles\]"):
            self.load('title = "none"\n')

    def test_rejects_unknown_engine(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown engine"):
            self.load('[profiles.sample]\nengine = "guess"\n')

    def test_rejects_invalid_pattern_without_echoing_it(self) -> None:
        example = EXAMPLE_PROFILES.read_text(encoding="utf-8")
        broken = example.replace("detect = '^EXAMPLE BANK CHECKING STATEMENT$'", "detect = 'SECRET('")

        with self.assertRaises(ValueError) as context:
            self.load(broken)

        self.assertIn("'detect'", str(context.exception))
        self.assertNotIn("SECRET", str(context.exception))

    def test_rejects_entry_pattern_without_the_amount_group(self) -> None:
        example = EXAMPLE_PROFILES.read_text(encoding="utf-8")
        broken = example.replace('amount_field = "billed"', 'amount_field = "missing"')

        with self.assertRaisesRegex(ValueError, "named groups: missing"):
            self.load(broken)

    def test_rejects_missing_account_columns(self) -> None:
        example = EXAMPLE_PROFILES.read_text(encoding="utf-8")
        broken = example.replace('name = "credit"', 'name = "deposits"')

        with self.assertRaisesRegex(ValueError, "missing columns: credit"):
            self.load(broken)

    def test_rejects_grand_total_with_undefined_values(self) -> None:
        example = EXAMPLE_PROFILES.read_text(encoding="utf-8")
        broken = example.replace('plus = ["previous_billed"]', 'plus = ["unknown"]')

        with self.assertRaisesRegex(ValueError, "undefined values: unknown"):
            self.load(broken)


class TestParseAmount(unittest.TestCase):
    def test_reads_both_separator_conventions_exactly(self) -> None:
        self.assertEqual(Decimal("1234567"), parse_amount("1.234.567", DOTS))
        self.assertEqual(Decimal("834.37"), parse_amount("834,37", DOTS))
        self.assertEqual(Decimal("-1234.50"), parse_amount("-1,234.50", COMMAS))
        self.assertEqual(Decimal("0"), parse_amount("0", COMMAS))

    def test_rejects_non_amounts_without_echoing_them(self) -> None:
        for text in ("SECRET", "12.34.5", "1,234.50"):
            with self.subTest(text=text), self.assertRaises(StatementFormatError) as context:
                parse_amount(text, DOTS)
            self.assertNotIn(text, str(context.exception))


class TestParseDate(unittest.TestCase):
    def test_uses_the_year_in_the_text_when_present(self) -> None:
        self.assertEqual(date(2026, 3, 5), parse_date("05/03/26", "%d/%m/%y"))

    def test_infers_the_year_from_the_period_end(self) -> None:
        self.assertEqual(date(2026, 1, 5), parse_date("05/01", "%d/%m", date(2026, 1, 19)))
        self.assertEqual(date(2025, 12, 22), parse_date("22/12", "%d/%m", date(2026, 1, 19)))

    def test_accepts_a_leap_day_from_the_previous_year(self) -> None:
        self.assertEqual(date(2028, 2, 29), parse_date("29/02", "%d/%m", date(2029, 1, 10)))


class TestGroupLines(unittest.TestCase):
    def test_groups_nearby_tops_and_orders_words_left_to_right(self) -> None:
        words = [
            Word("second", 60, 90, 101.5, 1),
            Word("first", 20, 50, 100, 1),
            Word("next", 20, 40, 110, 1),
            Word("other", 20, 45, 100, 2),
        ]

        lines = group_lines(words, tolerance=3)

        self.assertEqual(["first second", "next", "other"], [line.text for line in lines])
