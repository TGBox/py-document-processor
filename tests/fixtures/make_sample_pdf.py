"""Regenerate ``sample.pdf``: two A4 pages with known, synthetic text.

Not part of the test run. Usage:
    uv run --with reportlab python tests/fixtures/make_sample_pdf.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PAGE_TEXTS = ["Seite eins Alpha", "Seite zwei Beta"]


def main() -> None:
    target = Path(__file__).with_name("sample.pdf")
    pdf = canvas.Canvas(str(target), pagesize=A4, invariant=1)
    pdf.setTitle("py-document-processor test fixture")
    for text in PAGE_TEXTS:
        pdf.setFont("Helvetica", 24)
        pdf.drawString(72, A4[1] - 100, text)
        pdf.showPage()
    pdf.save()
    print(f"written: {target}")


if __name__ == "__main__":
    main()
