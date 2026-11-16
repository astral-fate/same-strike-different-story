"""paper/report.md -> Apart template DOCX -> PDF (via MS Word).
Supports: '# ' title, '## '/'### ' headings, paragraphs, '- ' bullets, pipe tables, ![caption](path), **bold**, *italic*."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TEMPLATE = ROOT.parents[1] / "02_Guidelines" / "template" / "Apart_Sprint_Report_Template.docx"
SRC = HERE / "report.md"
OUT = HERE / "Same_Strike_Different_Story.docx"
FONT = "Arial"
INK = RGBColor(17, 24, 39)


def runs(p, text, size=10, color=INK, italic=False):
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text):
        if not part:
            continue
        bold = part.startswith("**")
        ital = italic or (part.startswith("*") and not bold)
        code = part.startswith("`")
        t = part.strip("*`") if (bold or ital and part.startswith("*") or code) else part
        r = p.add_run(t)
        r.font.name = "Consolas" if code else FONT
        r.font.size = Pt(size - (1 if code else 0))
        r.font.bold = bold
        r.font.italic = ital and not bold
        r.font.color.rgb = color


def para(doc, text, size=10, after=6, italic=False, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.12
    if align:
        p.alignment = align
    runs(p, text, size=size, italic=italic)
    return p


def table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
    t = doc.add_table(rows=len(cells), cols=len(cells[0]))
    try:
        t.style = "Table Grid"
    except KeyError:  # template lacks the style: draw thin borders directly
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{edge}")
            for k, v in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", "9CA3AF")):
                el.set(qn(f"w:{k}"), v)
            borders.append(el)
        t._tbl.tblPr.append(borders)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(cells):
        for j, c in enumerate(r):
            cell = t.cell(i, j)
            cell.paragraphs[0].text = ""
            runs(cell.paragraphs[0], f"**{c}**" if i == 0 and c else c, size=8)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def build():
    doc = docx.Document(TEMPLATE)
    body = doc.element.body
    for el in list(body):
        if el.tag.endswith("sectPr"):
            continue
        body.remove(el)
    lines = [re.sub(r"\s*<!--.*?-->", "", l) for l in SRC.read_text(encoding="utf-8").splitlines()]
    i = 0
    buf: list[str] = []

    def flush():
        if buf:
            para(doc, " ".join(buf))
            buf.clear()

    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            flush(); i += 1; continue
        if ln.startswith("<!--"):
            while "-->" not in lines[i]:
                i += 1
            i += 1; continue
        if ln.startswith("# "):
            flush(); p = para(doc, f"**{ln[2:]}**", size=18, after=6)
        elif ln.startswith("## "):
            flush(); p = para(doc, f"**{ln[3:]}**", size=13, after=4); p.paragraph_format.space_before = Pt(10); p.paragraph_format.keep_with_next = True
        elif ln.startswith("### "):
            flush(); p = para(doc, f"**{ln[4:]}**", size=11, after=3); p.paragraph_format.space_before = Pt(6); p.paragraph_format.keep_with_next = True
        elif ln.startswith("- "):
            flush(); p = doc.add_paragraph(style="List Bullet") if "List Bullet" in [s.name for s in doc.styles] else doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            runs(p, ln[2:] if p.style.name == "List Bullet" else "• " + ln[2:], size=10)
        elif ln.startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            table(doc, rows); continue
        elif m := re.match(r"!\[(.*)\]\((.*)\)", ln):
            flush()
            img = (HERE / m.group(2)).resolve()
            from PIL import Image
            w, h = Image.open(img).size
            doc.add_picture(str(img), width=Inches(6.0 if h < w else 3.9))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            para(doc, m.group(1), size=8.5, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
        elif ln.startswith(">"):
            flush(); para(doc, ln.lstrip("> "), size=9.5, italic=True)
        else:
            buf.append(ln.strip())
        i += 1
    flush()
    doc.save(OUT)
    print("docx ->", OUT)


def to_pdf():
    import win32com.client  # pywin32
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    try:
        d = word.Documents.Open(str(OUT))
        pdf = OUT.with_suffix(".pdf")
        d.SaveAs(str(pdf), FileFormat=17)
        d.Close(False)
        print("pdf  ->", pdf)
    finally:
        word.Quit()


if __name__ == "__main__":
    build()
    if "--no-pdf" not in sys.argv:
        to_pdf()
