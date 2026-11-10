#!/usr/bin/env python3
"""Build the editable Word manuscript from Markdown + CSL JSON references.

Usage (from the project root):
  python scripts/build_docx.py --md 06_manuscript/manuscript.md --bib 06_manuscript/references.json \
      --csl 06_manuscript/citation_style.csl --out 08_final/<slug>_review_manuscript.docx \
      [--ref-doc 06_manuscript/reference.docx | --font "Times New Roman" --size 12 --spacing 1.5 --page a4] \
      [--toc] [--line-numbers] [--running-head "Short title"] [--title ..] [--author ..] [--keywords ..]

Pipeline: pandoc (+citeproc: real in-text citations and a formatted reference list, native Word tables,
figures, footnotes, equations) -> python-docx polish (academic table borders, repeating header rows,
SEQ-field captions, image scaling, page-number footer, optional line numbers, document properties)
-> optional validation with the docx skill's validate.py.
Exit code 2 if citations could not be resolved or pandoc failed: do not treat the file as final then.
Citations render as formatted text (not live Zotero/EndNote fields); export references.json for those tools.
"""
import argparse, copy, re, shutil, subprocess, sys
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def get_style(d, name):
    """Case-insensitive style lookup (pandoc's names differ in case from python-docx's built-in aliases)."""
    for st in d.styles:
        if st.name and (st.name.lower() == name.lower() or (st.style_id or "").lower() == name.replace(" ", "").lower()):
            return st
    raise KeyError(name)


def make_reference_doc(path, font, size, spacing, page, margin_in):
    """Generate a pandoc reference.docx with scholarly styles (only when none is supplied)."""
    with open(path, "wb") as fh:
        subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"], stdout=fh, check=True)
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor
    d = docx.Document(str(path))

    def setfont(st, sz=None, bold=None, italic=None, color=True):
        st.font.name = font
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.append(rf)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), font)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
            if rf.get(qn(a)) is not None:
                del rf.attrib[qn(a)]
        if sz:
            st.font.size = Pt(sz)
        if bold is not None:
            st.font.bold = bold
        if italic is not None:
            st.font.italic = italic
        if color:
            st.font.color.rgb = RGBColor(0, 0, 0)
            ce = rpr.find(qn("w:color"))
            for att in ("w:themeColor", "w:themeShade", "w:themeTint"):  # theme colour would override rgb
                if ce is not None and ce.get(qn(att)) is not None:
                    del ce.attrib[qn(att)]

    body = {"Normal": size, "Body Text": size, "First Paragraph": size, "Compact": size, "Block Text": size - 1,
            "Bibliography": size - 1, "Footnote Text": size - 2}
    heads = {"Title": (size + 6, True, False), "Subtitle": (size + 2, False, True), "Author": (size, False, False),
             "Date": (size, False, False), "Abstract": (size, False, False),
             "Heading 1": (size + 2, True, False), "Heading 2": (size + 1, True, False),
             "Heading 3": (size, True, True), "Heading 4": (size, False, True)}
    for name, sz in body.items():
        try:
            st = get_style(d, name)
            setfont(st, sz)
            pf = st.paragraph_format
            if name in ("Normal", "Body Text", "First Paragraph"):
                pf.line_spacing, pf.space_after, pf.space_before = spacing, Pt(6), Pt(0)
                pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            if name == "Bibliography":
                pf.left_indent, pf.first_line_indent, pf.space_after = Inches(0.4), Inches(-0.4), Pt(4)
        except KeyError:
            pass
    for name, (sz, b, i) in heads.items():
        try:
            st = get_style(d, name)
            setfont(st, sz, b, i)
            st.paragraph_format.keep_with_next = True
            if name.startswith("Heading"):
                st.paragraph_format.space_before, st.paragraph_format.space_after = Pt(14), Pt(6)
            if name in ("Title", "Subtitle", "Author", "Date"):
                st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        except KeyError:
            pass
    for name in ("Caption", "Table Caption", "Image Caption"):
        try:
            st = get_style(d, name)
            setfont(st, size - 1, False, False)
            st.paragraph_format.space_before, st.paragraph_format.space_after = Pt(6), Pt(8)
            st.paragraph_format.line_spacing = 1.0
        except KeyError:
            pass
    for s in d.sections:
        s.page_width, s.page_height = (Inches(8.27), Inches(11.69)) if page == "a4" else (Inches(8.5), Inches(11))
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(margin_in)
    d.save(str(path))


def run_pandoc(md, bib, csl, ref, out, toc, resource_paths, link_cites=False):
    cmd = ["pandoc", str(md), "-f", "markdown+smart+pipe_tables+table_captions+implicit_figures+footnotes+tex_math_dollars",
           "-t", "docx", "--standalone", "-o", str(out), "--reference-doc", str(ref),
           "--resource-path", ":".join(str(p) for p in resource_paths), "--metadata", f"link-citations={'true' if link_cites else 'false'}"]
    if bib:
        cmd += ["--citeproc", "--bibliography", str(bib)]
    if csl:
        cmd += ["--csl", str(csl)]
    if toc:
        cmd += ["--toc", "--toc-depth=3"]
    r = sh(cmd)
    return r.returncode, r.stderr



TBLPR_AFTER = ("shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription")
TCPR_AFTER = ("shd", "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark")


def insert_ordered(parent, child, qn, successors):
    """Insert child before the first existing successor element (keeps OOXML schema order)."""
    for el in parent:
        if el.tag in [qn("w:" + t) for t in successors]:
            el.addprevious(child)
            return
    parent.append(child)

def field_run(oxml, qn, instr, cached, bold=True):
    fld = oxml("w:fldSimple")
    fld.set(qn("w:instr"), f" {instr} ")
    r = oxml("w:r")
    if bold:
        rpr = oxml("w:rPr")
        rpr.append(oxml("w:b"))
        r.append(rpr)
    t = oxml("w:t")
    t.text = cached
    r.append(t)
    fld.append(r)
    return fld


def text_run(oxml, qn, text, bold=False):
    r = oxml("w:r")
    if bold:
        rpr = oxml("w:rPr")
        rpr.append(oxml("w:b"))
        r.append(rpr)
    t = oxml("w:t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    r.append(t)
    return r


def polish(path, a):
    import docx
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, Emu
    notes = []
    d = docx.Document(str(path))
    sec = d.sections[0]
    text_w = sec.page_width - sec.left_margin - sec.right_margin

    # tables: three-line academic look, repeating header, no split rows, smaller type
    for t in d.tables:
        tblPr = t._tbl.tblPr
        for old in tblPr.findall(qn("w:tblBorders")):
            tblPr.remove(old)
        b = OxmlElement("w:tblBorders")
        for side, val in (("top", "single"), ("left", "nil"), ("bottom", "single"), ("right", "nil"),
                          ("insideH", "nil"), ("insideV", "nil")):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:val"), val)
            if val == "single":
                e.set(qn("w:sz"), "8")
                e.set(qn("w:color"), "000000")
            b.append(e)
        jc = tblPr.find(qn("w:jc"))
        if jc is not None:  # pandoc emits jc after tblLook; schema wants it right after tblW
            tblPr.remove(jc)
            w_el = tblPr.find(qn("w:tblW"))
            (w_el.addnext(jc) if w_el is not None else tblPr.insert(0, jc))
        insert_ordered(tblPr, b, qn, TBLPR_AFTER)
        for ri, row in enumerate(t.rows):
            trPr = row._tr.get_or_add_trPr()
            trPr.append(OxmlElement("w:cantSplit"))
            if ri == 0:
                trPr.append(OxmlElement("w:tblHeader"))
                for c in row.cells:
                    tcPr = c._tc.get_or_add_tcPr()
                    bd = OxmlElement("w:tcBorders")
                    e = OxmlElement("w:bottom")
                    e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "6"); e.set(qn("w:color"), "000000")
                    bd.append(e)
                    insert_ordered(tcPr, bd, qn, TCPR_AFTER)
                    for p in c.paragraphs:
                        for r in p.runs:
                            r.bold = True
            for c in row.cells:
                for p in c.paragraphs:
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.line_spacing = 1.0
                    for r in p.runs:
                        r.font.size = Pt(a.size - 2.5)

    from docx.text.paragraph import Paragraph
    for t in d.tables:  # breathing room so a following figure/paragraph never touches the bottom rule
        nxt = t._tbl.getnext()
        if nxt is not None and nxt.tag == qn("w:p"):
            Paragraph(nxt, d.element.body).paragraph_format.space_before = Pt(10)

    # captions: Word SEQ fields so numbers renumber automatically when the user reorders items
    counters, caps = {"Table": 0, "Figure": 0}, 0
    for p in d.paragraphs:
        sname = p.style.name if p.style is not None else ""
        if sname not in ("Table Caption", "Image Caption", "Caption"):
            continue
        m = re.match(r"^\s*(Table|Figure|Fig\.)\s+(\d+)\s*([.:\u2013\u2014-])\s*", p.text)
        if not m:
            notes.append(f"caption without 'Table N.'/'Figure N.' prefix: {p.text[:60]!r}")
            continue
        label = "Figure" if m.group(1).startswith("Fig") else m.group(1)
        counters[label] += 1
        if int(m.group(2)) != counters[label]:
            notes.append(f"caption numbering out of sequence: typed {label} {m.group(2)}, position {counters[label]}")
        consumed = m.end()
        for r in list(p.runs):
            if consumed <= 0:
                break
            if len(r.text) <= consumed:
                consumed -= len(r.text)
                r._r.getparent().remove(r._r)
            else:
                r.text = r.text[consumed:]
                consumed = 0
        anchor = p._p.find(qn("w:r"))
        pieces = [text_run(OxmlElement, qn, label + " ", True),
                  field_run(OxmlElement, qn, f"SEQ {label} \\* ARABIC", str(counters[label])),
                  text_run(OxmlElement, qn, m.group(3) + " ", True)]
        for el in pieces:
            if anchor is not None:
                anchor.addprevious(el)
            else:
                p._p.append(el)
        if sname == "Table Caption":
            p.paragraph_format.keep_with_next = True
        caps += 1
    for p in d.paragraphs:
        if p.style is not None and p.style.name in ("Captioned Figure", "Figure"):
            p.paragraph_format.keep_with_next = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # images: fit to text width; report missing alt text
    no_alt = 0
    for s in d.inline_shapes:
        if s.width > text_w:
            ratio = text_w / s.width
            s.width, s.height = int(text_w), int(s.height * ratio)
    for dp in d.element.body.iter("{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr"):
        if not (dp.get("descr") or "").strip():
            no_alt += 1
    if no_alt:
        notes.append(f"{no_alt} image(s) without alt text: put alt text in the Markdown image brackets or add it in Word")

    # footer page numbers (+ optional running head), optional line numbering
    for s in d.sections:
        f = s.footer
        f.is_linked_to_previous = False
        p = f.paragraphs[0] if f.paragraphs else f.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for el in list(p._p):
            if el.tag != qn("w:pPr"):
                p._p.remove(el)
        p._p.append(field_run(OxmlElement, qn, "PAGE", "1", bold=False))
        if a.running_head:
            h = s.header
            h.is_linked_to_previous = False
            hp = h.paragraphs[0] if h.paragraphs else h.add_paragraph()
            hp.text = a.running_head
            hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for r in hp.runs:
                r.font.size = Pt(a.size - 2)
                r.italic = True
        if a.line_numbers:
            ln = OxmlElement("w:lnNumType")
            ln.set(qn("w:countBy"), "1")
            ln.set(qn("w:restart"), "continuous")
            pg = s._sectPr.find(qn("w:pgMar"))
            (pg.addnext(ln) if pg is not None else s._sectPr.append(ln))

    for s in d.sections:
        pg = s._sectPr.find(qn("w:pgMar"))
        if pg is not None:
            for k, v in (("header", "708"), ("footer", "708"), ("gutter", "0")):
                if pg.get(qn("w:" + k)) is None:
                    pg.set(qn("w:" + k), v)
    cp = d.core_properties
    if a.title:
        cp.title = a.title
    cp.author = a.author or ""
    cp.last_modified_by = a.author or ""
    cp.comments = ""
    if a.keywords:
        cp.keywords = a.keywords
    d.save(str(path))
    return counters, notes


def find_validator():
    for c in ("/mnt/skills/public/docx/scripts/office/validate.py",
              str(Path.home() / ".claude/skills/docx/scripts/office/validate.py")):
        if Path(c).exists():
            return c
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", required=True)
    ap.add_argument("--bib")
    ap.add_argument("--csl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref-doc")
    ap.add_argument("--font", default="Times New Roman")
    ap.add_argument("--size", type=float, default=11)
    ap.add_argument("--spacing", type=float, default=1.15)
    ap.add_argument("--page", choices=["a4", "letter"], default="a4")
    ap.add_argument("--margin-in", type=float, default=1.0)
    ap.add_argument("--toc", action="store_true")
    ap.add_argument("--link-citations", action="store_true", help="make in-text citations clickable (renders blue)")
    ap.add_argument("--line-numbers", action="store_true")
    ap.add_argument("--running-head")
    ap.add_argument("--title")
    ap.add_argument("--author")
    ap.add_argument("--keywords")
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args()

    if not shutil.which("pandoc"):
        sys.exit("pandoc not found. The Word manuscript cannot be built with this script; use the docx skill's docx-js route "
                 "and say so in the quality report. Do NOT claim the .docx deliverable is complete.")
    md, out = Path(a.md).resolve(), Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    ref = Path(a.ref_doc) if a.ref_doc else md.parent / "reference.docx"
    if not ref.exists():
        make_reference_doc(ref, a.font, a.size, a.spacing, a.page, a.margin_in)
        print(f"Generated reference styles -> {ref}")
    rc, err = run_pandoc(md, a.bib, a.csl, ref, out, a.toc, [md.parent, md.parent.parent, Path.cwd()], a.link_citations)
    if rc != 0:
        print(err)
        return 2
    missing = re.findall(r"citation (\S+) not found", err, re.I)
    if err.strip():
        print("pandoc messages:\n" + err.strip())
    counters, notes = polish(out, a)
    print(f"Built {out}\n  tables: {len([1 for _ in __import__('docx').Document(str(out)).tables])}, "
          f"table captions: {counters['Table']}, figure captions: {counters['Figure']}")
    for n in notes:
        print("  note: " + n)
    if not a.no_validate and find_validator():
        r = sh([sys.executable, find_validator(), str(out)])
        outp = (r.stdout + r.stderr)
        bad = set(re.findall(r"word/(\w+)\.xml: \d+ new error", outp))
        if "PASSED" in outp.split("\n")[0] or not bad:
            print("validate.py: passed" if "FAILED" not in outp else "validate.py: " + outp.strip()[:500])
        elif bad <= {"styles", "numbering", "settings"}:
            print("validate.py: document.xml is schema-clean. Strict-schema nits remain in " + ", ".join(sorted(bad)) +
                  ".xml, which pandoc's stock templates produce and Word opens normally; recorded as a known baseline, not a pass.")
        else:
            print("validate.py FAILED in: " + ", ".join(sorted(bad)) + "\n" + outp.strip()[:700])
    elif not a.no_validate:
        print("validate.py (docx skill) not found: OOXML schema validation was NOT run.")
    if missing:
        print("UNRESOLVED CITATIONS: " + ", ".join(sorted(set(missing))))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
