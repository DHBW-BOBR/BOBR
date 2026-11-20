"""Gemeinsame Test-Fixtures."""

import pytest


@pytest.fixture
def make_pdf():
    """Baut ein minimales, gültiges PDF mit Textlayer (korrekte xref-Offsets)."""

    def _make(lines: list[str]) -> bytes:
        content = "BT /F1 12 Tf 72 760 Td 14 TL\n"
        for ln in lines:
            esc = ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content += f"({esc}) Tj T*\n"
        content += "ET"
        objs = [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
        pdf = "%PDF-1.4\n"
        offsets = []
        for i, body in enumerate(objs, start=1):
            offsets.append(len(pdf))
            pdf += f"{i} 0 obj\n{body}\nendobj\n"
        xref_pos = len(pdf)
        pdf += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
        for off in offsets:
            pdf += f"{off:010d} 00000 n \n"
        pdf += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF"
        return pdf.encode("latin-1")

    return _make
