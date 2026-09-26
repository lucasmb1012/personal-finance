"""Tests for Gmail search configuration and token storage."""

import stat
import tempfile
import unittest
from pathlib import Path

from personal_finance.gmail.authentication import _save_token
from personal_finance.gmail.configuration import load_search_queries


class TestLoadSearchQueries(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        self.path = Path(self._directory.name) / "searches.toml"

    def test_returns_named_queries(self) -> None:
        self.path.write_text(
            '[searches]\ncard_purchase = "from:alerts@bank.example"\n',
            encoding="utf-8",
        )

        queries = load_search_queries(self.path)

        self.assertEqual({"card_purchase": "from:alerts@bank.example"}, queries)

    def test_rejects_missing_searches_table(self) -> None:
        self.path.write_text('title = "no searches"\n', encoding="utf-8")

        with self.assertRaisesRegex(ValueError, r"\[searches\]"):
            load_search_queries(self.path)

    def test_rejects_blank_query_without_echoing_other_values(self) -> None:
        self.path.write_text(
            '[searches]\nvalid = "from:alerts@bank.example"\nblank = " "\n',
            encoding="utf-8",
        )

        with self.assertRaises(ValueError) as context:
            load_search_queries(self.path)

        self.assertIn("'blank'", str(context.exception))
        self.assertNotIn("bank.example", str(context.exception))


class TestSaveToken(unittest.TestCase):
    def test_token_is_readable_only_by_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            token_path = Path(directory) / "nested" / "token.json"

            _save_token(token_path, '{"token": "synthetic"}')

            mode = stat.S_IMODE(token_path.stat().st_mode)
            self.assertEqual(0o600, mode)
            self.assertEqual('{"token": "synthetic"}', token_path.read_text(encoding="utf-8"))

    def test_existing_token_permissions_are_tightened(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            token_path = Path(directory) / "token.json"
            token_path.write_text("{}", encoding="utf-8")
            token_path.chmod(0o644)

            _save_token(token_path, "{}")

            self.assertEqual(0o600, stat.S_IMODE(token_path.stat().st_mode))
