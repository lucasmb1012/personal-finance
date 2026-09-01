"""Smoke tests for the project package."""

import unittest


class TestPackage(unittest.TestCase):
    def test_package_imports(self) -> None:
        import personal_finance

        self.assertIsNotNone(personal_finance)
