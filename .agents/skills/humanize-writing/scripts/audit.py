#!/usr/bin/env python3
"""Audit a humanized rewrite against the original.

Usage: audit.py ORIGINAL REVISED [--prose-only]
  --prose-only  ignore the reference list (everything after a line reading "References")
                and any line under 12 words (table cells, headings, captions, citations)
Accepts .txt/.md/.docx (docx is read through pandoc).
Reports: fidelity (numbers, citations, acronyms), shallow-rewrite overlap,
sentence-length burstiness, repeated frames, opener repetition, tell-phrase hits.
Exit code 1 if any hard failure (fidelity) is found.
"""
import re, sys, statistics, subprocess, os
from collections import Counter

TELLS = r"""\bdelve\w*|\btapestry\b|\brealm\b|\bleverag\w+|\bharness\w*|\brobust\b|\bcomprehensive\b|\bpivotal\b|\bseamless\w*|
\bmultifaceted\b|\bintricate\b|\btestament\b|\bunderscor\w+|\bshowcas\w+|\bboast\w*|\bgarner\w*|\bshed(s|ding)? light\b|
\bpaves? the way\b|\bever-evolving\b|\bgame-changer\b|it is (worth|important to) not\w+|plays? an? (key|vital|pivotal|crucial|significant) role|
\ba wide range of\b|\bserves as\b|\bstands as\b|\bin the realm of\b|\bnot just\b.{0,60}\bbut\b|\bmoreover\b|\bfurthermore\b|\badditionally\b|\bnotably\b|
\bin summary\b|\bin conclusion\b|\boverall,|\bin essence\b|\bI hope this helps\b"""
TELL_RE = re.compile(TELLS.replace("\n", ""), re.I)

def load(path):
    if path.lower().endswith(".docx"):
        return subprocess.run(["pandoc", "-t", "plain", "--wrap=none", path],
                              capture_output=True, text=True, check=True).stdout
    return open(path, encoding="utf-8").read()

def prose_only(t):
    out = []
    for line in t.splitlines():
        if re.fullmatch(r"\s*(references|bibliography|works cited)\s*", line, re.I): break
        if len(line.split()) >= 12: out.append(line)
    return "\n".join(out)

def sentences(t):
    t = re.sub(r"\s+", " ", t)
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(\[])", t) if len(s.split()) > 2]

def words(t): return re.findall(r"[A-Za-z0-9'%.-]+", t.lower())

def ngrams(w, n): return Counter(tuple(w[i:i+n]) for i in range(len(w) - n + 1))

def numbers(t):
    t = re.sub(r"[\u00b9\u00b2\u00b3\u2070-\u2079]+", " ", t)  # drop unicode superscripts
    t = re.sub(r"\^\([^)]*\)|\^\w+", " ", t)                   # pandoc ^(1, 2) style
    return Counter(re.findall(r"\d+(?:[.,/]\d+)*%?", t))

def acronyms(t): return Counter(re.findall(r"\b[A-Z][A-Za-z]*[A-Z0-9]+\b", t))

def main():
    if len(sys.argv) < 3: print(__doc__); sys.exit(2)
    a, b = load(sys.argv[1]), load(sys.argv[2])
    if "--prose-only" in sys.argv: a, b = prose_only(a), prose_only(b)
    fail = 0
    print("== FIDELITY ==")
    for name, fa, fb in (("numbers", numbers(a), numbers(b)), ("acronyms/identifiers", acronyms(a), acronyms(b))):
        lost, added = fa - fb, fb - fa
        if lost or added:
            fail += 1
            print(f"  {name}: MISSING {dict(lost)}  ADDED {dict(added)}")
        else:
            print(f"  {name}: identical")
    ca, cb = len(re.findall(r"\[\d+(?:[,\u2013-]\s*\d+)*\]", a)), len(re.findall(r"\[\d+(?:[,\u2013-]\s*\d+)*\]", b))
    if ca != cb: fail += 1; print(f"  bracket citations: {ca} -> {cb}  MISMATCH")

    print("== SHALLOW-REWRITE CHECK ==")
    wa, wb = words(a), words(b)
    ga, gb = ngrams(wa, 5), ngrams(wb, 5)
    shared = sum(min(c, gb[g]) for g, c in ga.items() if g in gb)
    pct = 100 * shared / max(1, sum(gb.values()))
    flag = "  <- too close to the original, rewrite more deeply" if pct > 30 else ""
    print(f"  5-gram overlap with original: {pct:.0f}%{flag}")
    print(f"  length: {len(wa)} -> {len(wb)} words ({100*(len(wb)-len(wa))/max(1,len(wa)):+.0f}%)")

    print("== RHYTHM ==")
    for label, t in (("original", a), ("revised ", b)):
        L = [len(s.split()) for s in sentences(t)]
        if len(L) > 5:
            m, sd = statistics.mean(L), statistics.pstdev(L)
            print(f"  {label}: {len(L)} sentences, mean {m:.1f}, stdev {sd:.1f}, burstiness {sd/m:.2f}")
    Lb = [len(s.split()) for s in sentences(b)]
    if len(Lb) > 5 and statistics.pstdev(Lb) / statistics.mean(Lb) < 0.5:
        print("  note: sentence lengths are still very even; add a few short and a few long ones")

    print("== REPEATED FRAMES (revised) ==")
    starts = Counter(" ".join(s.split()[:2]).lower() for s in sentences(b))
    top = [(k, v) for k, v in starts.most_common(6) if v >= 4]
    print("  frequent sentence openers:", top or "none")
    tri = Counter(t for t, c in ngrams(wb, 3).items() for _ in range(c) if not set(t) & {"the", "of", "and", "a", "to", "in", "is", "for"} == set(t))
    rep = [(" ".join(k), v) for k, v in tri.most_common(40) if v >= 5 and len(set(k)) == 3][:8]
    print("  3-word phrases used 5+ times:", rep or "none")

    print("== TELL PHRASES (revised) ==")
    hits = Counter(m.group(0).lower() for m in TELL_RE.finditer(b))
    ha = Counter(m.group(0).lower() for m in TELL_RE.finditer(a))
    print(f"  original: {sum(ha.values())} hits   revised: {sum(hits.values())} hits  {dict(hits) if hits else ''}")
    print("RESULT:", "FAIL (fidelity)" if fail else "OK")
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main()
