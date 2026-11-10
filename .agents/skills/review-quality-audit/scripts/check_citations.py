#!/usr/bin/env python3
"""Cross-check manuscript citations, the CSL JSON reference library, the claim ledger and the source register.

Usage:
  python scripts/check_citations.py --manuscript 06_manuscript/manuscript.md --bib 06_manuscript/references.json \
      [--ledger 03_extraction/claims.csv] [--register 03_extraction/source_register.csv] [--out 07_quality/checks/citation_check.json]

Checks (all offline; this script cannot verify that a reference exists in the real world, only that the records are
internally consistent, complete and used as the evidence trail says they should be):
  ERROR  cited key missing from library; library entry without title/year/author; invalid DOI syntax;
         ledger claim whose key is missing; ledger row with bad support_level or missing locator when status=verified
  WARN   library entry never cited; duplicate DOI or title; cited source not read in full text (register);
         cited source without an extraction record; claim marked abstract_only whose source is full_text, etc.
Exit code 1 when any ERROR is found.
"""
import argparse, csv, json, re, sys, datetime
from collections import Counter, defaultdict
from pathlib import Path

KEY = re.compile(r"(?<![\w@])-?@([A-Za-z0-9_](?:[\w:.#$%&\-+?<>~/]*\w)?)")
SUPPORT = {"direct", "indirect", "inferred", "abstract_only"}
CTYPE = {"finding", "interpretation", "method", "background", "synthesis"}
STATUS = {"draft", "verified", "revised", "dropped"}


def strip_code(t):
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    return re.sub(r"`[^`]*`", "", t)


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def rd(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manuscript", required=True)
    ap.add_argument("--bib", required=True)
    ap.add_argument("--ledger")
    ap.add_argument("--register")
    ap.add_argument("--out")
    a = ap.parse_args()
    F = []  # findings: (severity, area, id, message)
    add = lambda sev, area, ident, msg: F.append({"severity": sev, "area": area, "id": ident, "message": msg})

    text = strip_code(Path(a.manuscript).read_text(encoding="utf-8"))
    cited = Counter(k.rstrip(".:;,") for k in KEY.findall(text))
    bib = json.loads(Path(a.bib).read_text(encoding="utf-8"))
    lib = {b["id"]: b for b in bib}
    if len(lib) != len(bib):
        add("ERROR", "library", "-", "duplicate citation ids in references.json")

    for k, n in cited.items():
        if k not in lib:
            add("ERROR", "citation", k, f"cited {n}x in manuscript but absent from reference library")
    for k, b in lib.items():
        if k not in cited:
            add("WARN", "library", k, "in reference library but never cited (remove or cite; check for a lost citation)")
        if not b.get("title"):
            add("ERROR", "library", k, "missing title")
        if not b.get("issued"):
            add("ERROR", "library", k, "missing issued date")
        else:
            try:
                y = int(b["issued"]["date-parts"][0][0])
                if not 1500 <= y <= datetime.date.today().year + 1:
                    add("ERROR", "library", k, f"implausible year {y}")
            except Exception:
                add("ERROR", "library", k, "unreadable issued date")
        if not b.get("author") and not b.get("editor"):
            add("ERROR", "library", k, "missing author/editor")
        if any("et al" in (n.get("family", "") + n.get("literal", "")).lower() for n in b.get("author", [])):
            add("ERROR", "library", k, "'et al' stored as an author name; list authors in full")
        if b.get("type") == "article-journal" and not b.get("container-title"):
            add("WARN", "library", k, "journal article without container-title (journal)")
        if b.get("DOI") and not re.match(r"^10\.\d{4,9}/\S+$", b["DOI"]):
            add("ERROR", "library", k, f"invalid DOI syntax: {b['DOI']}")
        if not b.get("DOI") and not b.get("URL") and not b.get("ISBN"):
            add("WARN", "library", k, "no DOI/URL/ISBN: reader cannot locate the source from the reference")
    by_doi, by_title = defaultdict(list), defaultdict(list)
    for k, b in lib.items():
        if b.get("DOI"):
            by_doi[b["DOI"].lower()].append(k)
        by_title[norm(b.get("title"))].append(k)
    for d, ks in by_doi.items():
        if len(ks) > 1:
            add("WARN", "library", ",".join(ks), f"same DOI {d}: duplicate entries")
    for t, ks in by_title.items():
        if t and len(ks) > 1 and not any(len(by_doi.get(lib[k].get("DOI", "").lower(), [])) > 1 for k in ks):
            add("WARN", "library", ",".join(ks), "identical titles: duplicate or different versions of one work?")

    register = {}
    if a.register and Path(a.register).exists():
        register = {r["citation_key"]: r for r in rd(a.register)}
        for k in cited:
            r = register.get(k)
            if r is None:
                add("WARN", "register", k, "cited but has no row in source_register (no extraction record)")
            elif r.get("evidence_access_level") != "full_text":
                add("WARN", "register", k, f"cited but evidence_access_level={r.get('evidence_access_level')!r}: restrict claims to what that level supports and disclose it")
            elif r.get("extraction_status") not in ("done",):
                add("WARN", "register", k, f"extraction_status={r.get('extraction_status')!r}")
    elif a.register:
        add("WARN", "register", "-", f"register file not found: {a.register}")

    ledger_keys = set()
    if a.ledger and Path(a.ledger).exists():
        rows = rd(a.ledger)
        need = {"claim_id", "claim", "claim_type", "citation_keys", "locator", "support_level", "status"}
        if rows and not need <= set(rows[0]):
            add("ERROR", "ledger", "-", f"missing ledger columns: {sorted(need - set(rows[0]))}")
        else:
            for r in rows:
                cid = r.get("claim_id", "?")
                if r.get("status") == "dropped":
                    continue
                keys = [k.strip().lstrip("@") for k in re.split(r"[;,]", r.get("citation_keys", "")) if k.strip()]
                ledger_keys.update(keys)
                if r.get("claim_type") not in CTYPE:
                    add("ERROR", "ledger", cid, f"claim_type {r.get('claim_type')!r} not in {sorted(CTYPE)}")
                if r.get("status") not in STATUS:
                    add("ERROR", "ledger", cid, f"status {r.get('status')!r} not in {sorted(STATUS)}")
                if r.get("support_level") not in SUPPORT:
                    add("ERROR", "ledger", cid, f"support_level {r.get('support_level')!r} not in {sorted(SUPPORT)}")
                if not keys and r.get("claim_type") not in ("synthesis", "interpretation"):
                    add("ERROR", "ledger", cid, "factual claim with no source key")
                for k in keys:
                    if k not in lib:
                        add("ERROR", "ledger", cid, f"source key {k} not in reference library")
                    elif register and register.get(k, {}).get("evidence_access_level") not in (None, "full_text") and r.get("support_level") != "abstract_only":
                        add("WARN", "ledger", cid, f"{k} was not read in full text but claim support_level is {r.get('support_level')!r}")
                if r.get("status") == "verified" and not r.get("locator"):
                    add("ERROR", "ledger", cid, "status=verified but no locator (page/section/table) recorded")
                if r.get("support_level") == "inferred" and not re.search(r"suggest|may|might|could|consistent|appear|indicat|likely|possibl", r.get("claim", ""), re.I):
                    add("WARN", "ledger", cid, "inferred claim lacks hedged wording; manuscript must not state it as established")
        for k in ledger_keys - set(cited):
            add("WARN", "ledger", k, "ledger source key never cited in the manuscript text")
    elif a.ledger:
        add("WARN", "ledger", "-", f"ledger file not found: {a.ledger}")

    err = sum(1 for f in F if f["severity"] == "ERROR")
    warn = sum(1 for f in F if f["severity"] == "WARN")
    for f in sorted(F, key=lambda x: (x["severity"] != "ERROR", x["area"])):
        print(f"[{f['severity']}] {f['area']:9s} {f['id']:28s} {f['message']}")
    print(f"\n{len(cited)} distinct key(s) cited; {len(lib)} library entr(ies); {err} error(s), {warn} warning(s).")
    print("Not checked here: whether each reference exists and is described correctly in the real world; "
          "whether each claim is faithful to its source. Those need source-level verification (see audit skill).")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"errors": err, "warnings": warn, "findings": F}, indent=2), encoding="utf-8")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
