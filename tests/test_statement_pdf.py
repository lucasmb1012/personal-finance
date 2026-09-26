"""Tests for the PDF adapter, using a minimal PDF generated in the test."""

import tempfile
import unittest
from pathlib import Path

from personal_finance.statements.pdf import read_words


def minimal_pdf(texts: list[tuple[float, float, str]]) -> bytes:
    """Build a one-page PDF that draws each text at a position (x, y from bottom)."""
    content = "".join(f"BT /F1 10 Tf {x} {y} Td ({text}) Tj ET\n" for x, y, text in texts).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(document)
    document += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    document += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    document += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    document += b"startxref\n%d\n%%%%EOF\n" % xref
    return bytes(document)


class TestReadWords(unittest.TestCase):
    def test_returns_positioned_words_and_drops_off_page_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.pdf"
            path.write_bytes(minimal_pdf([(50, 800, "FICTIONAL"), (300, 700, "12.50"), (900, 700, "HIDDEN")]))

            words = read_words(path)

        self.assertEqual(["FICTIONAL", "12.50"], [word.text for word in words])
        self.assertAlmostEqual(50, words[0].x0, places=0)
        self.assertLess(words[0].top, words[1].top)
        self.assertEqual({1}, {word.page for word in words})
