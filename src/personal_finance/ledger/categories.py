"""Assign categories to transactions with ordered local rules.

Rules name merchants and people the operator deals with, so they live in an
ignored local file; the repository ships a fictional example. Categorizing is a
pure function of the rules, a description, and an amount, so re-running it with
the same rules always gives the same result.
"""

import re
import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

DIRECTIONS = ("in", "out")


@dataclass(frozen=True)
class CategoryRule:
    """Descriptions matching any pattern get ``category``.

    ``direction`` limits the rule to money in (``in``) or out (``out``).
    """

    category: str
    patterns: tuple[re.Pattern[str], ...]
    direction: str | None = None

    def matches(self, description: str, amount: Decimal) -> bool:
        if self.direction == "in" and amount <= 0:
            return False
        if self.direction == "out" and amount >= 0:
            return False
        return any(pattern.search(description) for pattern in self.patterns)


def load_category_rules(path: Path) -> tuple[CategoryRule, ...]:
    """Return the rules of a local TOML file, in file order."""
    with Path(path).open("rb") as rules_file:
        config = tomllib.load(rules_file)
    tables = config.get("rules")
    if not isinstance(tables, list) or not tables:
        raise ValueError("Category rules need a non-empty [[rules]] array.")
    return tuple(_rule(index, table) for index, table in enumerate(tables))


def categorize(rules: tuple[CategoryRule, ...], description: str, amount: Decimal) -> str | None:
    """Return the category of the first matching rule, or None."""
    for rule in rules:
        if rule.matches(description, amount):
            return rule.category
    return None


def _rule(index: int, table: object) -> CategoryRule:
    context = f"rules[{index}]"
    if not isinstance(table, dict):
        raise ValueError(f"{context} must be a table.")
    category = table.get("category")
    if not isinstance(category, str) or not category:
        raise ValueError(f"{context} needs a non-empty string 'category'.")
    patterns = table.get("patterns")
    if not isinstance(patterns, list) or not patterns or not all(
        isinstance(pattern, str) and pattern for pattern in patterns
    ):
        raise ValueError(f"{context} needs 'patterns' to be a non-empty list of strings.")
    direction = table.get("direction")
    if direction is not None and direction not in DIRECTIONS:
        raise ValueError(f"{context} has a direction other than 'in' or 'out'.")
    compiled = []
    for number, pattern in enumerate(patterns):
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            raise ValueError(f"{context} has an invalid pattern {number}.") from None
    return CategoryRule(category, tuple(compiled), direction)
