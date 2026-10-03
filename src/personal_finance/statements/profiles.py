"""Local statement profiles: the layout details of one institution's statements.

Profiles identify the operator's financial institutions, so they live in an
ignored local file. Error messages name profiles and keys but never echo
patterns or other values.
"""

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_LINE_TOLERANCE = 3.0
ACCOUNT_COLUMNS = ("date", "description", "debit", "credit", "balance")
ACCOUNT_KINDS = ("checking", "demand_deposit", "credit_card")


@dataclass(frozen=True)
class AmountFormat:
    thousands: str
    decimal: str


@dataclass(frozen=True)
class Column:
    """A table column: words whose ``anchor`` edge lies in [minimum, maximum)."""

    name: str
    anchor: str
    minimum: float
    maximum: float


@dataclass(frozen=True)
class AccountRule:
    """Which account a statement belongs to, and which of its entries are transfers.

    ``reference`` finds the account number on the statement; only its last four
    digits are kept. Without it, statements of the profile share one account.
    ``aliases`` map a replaced number's last four digits to the current ones,
    so a replaced card stays one account. ``transfers`` match entry
    descriptions that move money between the operator's own accounts, such as
    a card payment from a checking account.
    """

    institution: str
    kind: str
    currency: str
    reference: re.Pattern[str] | None = None
    aliases: Mapping[str, str] = field(default_factory=dict)
    transfers: tuple[re.Pattern[str], ...] = ()


@dataclass(frozen=True)
class ColumnTableProfile:
    """A statement laid out as a table whose columns are found by position.

    The opening and closing balances come either from rows whose description
    matches ``opening_balance`` and ``closing_balance``, or from one
    ``summary`` line with ``opening`` and ``closing`` groups.
    """

    name: str
    detect: re.Pattern[str]
    amount_format: AmountFormat
    header: re.Pattern[str]
    footer: re.Pattern[str]
    row_start: re.Pattern[str]
    date_format: str
    period: re.Pattern[str]
    period_date_format: str
    opening_balance: re.Pattern[str] | None
    closing_balance: re.Pattern[str] | None
    columns: tuple[Column, ...]
    line_tolerance: float = DEFAULT_LINE_TOLERANCE
    account: AccountRule | None = None
    summary: re.Pattern[str] | None = None


@dataclass(frozen=True)
class SectionRule:
    """A line that starts a section; entries of unbilled sections are informational."""

    name: str
    pattern: re.Pattern[str]
    billed: bool


@dataclass(frozen=True)
class TotalRule:
    """A line stating the total of the billed entries since the previous total."""

    pattern: re.Pattern[str]
    subtotal: bool


@dataclass(frozen=True)
class GrandTotalRule:
    """The amount due: every non-subtotal total plus the named ``plus`` values."""

    pattern: re.Pattern[str]
    plus: tuple[str, ...]


@dataclass(frozen=True)
class PartProfile:
    """One part of a line-pattern statement, such as the portion in one currency."""

    name: str
    currency: str
    start: re.Pattern[str]
    amount_format: AmountFormat
    entry_patterns: tuple[re.Pattern[str], ...]
    amount_field: str
    amount_fields: frozenset[str]
    date_fields: Mapping[str, str]
    integer_fields: frozenset[str]
    sections: tuple[SectionRule, ...] = ()
    totals: tuple[TotalRule, ...] = ()
    values: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    grand_total: GrandTotalRule | None = None


@dataclass(frozen=True)
class LinePatternProfile:
    """A statement whose entries are single text lines matched by patterns."""

    name: str
    detect: re.Pattern[str]
    parts: tuple[PartProfile, ...]
    line_tolerance: float = DEFAULT_LINE_TOLERANCE
    account: AccountRule | None = None
    period: re.Pattern[str] | None = None
    period_date_format: str | None = None


Profile = ColumnTableProfile | LinePatternProfile


def load_profiles(path: Path) -> dict[str, Profile]:
    """Return the statement profiles defined in a local TOML file."""
    with Path(path).open("rb") as profile_file:
        config = tomllib.load(profile_file)

    profiles = config.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("Statement profiles need a non-empty [profiles] table.")

    loaded: dict[str, Profile] = {}
    for name, table in profiles.items():
        reader = _Reader(f"profile {name!r}", table)
        engine = reader.string("engine")
        if engine == "column_table":
            loaded[name] = _column_table(name, reader)
        elif engine == "line_patterns":
            loaded[name] = _line_patterns(name, reader)
        else:
            raise ValueError(f"Profile {name!r} has an unknown engine.")
    return loaded


def _column_table(name: str, reader: "_Reader") -> ColumnTableProfile:
    columns = tuple(_column(column) for column in reader.tables("columns"))
    names = [column.name for column in columns]
    missing = [column for column in ACCOUNT_COLUMNS if column not in names]
    if missing:
        raise ValueError(f"Profile {name!r} is missing columns: {', '.join(missing)}.")
    summary = None
    opening_balance = closing_balance = None
    if "summary" in reader.table:
        summary = reader.pattern("summary", groups=("opening", "closing"))
    else:
        opening_balance = reader.pattern("opening_balance")
        closing_balance = reader.pattern("closing_balance")
    return ColumnTableProfile(
        name=name,
        detect=reader.pattern("detect"),
        amount_format=_amount_format(reader),
        header=reader.pattern("header"),
        footer=reader.pattern("footer"),
        row_start=reader.pattern("row_start"),
        date_format=reader.string("date_format"),
        period=reader.pattern("period", groups=("start", "end")),
        period_date_format=reader.string("period_date_format"),
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        columns=columns,
        line_tolerance=reader.number("line_tolerance", DEFAULT_LINE_TOLERANCE),
        account=_account(reader),
        summary=summary,
    )


def _column(reader: "_Reader") -> Column:
    anchor = reader.string("anchor")
    if anchor not in ("x0", "x1"):
        raise ValueError(f"{reader.context} needs an anchor of 'x0' or 'x1'.")
    return Column(
        name=reader.string("name"),
        anchor=anchor,
        minimum=reader.number("min"),
        maximum=reader.number("max"),
    )


def _line_patterns(name: str, reader: "_Reader") -> LinePatternProfile:
    period = None
    period_date_format = None
    if "period" in reader.table:
        period = reader.pattern("period", groups=("start", "end"))
        period_date_format = reader.string("period_date_format")
    return LinePatternProfile(
        name=name,
        detect=reader.pattern("detect"),
        parts=tuple(_part(part) for part in reader.tables("parts")),
        line_tolerance=reader.number("line_tolerance", DEFAULT_LINE_TOLERANCE),
        account=_account(reader),
        period=period,
        period_date_format=period_date_format,
    )


def _account(reader: "_Reader") -> AccountRule | None:
    if "account" not in reader.table:
        return None
    account = _Reader(f"{reader.context} account", reader.table["account"])
    kind = account.string("kind")
    if kind not in ACCOUNT_KINDS:
        raise ValueError(f"{account.context} has an unknown kind.")
    aliases = account.optional_table("aliases")
    reference = None
    if "reference" in account.table:
        reference = account.pattern("reference", groups=("reference",))
    return AccountRule(
        institution=account.string("institution"),
        kind=kind,
        currency=account.string("currency"),
        reference=reference,
        aliases={key: aliases.string(key) for key in aliases.table},
        transfers=tuple(
            account.compile(f"transfers[{index}]", pattern)
            for index, pattern in enumerate(account.strings("transfers"))
        ),
    )


def _part(reader: "_Reader") -> PartProfile:
    amount_field = reader.string("amount_field")
    amount_fields = frozenset(reader.strings("amount_fields")) | {amount_field}
    entry_patterns = tuple(
        reader.compile(f"entry_patterns[{index}]", pattern, groups=(amount_field,))
        for index, pattern in enumerate(reader.strings("entry_patterns"))
    )
    if not entry_patterns:
        raise ValueError(f"{reader.context} needs at least one entry pattern.")
    date_fields = reader.optional_table("date_fields")
    values = reader.optional_table("values")
    grand_total = None
    if "grand_total" in reader.table:
        grand = _Reader(f"{reader.context} grand_total", reader.table["grand_total"])
        grand_total = GrandTotalRule(
            pattern=grand.pattern("pattern", groups=("amount",)),
            plus=tuple(grand.strings("plus")),
        )
        unknown = [value for value in grand_total.plus if value not in values.table]
        if unknown:
            raise ValueError(f"{grand.context} adds undefined values: {', '.join(unknown)}.")
    return PartProfile(
        name=reader.string("name"),
        currency=reader.string("currency"),
        start=reader.pattern("start"),
        amount_format=_amount_format(reader),
        entry_patterns=entry_patterns,
        amount_field=amount_field,
        amount_fields=amount_fields,
        date_fields={key: date_fields.string(key) for key in date_fields.table},
        integer_fields=frozenset(reader.strings("integer_fields")),
        sections=tuple(
            SectionRule(
                name=section.string("name"),
                pattern=section.pattern("pattern"),
                billed=section.boolean("billed"),
            )
            for section in reader.tables("sections")
        ),
        totals=tuple(
            TotalRule(
                pattern=total.pattern("pattern", groups=("amount",)),
                subtotal=total.boolean("subtotal", False),
            )
            for total in reader.tables("totals")
        ),
        values={key: values.pattern(key, groups=("amount",)) for key in values.table},
        grand_total=grand_total,
    )


def _amount_format(reader: "_Reader") -> AmountFormat:
    table = _Reader(f"{reader.context} amount_format", reader.table.get("amount_format"))
    return AmountFormat(thousands=table.string("thousands"), decimal=table.string("decimal"))


class _Reader:
    """Typed access to a TOML table, with errors that never echo values."""

    def __init__(self, context: str, table: Any) -> None:
        if not isinstance(table, dict):
            raise ValueError(f"{context} must be a table.")
        self.context = context
        self.table: dict[str, Any] = table

    def string(self, key: str) -> str:
        value = self.table.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{self.context} needs a non-empty string {key!r}.")
        return value

    def strings(self, key: str) -> list[str]:
        values = self.table.get(key, [])
        if not isinstance(values, list) or not all(
            isinstance(value, str) and value for value in values
        ):
            raise ValueError(f"{self.context} needs {key!r} to be a list of strings.")
        return values

    def number(self, key: str, default: float | None = None) -> float:
        value = self.table.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{self.context} needs a number {key!r}.")
        return float(value)

    def boolean(self, key: str, default: bool | None = None) -> bool:
        value = self.table.get(key, default)
        if not isinstance(value, bool):
            raise ValueError(f"{self.context} needs a boolean {key!r}.")
        return value

    def pattern(self, key: str, groups: tuple[str, ...] = ()) -> re.Pattern[str]:
        return self.compile(key, self.string(key), groups)

    def compile(self, key: str, pattern: str, groups: tuple[str, ...] = ()) -> re.Pattern[str]:
        try:
            compiled = re.compile(pattern, re.MULTILINE)
        except re.error:
            raise ValueError(f"{self.context} has an invalid pattern {key!r}.") from None
        missing = [group for group in groups if group not in compiled.groupindex]
        if missing:
            raise ValueError(
                f"{self.context} pattern {key!r} needs named groups: {', '.join(missing)}."
            )
        return compiled

    def tables(self, key: str) -> list["_Reader"]:
        tables = self.table.get(key, [])
        if not isinstance(tables, list):
            raise ValueError(f"{self.context} needs {key!r} to be an array of tables.")
        return [_Reader(f"{self.context} {key}[{index}]", table) for index, table in enumerate(tables)]

    def optional_table(self, key: str) -> "_Reader":
        return _Reader(f"{self.context} {key}", self.table.get(key, {}))
