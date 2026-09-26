"""Tests for the line-pattern statement engine."""

import unittest
from datetime import date
from decimal import Decimal

from personal_finance.statements import parse_line_patterns
from statement_fixtures import example_profile, text_words

DOMESTIC = [
    "EXAMPLE BANK CARD STATEMENT",
    "PREVIOUS AMOUNT DUE 120.00",
    "02/03/26 PAYMENT THANK YOU -120.00 01/01 -120.00",
    "TOTAL PAYMENTS -120.00",
    "05/03/26 CAFE EXAMPLE 12.50 01/01 12.50",
    "07/03/26 BOOKSHOP FICTION 30.00 01/01 30.00",
    "CARD ENDING 0000 TOTAL 42.50",
    "TOTAL PURCHASES 42.50",
    "10/01/26 FICTIONAL FURNITURE 1,200.00 03/06 200.00",
    "TOTAL INSTALLMENTS 200.00",
    "UPCOMING INSTALLMENTS",
    "12/03/26 GADGET STORE 90.00 00/03 30.00",
    "AMOUNT DUE 242.50",
]
FOREIGN = [
    "EXAMPLE BANK FOREIGN CARD STATEMENT",
    "03/03/26 MUSEUM SHOP LISBON PT 45.00 48.60",
    "04/03/26 ONLINE SERVICE US 10.00 10.00",
    "FOREIGN TOTAL 58.60",
]


def failed_checks(lines_by_page: list[list[str]]) -> list[str]:
    words = [word for page, lines in enumerate(lines_by_page, 1) for word in text_words(lines, page)]
    parts = parse_line_patterns(words, example_profile("example_card"))
    return [check.name for part in parts for check in part.checks if not check.passed]


class TestParseLinePatterns(unittest.TestCase):
    def setUp(self) -> None:
        words = text_words(DOMESTIC) + text_words(FOREIGN, page=2)
        self.domestic, self.foreign = parse_line_patterns(words, example_profile("example_card"))

    def test_splits_the_statement_into_parts(self) -> None:
        self.assertEqual(("domestic", "EUR"), (self.domestic.name, self.domestic.currency))
        self.assertEqual(("foreign", "USD"), (self.foreign.name, self.foreign.currency))
        self.assertEqual(5, len(self.domestic.entries))
        self.assertEqual(2, len(self.foreign.entries))

    def test_types_named_fields(self) -> None:
        installment = self.domestic.entries[3]

        self.assertEqual(Decimal("200.00"), installment.amount)
        self.assertEqual(Decimal("1200.00"), installment.fields["amount"])
        self.assertEqual(date(2026, 1, 10), installment.fields["date"])
        self.assertEqual((3, 6), (installment.fields["installment"], installment.fields["installments"]))
        self.assertEqual("FICTIONAL FURNITURE", installment.fields["description"])

    def test_keeps_the_original_currency_amount_of_foreign_entries(self) -> None:
        museum = self.foreign.entries[0]

        self.assertEqual(Decimal("48.60"), museum.amount)
        self.assertEqual(Decimal("45.00"), museum.fields["original_amount"])
        self.assertEqual("PT", museum.fields["country"])

    def test_marks_entries_of_unbilled_sections(self) -> None:
        upcoming = self.domestic.entries[4]

        self.assertEqual(("upcoming_installments", False), (upcoming.section, upcoming.billed))
        self.assertTrue(all(entry.billed for entry in self.domestic.entries[:4]))

    def test_every_check_passes_on_a_complete_statement(self) -> None:
        checks = self.domestic.checks + self.foreign.checks

        self.assertEqual(
            [
                "total PAYMENTS",
                "subtotal 0000",
                "total PURCHASES",
                "total INSTALLMENTS",
                "entries after the last total",
                "grand total",
                "total #0",
                "entries after the last total",
            ],
            [check.name for check in checks],
        )
        self.assertTrue(all(check.passed for check in checks))


class TestUnrecognizedLines(unittest.TestCase):
    def test_a_line_no_pattern_matches_fails_its_totals(self) -> None:
        domestic = [line for line in DOMESTIC if not line.startswith("07/03/26")]

        self.assertEqual(["subtotal 0000", "total PURCHASES"], failed_checks([domestic, FOREIGN]))

    def test_an_entry_after_the_last_total_is_reported(self) -> None:
        foreign = FOREIGN + ["05/03/26 LATE CHARGE US 1.00 1.00"]

        self.assertEqual(["entries after the last total"], failed_checks([DOMESTIC, foreign]))

    def test_a_wrong_stated_total_fails_the_grand_total(self) -> None:
        domestic = [line.replace("AMOUNT DUE 242.50", "AMOUNT DUE 999.00") for line in DOMESTIC]

        self.assertEqual(["grand total"], failed_checks([domestic, FOREIGN]))
