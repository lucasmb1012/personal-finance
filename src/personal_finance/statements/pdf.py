"""PDF adapter: extract positioned words from a statement file."""

from pathlib import Path

import pdfplumber

from personal_finance.statements.models import Word


def read_words(path: Path, password: str | None = None) -> list[Word]:
    """Return every word on every page, dropping words placed outside the page."""
    words: list[Word] = []
    with pdfplumber.open(Path(path), password=password) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            for word in page.extract_words():
                if word["x1"] <= 0 or word["x0"] >= page.width:
                    continue
                words.append(
                    Word(
                        text=word["text"],
                        x0=float(word["x0"]),
                        x1=float(word["x1"]),
                        top=float(word["top"]),
                        page=number,
                    )
                )
    return words
