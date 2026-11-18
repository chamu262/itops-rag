"""Build the demo vendor PDFs from Markdown sources, so the PDF loader is exercised on real PDF files.

    python scripts/build_demo_pdfs.py

Reads data/demo/sources/vendor/*.md (front matter + Markdown) and writes data/demo/kestrel-cloud/vendor/<name>.pdf
plus a <name>.meta.yaml sidecar with the front matter. Needs the dev dependency fpdf2.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import yaml
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "demo" / "sources" / "vendor"
OUT = ROOT / "data" / "demo" / "kestrel-cloud" / "vendor"

_REPLACE = {
    "—": "-",
    "–": "-",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    "→": "->",
    " ": " ",
    "•": "-",
    "≤": "<=",
    "≥": ">=",
    "✓": "v",
    "×": "x",
}


def latin1(text: str) -> str:
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def build(md_path: Path) -> Path:
    raw = md_path.read_text(encoding="utf-8")
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    meta = yaml.safe_load(m.group(1)) if m else {}
    body = raw[m.end() :] if m else raw

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title(latin1(str(meta.get("title", md_path.stem))))
    pdf.set_author("Kestrel Cloud IT (fictional)")
    pdf.set_creation_date(datetime(2026, 1, 1, tzinfo=UTC))  # fixed date: reproducible output
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin
    in_code = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        text = latin1(line.rstrip())
        if in_code:
            pdf.set_font("Courier", size=8)
            pdf.multi_cell(width, 4, text or " ", new_x="LMARGIN", new_y="NEXT")
            continue
        h = re.match(r"^(#{1,6})\s+(.*)", text)
        if h:
            size = {1: 15, 2: 12, 3: 11}.get(len(h.group(1)), 10)
            pdf.set_font("Helvetica", "B", size)
            pdf.ln(2)
            pdf.multi_cell(width, size * 0.55, h.group(2), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            continue
        pdf.set_font("Helvetica", size=9.5)
        text = re.sub(r"\*\*(.+?)\*\*|`(.+?)`", lambda mm: mm.group(1) or mm.group(2), text)
        pdf.multi_cell(width, 4.8, text or " ", new_x="LMARGIN", new_y="NEXT")

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{md_path.stem}.pdf"
    pdf.output(str(out))
    out.with_suffix(".meta.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    return out


def main() -> None:
    for md in sorted(SRC.glob("*.md")):
        print(f"built {build(md).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
