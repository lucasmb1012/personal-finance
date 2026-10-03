"""Tests for mapping statements to the core model and chaining them."""

import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal

from personal_finance.ledger.continuity import check_continuity
from personal_finance.ledger.models import AccountKey, PeriodBalance
from personal_finance.ledger.statements import UnreconciledStatementError, statement_record
from statement_fixtures import example_profile, left_aligned, text_words
from test_statement_column_table import row, statement_words
from test_statement_line_patterns import DOMESTIC, FOREIGN


def checking_words():
    return left_aligned("ACCOUNT NUMBER 00-123-4567", 20, 5) + statement_words()


def card_words():
    domestic = [DOMESTIC[0], "BILLING PERIOD 01/03/2026 TO 31/03/2026", *DOMESTIC[1:]]
    return text_words(domestic) + text_words(FOREIGN, page=2)


class TestCheckingStatementRecord(unittest.TestCase):
    def setUp(self) -> None:
        self.record = statement_record(checking_words(), example_profile("example_checking"))

    def test_identifies_the_account_by_its_last_four_digits(self) -> None:
        self.assertEqual(AccountKey("Example Bank", "checking", "4567"), self.record.account)

    def test_maps_a_replaced_number_to_the_current_account(self) -> None:
        profile = example_profile("example_checking")
        rule = replace(profile.account, aliases={"4567": "9999"})

        record = statement_record(checking_words(), replace(profile, account=rule))

        self.assertEqual("9999", record.account.reference)

    def test_keeps_period_and_balances(self) -> None:
        (balance,) = self.record.balances

        self.assertEqual((date(2025, 12, 20), date(2026, 1, 19)), (self.record.period_start, self.record.period_end))
        self.assertEqual(("EUR", Decimal("1000.00"), Decimal("2170.50")), (balance.currency, balance.opening, balance.closing))

    def test_signs_debits_negative_and_credits_positive(self) -> None:
        amounts = [transaction.amount for transaction in self.record.transactions]

        self.assertEqual([Decimal("-4.50"), Decimal("-25.00"), Decimal("2000.00"), Decimal("-800.00")], amounts)
        self.assertEqual(self.record.balances[0].closing - self.record.balances[0].opening, sum(amounts))

    def test_marks_transfers_by_description(self) -> None:
        words = checking_words() + row(75, "23/12", "CARD PAYMENT FICTION", debit="0.00")

        record = statement_record(words, example_profile("example_checking"))

        self.assertEqual(
            ["CARD PAYMENT FICTION"],
            [t.description for t in record.transactions if t.is_transfer],
        )

    def test_rejects_a_statement_that_does_not_reconcile(self) -> None:
        words = checking_words() + row(85, "02/01", "UNSTATED FEE", debit="1.00")

        with self.assertRaises(UnreconciledStatementError):
            statement_record(words, example_profile("example_checking"))


class TestCardStatementRecord(unittest.TestCase):
    def setUp(self) -> None:
        self.record = statement_record(card_words(), example_profile("example_card"))

    def test_uses_the_profile_as_the_account_without_a_reference(self) -> None:
        self.assertEqual(AccountKey("Example Bank", "credit_card", "example_card"), self.record.account)
        self.assertEqual((date(2026, 3, 1), date(2026, 3, 31)), (self.record.period_start, self.record.period_end))

    def test_balance_is_previous_amount_due_and_amount_due(self) -> None:
        (balance,) = self.record.balances

        self.assertEqual(("EUR", Decimal("120.00"), Decimal("242.50")), (balance.currency, balance.opening, balance.closing))

    def test_charges_are_negative_and_payments_positive_transfers(self) -> None:
        payment, cafe = self.record.transactions[:2]

        self.assertEqual((Decimal("120.00"), True), (payment.amount, payment.is_transfer))
        self.assertEqual((Decimal("-12.50"), False), (cafe.amount, cafe.is_transfer))

    def test_skips_unbilled_entries_and_keeps_installments(self) -> None:
        descriptions = [t.description for t in self.record.transactions]
        furniture = self.record.transactions[3]

        self.assertNotIn("GADGET STORE", descriptions)
        self.assertEqual((3, 6, Decimal("-200.00")), (furniture.installment, furniture.installments, furniture.amount))
        self.assertEqual("1200.00", furniture.details["amount"])

    def test_keeps_foreign_entries_in_their_currency(self) -> None:
        foreign = [t for t in self.record.transactions if t.currency == "USD"]

        self.assertEqual([Decimal("-48.60"), Decimal("-10.00")], [t.amount for t in foreign])
        self.assertEqual("45.00", foreign[0].details["original_amount"])


def balance(start, end, opening, closing, currency="EUR"):
    return PeriodBalance(start, end, currency, Decimal(opening), Decimal(closing))


class TestContinuity(unittest.TestCase):
    def test_contiguous_statements_have_no_issues(self) -> None:
        balances = [
            balance(date(2026, 2, 1), date(2026, 2, 28), "0", "50"),
            balance(date(2026, 2, 28), date(2026, 3, 31), "50", "70"),
            balance(date(2026, 4, 1), date(2026, 4, 30), "70", "10"),
        ]

        self.assertEqual([], check_continuity(reversed(balances)))

    def test_a_balance_break_means_a_missing_statement(self) -> None:
        balances = [
            balance(date(2026, 1, 1), date(2026, 1, 31), "0", "50"),
            balance(date(2026, 3, 1), date(2026, 3, 31), "80", "90"),
        ]

        (issue,) = check_continuity(balances)

        self.assertEqual(("balance", date(2026, 1, 31)), (issue.kind, issue.previous.period_end))

    def test_a_gap_with_chained_balances_is_a_skipped_period(self) -> None:
        balances = [
            balance(date(2026, 1, 1), date(2026, 1, 31), "10", "0"),
            balance(date(2026, 3, 1), date(2026, 3, 31), "0", "30"),
        ]

        self.assertEqual(["gap"], [issue.kind for issue in check_continuity(balances)])

    def test_overlapping_periods_are_reported(self) -> None:
        first = balance(date(2026, 1, 1), date(2026, 1, 31), "0", "5")
        second = replace(first, period_start=date(2026, 1, 15), period_end=date(2026, 2, 15), opening=Decimal(5))

        self.assertEqual(["overlap"], [issue.kind for issue in check_continuity([first, second])])

    def test_currencies_chain_separately(self) -> None:
        balances = [
            balance(date(2026, 1, 1), date(2026, 1, 31), "0", "5"),
            balance(date(2026, 1, 1), date(2026, 1, 31), "0", "7", "USD"),
            balance(date(2026, 2, 1), date(2026, 2, 28), "5", "6"),
            balance(date(2026, 2, 1), date(2026, 2, 28), "7", "8", "USD"),
        ]

        self.assertEqual([], check_continuity(balances))


if __name__ == "__main__":
    unittest.main()
