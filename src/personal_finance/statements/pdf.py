"""PDF adapter: extract positioned words from a statement file."""

from pathlib import Path

import pdfplumber

from personal_finance.statements.models import Word

# Some generators write dashes and minus signs as U+2212 instead of a hyphen.
MINUS_SIGN = "\u2212"


def read_words(path: Path, password: str | None = None) -> list[Word]:
    """Return every word on every page, dropping words placed outside the page.

    Minus signs are normalized to hyphens so that dates and negative amounts
    read the same whichever character the generator used.
    """
    words: list[Word] = []
    with pdfplumber.open(Path(path), password=password) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            for word in page.extract_words():
                if word["x1"] <= 0 or word["x0"] >= page.width:
                    continue
                words.append(
                    Word(
                        text=normalize_text(word["text"]),
                        x0=float(word["x0"]),
                        x1=float(word["x1"]),
                        top=float(word["top"]),
                        page=number,
                    )
                )
    return words


def normalize_text(text: str) -> str:
    """Write minus signs as hyphens."""
    return text.replace(MINUS_SIGN, "-")
