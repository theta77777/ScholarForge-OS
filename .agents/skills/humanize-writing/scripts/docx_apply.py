#!/usr/bin/env python3
"""Replace the text of selected paragraphs in an UNPACKED .docx, keeping superscript runs.

  List paragraphs:   docx_apply.py list  unpacked_dir [--tables]
  Apply rewrites:    docx_apply.py apply unpacked_dir rewrites.json [--tables] [--force]

rewrites.json = {"<paragraph index>": "new text with {1} {2} ... marking where the
original superscript runs (citation numbers) go, in their original order"}.

Safety rules built in:
- Paragraphs inside tables are skipped unless --tables.
- A paragraph whose non-superscript runs use different formatting (bold lead-in, italics)
  is skipped with a WARNING unless --force, because all new text takes the first run's format.
- Superscript marker count must match the paragraph's superscript runs exactly.
- Digits in the new text must match the old text (modulo citation numbers) or a WARNING prints.
Unpack first: python /mnt/skills/public/docx/scripts/office/unpack.py in.docx dir/
Repack and validate with the docx skill's pack/validate scripts afterwards.
"""
import json, re, sys, copy
from collections import Counter
from lxml import etree
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ns = {"w": W}
q = lambda t: "{%s}%s" % (W, t)
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

def load(d):
    tree = etree.parse(f"{d}/word/document.xml")
    return tree, tree.getroot().find("w:body", ns).findall(".//w:p", ns)

def in_table(p): return any(a.tag == q("tbl") for a in p.iterancestors())
def is_sup(r): return r.find("w:rPr/w:vertAlign", ns) is not None
def ptext(p): return "".join(x.text or "" for x in p.iter(q("t")))
def rpr_key(r):
    e = r.find("w:rPr", ns)
    return etree.tostring(e) if e is not None else b""

def cmd_list(d, tables):
    _, paras = load(d)
    for i, p in enumerate(paras):
        if in_table(p) and not tables: continue
        runs = p.findall("w:r", ns)
        sups = sum(is_sup(r) for r in runs)
        fm = len({rpr_key(r) for r in runs if not is_sup(r)})
        st = p.find("w:pPr/w:pStyle", ns)
        tag = f"style={st.get(q('val')) if st is not None else '-'}"
        print(f"{i}\t{tag}\truns={len(runs)} sup={sups} fmt={fm}\t{ptext(p)[:70]!r}")

def cmd_apply(d, rj, tables, force):
    tree, paras = load(d)
    rewrites = json.load(open(rj, encoding="utf-8"))
    done = skipped = 0
    for key, new in rewrites.items():
        p = paras[int(key)]
        if in_table(p) and not tables:
            print(f"SKIP {key}: inside a table (use --tables)"); skipped += 1; continue
        runs = p.findall("w:r", ns)
        sups = [r for r in runs if is_sup(r)]
        texts = [r for r in runs if not is_sup(r)]
        if not texts: print(f"SKIP {key}: no text runs"); skipped += 1; continue
        if len({rpr_key(r) for r in texts}) > 1 and not force:
            print(f"WARN {key}: mixed formatting in text runs; skipped (use --force)"); skipped += 1; continue
        parts = re.split(r"\{(\d+)\}", new)
        marks = [int(x) for x in parts[1::2]]
        if marks != list(range(1, len(sups) + 1)):
            print(f"SKIP {key}: expected markers {{1}}..{{{len(sups)}}}, got {marks}"); skipped += 1; continue
        old = ptext(p)
        n = lambda s: Counter(re.findall(r"\d+(?:[.,/]\d+)*%?", s))
        if (n(old) - n(re.sub(r"\{\d+\}", "", new))) :
            print(f"WARN {key}: numbers dropped from text: {dict(n(old) - n(new))}")
        rpr = texts[0].find("w:rPr", ns)
        for r in runs: p.remove(r)
        def mk(s):
            r = etree.SubElement(p, q("r"))
            if rpr is not None: r.append(copy.deepcopy(rpr))
            t = etree.SubElement(r, q("t")); t.text = s; t.set(XML_SPACE, "preserve")
        for k, seg in enumerate(parts[0::2]):
            if seg: mk(seg)
            if k < len(sups): p.append(sups[k])
        done += 1
    tree.write(f"{d}/word/document.xml", xml_declaration=True, encoding="UTF-8", standalone=True)
    print(f"applied {done}, skipped {skipped}")

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "list": cmd_list(a[1], "--tables" in a)
    elif len(a) >= 3 and a[0] == "apply": cmd_apply(a[1], a[2], "--tables" in a, "--force" in a)
    else: print(__doc__); sys.exit(2)
