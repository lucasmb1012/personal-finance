"""Parse statements whose entries are single text lines matched by patterns.

Such statements group entries into sections and state totals between them.
Every total is checked against the entries read since the previous total, so a
line that no pattern recognizes shows up as a failed check instead of silently
disappearing.
"""

import re
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from personal_finance.statements.models import (
    Check,
    PatternEntry,
    StatementFormatError,
    StatementPart,
    Word,
)
from personal_finance.statements.profiles import LinePatternProfile, PartProfile, SectionRule
from personal_finance.statements.text import group_lines, parse_amount

DEFAULT_SECTION = SectionRule(name="default", pattern=re.compile(""), billed=True)


def parse_line_patterns(
    words: Iterable[Word], profile: LinePatternProfile
) -> tuple[StatementPart, ...]:
    """Split the statement into its parts and parse each one."""
    parts: list[StatementPart] = []
    current: PartProfile | None = None
    texts: list[str] = []
    for line in group_lines(words, profile.line_tolerance):
        started = next((part for part in profile.parts if part.start.search(line.text)), None)
        if started is not None and started is not current:
            if current is not None:
                parts.append(_PartParser(current).parse(texts))
            current, texts = started, []
        elif current is not None:
            texts.append(line.text)
    if current is not None:
        parts.append(_PartParser(current).parse(texts))
    return tuple(parts)


class _PartParser:
    def __init__(self, part: PartProfile) -> None:
        self.part = part
        self.entries: list[PatternEntry] = []
        self.checks: list[Check] = []
        self.values: dict[str, Decimal] = {}
        self.grand_total: Decimal | None = None
        self.section = DEFAULT_SECTION
        self.since_total = Decimal(0)
        self.since_subtotal = Decimal(0)
        self.totals_sum = Decimal(0)

    def parse(self, texts: list[str]) -> StatementPart:
        for text in texts:
            self._read(text)
        if self.part.totals:
            self.checks.append(Check("entries after the last total", Decimal(0), self.since_total))
        if self.part.grand_total is not None:
            self._check_grand_total()
        return StatementPart(
            name=self.part.name,
            currency=self.part.currency,
            entries=tuple(self.entries),
            checks=tuple(self.checks),
        )

    def _read(self, text: str) -> None:
        for section in self.part.sections:
            if section.pattern.search(text):
                self.section = section
                return
        for index, total in enumerate(self.part.totals):
            if match := total.pattern.search(text):
                self._total(match, index, total.subtotal)
                return
        for pattern in self.part.entry_patterns:
            if match := pattern.search(text):
                self._entry(match)
                return
        for name, pattern in self.part.values.items():
            if name not in self.values and (match := pattern.search(text)):
                self.values[name] = self._amount(match["amount"])
                return
        grand = self.part.grand_total
        if grand is not None and self.grand_total is None and (match := grand.pattern.search(text)):
            self.grand_total = self._amount(match["amount"])

    def _total(self, match: re.Match[str], index: int, subtotal: bool) -> None:
        stated = self._amount(match["amount"])
        label = match.groupdict().get("label") or f"#{index}"
        if subtotal:
            self.checks.append(Check(f"subtotal {label}", stated, self.since_subtotal))
            self.since_subtotal = Decimal(0)
            return
        self.checks.append(Check(f"total {label}", stated, self.since_total))
        self.totals_sum += stated
        self.since_total = Decimal(0)
        self.since_subtotal = Decimal(0)

    def _entry(self, match: re.Match[str]) -> None:
        fields = {name: self._field(name, value) for name, value in match.groupdict().items()}
        entry = PatternEntry(
            section=self.section.name,
            billed=self.section.billed,
            amount=fields[self.part.amount_field],
            fields=fields,
        )
        self.entries.append(entry)
        if entry.billed:
            self.since_total += entry.amount
            self.since_subtotal += entry.amount

    def _field(self, name: str, value: str | None) -> object:
        if value is None:
            return None
        if name in self.part.amount_fields:
            return self._amount(value)
        if name in self.part.date_fields:
            try:
                return datetime.strptime(value, self.part.date_fields[name]).date()
            except ValueError:
                raise StatementFormatError(f"Field {name!r} is not a valid date.") from None
        if name in self.part.integer_fields:
            return int(value)
        return value.strip()

    def _amount(self, text: str) -> Decimal:
        return parse_amount(text, self.part.amount_format)

    def _check_grand_total(self) -> None:
        grand = self.part.grand_total
        assert grand is not None
        if self.grand_total is None:
            raise StatementFormatError(f"Part {self.part.name!r} found no grand total.")
        missing = [name for name in grand.plus if name not in self.values]
        if missing:
            raise StatementFormatError(
                f"Part {self.part.name!r} is missing values: {', '.join(missing)}."
            )
        computed = self.totals_sum + sum((self.values[name] for name in grand.plus), Decimal(0))
        self.checks.append(Check("grand total", self.grand_total, computed))
