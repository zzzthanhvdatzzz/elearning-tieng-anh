"""Chuyển file Markdown đơn giản sang .docx (Times New Roman 13, bảng có viền).

Dùng: ~/.venv-docx/bin/python scripts/md_to_docx.py docs/BAO_CAO_CAP_NHAT_Chuong3.md
"""
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm


def add_table(doc, rows):
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=cols)
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        for j in range(cols):
            text = row[j] if j < len(row) else ""
            cells[j].text = ""
            p = cells[j].paragraphs[0]
            run = p.add_run(text)
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
            run.bold = (i == 0)


def convert(md_path: Path, out_path: Path) -> Path:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(13)

    table_buf = []
    para_buf = []

    def _runs(paragraph, text: str):
        """Bỏ dấu `backtick`, biến **đậm** thành run in đậm thật."""
        clean = text.replace("`", "")
        for i, part in enumerate(clean.split("**")):
            if not part:
                continue
            run = paragraph.add_run(part)
            run.font.name = "Times New Roman"
            run.bold = (i % 2 == 1)

    def flush_para():
        if para_buf:
            text = " ".join(para_buf).strip()
            if text:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(6)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                _runs(p, text)
            para_buf.clear()

    def flush_table():
        if table_buf:
            add_table(doc, table_buf)
            doc.add_paragraph()
            table_buf.clear()

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("|"):
            flush_para()
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue                      # dòng phân cách của bảng markdown
            table_buf.append(cells)
            continue
        flush_table()

        if not line.strip():
            flush_para()
            continue

        if line.startswith("#"):
            flush_para()
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            h = doc.add_heading(text, level=min(level, 3))
            for run in h.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(15 if level <= 1 else 14 if level == 2 else 13)
            continue

        if line.strip() in ("---", "***"):
            flush_para()
            doc.add_paragraph("─" * 40).alignment = WD_ALIGN_PARAGRAPH.CENTER
            continue

        if line.lstrip().startswith(("- ", "* ")):
            flush_para()
            p = doc.add_paragraph(line.lstrip()[2:], style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            continue

        if line.lstrip().startswith("> "):
            flush_para()
            p = doc.add_paragraph(line.lstrip()[2:])
            p.runs[0].italic = True
            continue

        para_buf.append(line)

    flush_table()
    flush_para()

    for section in doc.sections:
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)

    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".docx")
    out = convert(src, dst)
    print(f"{out} — {out.stat().st_size} bytes")
