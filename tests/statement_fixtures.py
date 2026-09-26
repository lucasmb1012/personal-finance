"""Synthetic statement words for tests. Every name, amount, and date is fictional."""

from pathlib import Path

from personal_finance.statements.models import Word
from personal_finance.statements.profiles import load_profiles

EXAMPLE_PROFILES = Path(__file__).resolve().parent.parent / "examples" / "statement_profiles.example.toml"
CHARACTER_WIDTH = 5.0


def example_profile(name: str):
    return load_profiles(EXAMPLE_PROFILES)[name]


def text_words(lines: list[str], page: int = 1, x0: float = 20.0) -> list[Word]:
    """Lay out each text line on its own baseline, words left to right."""
    words: list[Word] = []
    for number, line in enumerate(lines):
        left = x0
        for text in line.split():
            width = len(text) * CHARACTER_WIDTH
            words.append(Word(text, left, left + width, 20.0 * (number + 1), page))
            left += width + CHARACTER_WIDTH
    return words


def left_aligned(text: str, x0: float, top: float, page: int = 1) -> list[Word]:
    return [Word(word.text, word.x0, word.x1, top, page) for word in text_words([text], page, x0)]


def right_aligned(text: str, x1: float, top: float, page: int = 1) -> Word:
    return Word(text, x1 - len(text) * CHARACTER_WIDTH, x1, top, page)
