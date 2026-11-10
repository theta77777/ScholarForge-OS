#!/usr/bin/env python3
"""Structural and hygiene checks for the Word manuscript.

Usage:  python scripts/check_docx.py 08_final/<manuscript>.docx [--out 07_quality/checks/docx_check.json] [--max-words N]

What it inspects (by reading the .docx itself): heading hierarchy, fake headings, placeholder and unresolved-citation
text, tables (header row, empties, captions), figures (alt text, captions), caption numbering and in-text mentions,
reference section, quotation-mark and spacing hygiene, fonts, tracked changes/comments left in, document properties,
declarations headings. It does NOT judge scientific content, and it does not render pages: pair it with a rendered
visual inspection (see the audit skill) for layout defects. Exit code 1 when any ERROR is found.
"""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

PLACEHOLDERS = re.compile(r"\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b|lorem ipsum|\[citation needed\]|\[ref\]|\[\?+\]|\?\?\?|"
                          r"\{\{|\bINSERT\b|\[REFERENCE\]|\(Author,? (Year|\d{4})\)|<[A-Z ]{4,}>", re.I)
UNRESOLVED = re.compile(r"\[?@[A-Za-z][A-Za-z0-9_:-]*\d{4}[A-Za-z0-9_]*\]?")
CAPTION_STYLES = ("caption", "table caption", "image caption")


def ptext(p):
    """Paragraph text including text inside simple fields (SEQ/PAGE results), which python-docx's .text omits."""
    from docx.oxml.ns import qn
    return "".join(t.text or "" for t in p._p.iter(qn("w:t")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--out")
    ap.add_argument("--max-words", type=int)
    a = ap.parse_args()
    try:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        from docx.oxml.ns import qn
    except ImportError:
        sys.exit("python-docx not installed: structural .docx checks were NOT run (say so in the quality report).")

    F = []
    add = lambda sev, area, msg: F.append({"severity": sev, "area": area, "message": msg})
    try:
        d = docx.Document(a.docx)
    except Exception as e:
        print(f"[ERROR] file cannot be opened as a Word document: {e}")
        return 1
    body = d.element.body
    blocks = []
    for ch in body.iterchildren():
        if ch.tag == qn("w:p"):
            blocks.append(("p", Paragraph(ch, d)))
        elif ch.tag == qn("w:tbl"):
            blocks.append(("t", Table(ch, d)))
    paras = [b for k, b in blocks if k == "p"]
    sname = lambda p: (p.style.name if p.style is not None else "").lower()
    words = sum(len(ptext(p).split()) for p in paras)

    # headings
    levels = []
    for p in paras:
        m = re.match(r"heading (\d)", sname(p))
        if m and ptext(p).strip():
            levels.append((int(m.group(1)), ptext(p).strip()))
    if not levels:
        add("ERROR", "structure", "no Word heading styles found: navigation pane, TOC and journal conversion will not work")
    prev = 0
    for lv, tx in levels:
        if lv > prev + 1 and prev:
            add("WARN", "structure", f"heading level jumps {prev}->{lv} at {tx[:50]!r}")
        prev = lv
    for p in paras:
        t = ptext(p).strip()
        if t and len(t) < 90 and not t.endswith((".", ":", ";", ",")) and not sname(p).startswith(("heading", "title", "caption", "table caption", "image caption", "bibliography")):
            runs = [r for r in p.runs if r.text.strip()]
            if runs and all(r.bold for r in runs) and len(t.split()) <= 12:
                add("WARN", "structure", f"bold-only short paragraph looks like a fake heading: {t[:60]!r} (use a Heading style)")
    if not any(sname(p) == "title" for p in paras):
        add("WARN", "structure", "no Title-style paragraph")
    texts = " ".join(ptext(p) for p in paras)
    for hd in (t for _, t in levels):
        pass
    heads = " | ".join(t.lower() for _, t in levels)
    if not re.search(r"reference|bibliograph", heads):
        add("ERROR", "references", "no References/Bibliography heading")
    nbib = sum(1 for p in paras if sname(p) == "bibliography")
    if nbib == 0:
        add("WARN", "references", "no paragraphs in 'Bibliography' style: reference list may be missing or unstyled")
    if not re.search(r"declaration|funding|conflict|competing|acknowledg|author contribution|ai[- ]assist|use of ai|data availability", heads):
        add("WARN", "declarations", "no declarations headings (funding, competing interests, AI-assistance disclosure, data availability): human authors must supply these")

    # placeholders and unresolved citations
    for p in paras:
        for m in PLACEHOLDERS.finditer(ptext(p)):
            add("ERROR", "placeholder", f"{m.group(0)!r} in: {ptext(p)[max(0, m.start() - 30):m.end() + 30]!r}")
        for m in UNRESOLVED.finditer(ptext(p)):
            add("ERROR", "citation", f"unresolved citation-like token {m.group(0)!r}")

    # tables
    tabs = [b for k, b in blocks if k == "t"]
    for i, (k, b) in enumerate(blocks):
        if k != "t":
            continue
        tn = tabs.index(b) + 1
        trs = b._tbl.findall(".//" + qn("w:tr"))
        hdr = trs[0].find(qn("w:trPr") + "/" + qn("w:tblHeader")) if trs else None
        if hdr is None:
            add("WARN", "tables", f"table {tn}: first row is not marked as a repeating header row")
        empties = sum(1 for r in b.rows for c in r.cells if not c.text.strip())
        total = sum(len(r.cells) for r in b.rows)
        if total and empties / total > 0.25:
            add("WARN", "tables", f"table {tn}: {empties}/{total} empty cells (merged cells or missing data?)")
        before = blocks[i - 1][1] if i and blocks[i - 1][0] == "p" else None
        if not (before is not None and (sname(before) in CAPTION_STYLES or re.match(r"\s*table\s+\d+", ptext(before), re.I))):
            add("ERROR", "tables", f"table {tn}: no caption paragraph directly above it")
        if len(b.rows) > 40:
            add("INFO", "tables", f"table {tn}: {len(b.rows)} rows; consider moving to a supplement")

    # figures
    nfig_img = 0
    for i, (k, b) in enumerate(blocks):
        if k == "p" and b._p.findall(".//" + qn("w:drawing")):
            nfig_img += 1
            for dp in b._p.iter("{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr"):
                if not (dp.get("descr") or "").strip():
                    add("ERROR", "figures", f"image {nfig_img}: no alt text")
            after = blocks[i + 1][1] if i + 1 < len(blocks) and blocks[i + 1][0] == "p" else None
            if not (after is not None and (sname(after) in CAPTION_STYLES or re.match(r"\s*fig", ptext(after), re.I))):
                add("ERROR", "figures", f"image {nfig_img}: no caption paragraph directly below it")

    # caption numbering and in-text mentions
    caps = {"table": [], "figure": []}
    for p in paras:
        m = re.match(r"\s*(table|figure|fig\.)\s+(\d+)", ptext(p), re.I)
        if m and (sname(p) in CAPTION_STYLES):
            caps["table" if m.group(1).lower() == "table" else "figure"].append(int(m.group(2)))
    for kind, nums in caps.items():
        if nums != list(range(1, len(nums) + 1)):
            add("ERROR", "captions", f"{kind} caption numbers not 1..n in order: {nums}")
    if len(caps["table"]) != len(tabs):
        add("ERROR", "captions", f"{len(tabs)} table(s) but {len(caps['table'])} table caption(s)")
    if len(caps["figure"]) != nfig_img:
        add("ERROR", "captions", f"{nfig_img} image(s) but {len(caps['figure'])} figure caption(s)")
    body_text = " ".join(ptext(p) for p in paras if sname(p) not in CAPTION_STYLES)
    for kind, label in (("table", "Table"), ("figure", "Figure|Fig\\.")):
        mentioned = {int(n) for n in re.findall(rf"(?:{label})\s+(\d+)", body_text)}
        for n in sorted(mentioned - set(caps[kind])):
            add("ERROR", "captions", f"text mentions {kind} {n} but no such {kind} exists")
        for n in sorted(set(caps[kind]) - mentioned):
            add("WARN", "captions", f"{kind} {n} is never mentioned in the text")

    # typography
    straight = texts.count('"') + len(re.findall(r"(?<=\w)'(?=\w)", texts))
    curly = sum(texts.count(c) for c in "\u201c\u201d\u2019")
    if straight > 5 and curly > 5:
        add("WARN", "typography", f"mixed straight ({straight}) and curly ({curly}) quotes/apostrophes")
    for pat, msg in ((r"  +", "double spaces"), (r"\s+[,.;:](?!\d)", "space before punctuation"), (r"\b(\w+)\s+\1\b", "repeated word")):
        hits = [m.group(0) for p in paras if not p._p.findall(".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath") for m in re.finditer(pat, ptext(p)) if not (msg == "repeated word" and m.group(1).lower() in ("had", "that"))]
        if hits:
            add("WARN", "typography", f"{len(hits)} instance(s) of {msg}, e.g. {hits[0]!r}")
    blank_runs = sum(1 for i in range(1, len(paras)) if not paras[i].text.strip() and not paras[i - 1].text.strip()
                     and not paras[i]._p.findall(".//" + qn("w:drawing")))
    if blank_runs:
        add("WARN", "layout", f"{blank_runs} consecutive empty paragraph(s): use paragraph spacing or page breaks instead")

    # fonts, revisions, comments, properties
    fonts = Counter(r.font.name for p in paras for r in p.runs if r.font.name)
    if len(fonts) > 3:
        add("WARN", "styles", f"{len(fonts)} different explicit run fonts {dict(fonts)}; formatting should come from styles")
    xml = body.xml
    ins, dele = xml.count("<w:ins "), xml.count("<w:del ")
    if ins or dele:
        add("WARN", "revisions", f"{ins} tracked insertion(s) and {dele} deletion(s) remain: accept or reject before circulation")
    import zipfile
    names = zipfile.ZipFile(a.docx).namelist()
    if "word/comments.xml" in names and zipfile.ZipFile(a.docx).read("word/comments.xml").count(b"<w:comment ") > 0:
        add("WARN", "revisions", "comments present in the file: confirm they are intended")
    cp = d.core_properties
    if not cp.title:
        add("WARN", "properties", "document title property is empty")
    if cp.author:
        add("INFO", "properties", f"author property is {cp.author!r}: confirm it is the human author, not a tool name")
    if a.max_words and words > a.max_words:
        add("WARN", "length", f"{words} words exceeds the stated limit of {a.max_words} (check what the limit includes)")

    stats = {"words_in_body_paragraphs": words, "headings": len(levels), "tables": len(tabs), "images": nfig_img,
             "bibliography_paragraphs": nbib, "equations_omml": xml.count("<m:oMath>"), "seq_fields": xml.count("SEQ "),
             "footnotes_part": "word/footnotes.xml" in names}
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for f in sorted(F, key=lambda x: order[x["severity"]]):
        print(f"[{f['severity']}] {f['area']:12s} {f['message']}")
    err = sum(1 for f in F if f["severity"] == "ERROR")
    print(f"\n{stats}\n{err} error(s), {sum(1 for f in F if f['severity'] == 'WARN')} warning(s).")
    print("Not checked here: page layout/rendering, scientific content, whether references are real.")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"stats": stats, "findings": F}, indent=2), encoding="utf-8")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
