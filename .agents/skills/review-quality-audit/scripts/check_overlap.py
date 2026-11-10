#!/usr/bin/env python3
"""Find long verbatim word-runs shared between the manuscript and the extracted source texts in the workspace.

Usage:
  python scripts/check_overlap.py --manuscript 06_manuscript/manuscript.md --texts 03_extraction/text \
      [--n 8] [--out 07_quality/checks/overlap_check.csv]

This is a LOCAL hygiene check, not a plagiarism detector. It only compares against the source files the user supplied
(it cannot see the wider literature, preprints, or the web) and it catches only exact word sequences, not close
paraphrase or structural copying. A clean result does NOT prove originality; a flagged run is a prompt to rewrite in
fresh language or, if quoting is warranted, to use a short quotation with attribution. The manuscript's own reference
list is excluded. Accepts .md/.txt or .docx (converted with pandoc) manuscripts.
"""
import argparse, csv, re, shutil, subprocess, sys
from pathlib import Path

TOK = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")


def tokens(text):
    return [(m.group(0).lower(), m.start(), m.end()) for m in TOK.finditer(text)]


def load_manuscript(p):
    p = Path(p)
    if p.suffix.lower() == ".docx":
        if not shutil.which("pandoc"):
            sys.exit("pandoc is needed to read .docx; pass the Markdown source instead.")
        t = subprocess.run(["pandoc", "-t", "plain", "--wrap=none", str(p)], capture_output=True, text=True).stdout
    else:
        t = p.read_text(encoding="utf-8")
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"^---\n.*?\n---\n", " ", t, flags=re.S)
    m = re.search(r"^\s{0,3}(#+\s*)?(references|bibliography)\s*$", t, re.I | re.M)
    return t[: m.start()] if m else t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manuscript", required=True)
    ap.add_argument("--texts", required=True, help="folder of extracted source .txt files")
    ap.add_argument("--n", type=int, default=8, help="shortest shared run, in words, to report (default 8)")
    ap.add_argument("--out")
    a = ap.parse_args()

    ms = load_manuscript(a.manuscript)
    mt = tokens(ms)
    if len(mt) < a.n:
        sys.exit("manuscript too short to check.")
    index = {}
    files = sorted(Path(a.texts).glob("*.txt"))
    if not files:
        sys.exit(f"no .txt source files in {a.texts}: overlap check NOT run (extract text first).")
    for f in files:
        st = [w for w, _, _ in tokens(f.read_text(encoding="utf-8", errors="replace"))]
        for i in range(len(st) - a.n + 1):
            index.setdefault(tuple(st[i:i + a.n]), f.stem)
    hits = []
    i = 0
    while i <= len(mt) - a.n:
        src = index.get(tuple(w for w, _, _ in mt[i:i + a.n]))
        if not src:
            i += 1
            continue
        j = i + a.n
        while j < len(mt) and index.get(tuple(w for w, _, _ in mt[j - a.n + 1:j + 1])) == src:
            j += 1
        s, e = mt[i][1], mt[j - 1][2]
        before = ms[max(0, ms.rfind("\n", 0, s)):s]
        inq = (before.count('"') + before.count("\u201c") + before.count("\u201d")) % 2 == 1 or \
              ms[max(0, s - 2):s].strip() in ('"', "\u201c")
        hits.append({"source": src, "words": j - i, "in_quotes": "yes" if inq else "no",
                     "manuscript_excerpt": re.sub(r"\s+", " ", ms[s:e])[:220]})
        i = j
    hits.sort(key=lambda h: -h["words"])
    for h in hits:
        print(f"{h['words']:>3} words | source {h['source']:<14} | quoted: {h['in_quotes']:<3} | {h['manuscript_excerpt']}")
    unq = [h for h in hits if h["in_quotes"] == "no"]
    print(f"\n{len(hits)} shared run(s) of >= {a.n} words against {len(files)} source text(s); {len(unq)} outside quotation marks.")
    print("Interpretation: unquoted runs should be rewritten in original wording. Quoted runs need exact attribution and "
          "should be short. A zero count does not establish originality or pass any external similarity screen.")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["source", "words", "in_quotes", "manuscript_excerpt"])
            w.writeheader()
            w.writerows(hits)
    return 1 if unq else 0


if __name__ == "__main__":
    sys.exit(main())
