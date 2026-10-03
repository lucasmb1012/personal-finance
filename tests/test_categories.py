"""Tests for rule-based transaction categories."""

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from personal_finance.ledger.categories import categorize, load_category_rules

EXAMPLE_RULES = Path(__file__).resolve().parent.parent / "examples" / "categories.example.toml"


class TestCategories(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_category_rules(EXAMPLE_RULES)

    def test_the_first_matching_rule_wins(self) -> None:
        self.assertEqual(
            "housing:rent",
            categorize(self.rules, "TRANSFER TO FICTIONAL LANDLORD", Decimal("-500")),
        )
        self.assertEqual(
            "people:transfers out",
            categorize(self.rules, "TRANSFER TO IMAGINARY FRIEND", Decimal("-20")),
        )

    def test_matches_ignoring_case(self) -> None:
        self.assertEqual("food:groceries", categorize(self.rules, "Example Supermarket", Decimal("-12.50")))

    def test_direction_limits_a_rule_to_money_in_or_out(self) -> None:
        self.assertEqual("income:salary", categorize(self.rules, "PAYROLL EXAMPLE CORP", Decimal("2000")))
        self.assertIsNone(categorize(self.rules, "PAYROLL EXAMPLE CORP", Decimal("-2000")))

    def test_unmatched_descriptions_have_no_category(self) -> None:
        self.assertIsNone(categorize(self.rules, "UNKNOWN SHOP", Decimal("-1")))


class TestLoadCategoryRules(unittest.TestCase):
    def load(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.toml"
            path.write_text(text, encoding="utf-8")
            return load_category_rules(path)

    def test_rejects_a_file_without_rules(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            self.load("title = 'nothing'\n")

    def test_rejects_an_unknown_direction(self) -> None:
        with self.assertRaisesRegex(ValueError, "direction"):
            self.load("[[rules]]\ncategory = 'x'\ndirection = 'sideways'\npatterns = ['A']\n")

    def test_rejects_an_invalid_pattern_without_echoing_it(self) -> None:
        with self.assertRaises(ValueError) as context:
            self.load("[[rules]]\ncategory = 'x'\npatterns = ['SECRET(']\n")

        self.assertNotIn("SECRET", str(context.exception))


if __name__ == "__main__":
    unittest.main()
