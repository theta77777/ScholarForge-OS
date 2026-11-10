#!/usr/bin/env python3
"""Validate, de-duplicate and export a literature catalog.

Usage:
  python scripts/build_catalog.py --in 01_search/candidates.csv --out-dir 01_search/catalog \
      [--search-log 01_search/search_log.csv] [--scope-file scope.md] [--coverage-file coverage.md] \
      [--as-of 2026-10-29] [--csl-out 06_manuscript/references.json --csl-statuses cited,screened_in]

Input: CSV with any subset of the catalog columns (see COLS). Re-running on the
produced literature_catalog.csv is safe: existing catalog_ids and citation_keys
are kept, new rows get new ones. Nothing is looked up online; every value comes
from the input, so the script cannot invent metadata. It only normalises, flags
and formats.

Outputs in --out-dir: literature_catalog.xlsx, literature_catalog.csv, catalog_report.md
"""
import argparse, csv, datetime, difflib, json, re, sys, unicodedata
from collections import Counter
from pathlib import Path

COLS = ["catalog_id", "citation_key", "title", "authors", "year", "item_type", "source", "volume",
        "issue", "pages", "doi", "other_id", "study_type", "relevance_tier", "relevance_note",
        "access_status", "fulltext_link", "fulltext_link_type", "landing_page_link", "doi_url",
        "access_note", "version_type", "retraction_check", "record_verification", "uncertainty_note",
        "found_via", "suggested_filename", "use_status", "exclusion_reason", "qa_flags"]
VOCAB = {
    "access_status": ["open_full_text", "open_version_found", "subscription_confirmed",
                      "subscription_possible", "paywalled", "unknown"],
    "relevance_tier": ["core", "supporting", "background"],
    "record_verification": ["verified", "reported", "unverified"],
    "use_status": ["candidate", "screened_in", "excluded", "cited"],
    "version_type": ["published", "accepted_manuscript", "preprint", "unknown"],
    "retraction_check": ["not_checked", "clear", "flagged"],
}
DEFAULTS = {"use_status": "candidate", "record_verification": "unverified",
            "access_status": "unknown", "version_type": "unknown", "retraction_check": "not_checked"}
OPEN = {"open_full_text", "open_version_found"}
CSL_TYPES = {"article-journal", "book", "chapter", "report", "paper-conference", "article", "thesis", "webpage"}
STOP = {"a", "an", "the", "of", "on", "in", "for", "and", "to", "with", "from", "by", "at", "is", "are"}
FILL = {"open_full_text": "C6EFCE", "open_version_found": "DDEBF7", "subscription_confirmed": "E2EFDA",
        "subscription_possible": "FFF2CC", "paywalled": "F8CBAD", "unknown": "D9D9D9"}


def ascii_fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def norm_doi(d):
    d = (d or "").strip()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I)
    return d.lower().rstrip(".,;")


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", ascii_fold(t).lower()).strip()


def first_family(authors):
    first = (authors or "").split(";")[0].strip()
    if first.startswith("{"):
        first = first.strip("{}")
        return re.sub(r"[^a-z0-9]", "", ascii_fold(first).lower().split()[0]) if first.split() else "anon"
    fam = first.split(",")[0]
    return re.sub(r"[^a-z0-9]", "", ascii_fold(fam).lower()) or "anon"


def make_key(r, used):
    words = [w for w in norm_title(r.get("title", "")).split() if w not in STOP]
    base = f"{first_family(r.get('authors', ''))}{(r.get('year') or 'nd').strip()}{words[0] if words else ''}"
    key, n = base, 0
    while key in used:
        n += 1
        key = base + chr(96 + n) if n < 27 else f"{base}{n}"
    return key


def parse_authors(s):
    out, flags = [], []
    for part in [p.strip() for p in (s or "").split(";") if p.strip()]:
        if part.lower() in ("et al", "et al."):
            flags.append("authors_truncated_et_al")
        elif part.startswith("{") and part.endswith("}"):
            out.append({"literal": part[1:-1]})
        elif "," in part:
            fam, giv = [x.strip() for x in part.split(",", 1)]
            out.append({"family": fam, "given": giv})
        else:
            out.append({"literal": part})
            flags.append("author_not_Family,Given")
    return out, flags


def validate(r, today_year):
    f = []
    for need in ("title", "authors", "year"):
        if not r.get(need):
            f.append(f"missing_{need}")
    f += sorted(set(parse_authors(r.get("authors", ""))[1]))
    if r.get("year") and not (r["year"].isdigit() and 1500 <= int(r["year"]) <= today_year + 1):
        f.append("year_out_of_range")
    if not r.get("doi") and not r.get("other_id"):
        f.append("no_stable_identifier")
    if r.get("doi") and not re.match(r"^10\.\d{4,9}/\S+$", r["doi"]):
        f.append("invalid_doi_format")
    for col, allowed in VOCAB.items():
        if r.get(col) and r[col] not in allowed:
            f.append(f"bad_{col}")
    ft = r.get("fulltext_link", "")
    if ft and not re.match(r"^https?://", ft):
        f.append("fulltext_link_not_http")
    if r.get("access_status") in OPEN:
        if not ft:
            f.append("open_status_without_fulltext_link")
        elif ft in (r.get("landing_page_link"), r.get("doi_url")):
            f.append("fulltext_link_equals_landing_page_unconfirmed")
    if r.get("access_status") == "subscription_confirmed" and not r.get("access_note"):
        f.append("subscription_route_not_described")
    if r.get("version_type") in ("preprint", "accepted_manuscript"):
        f.append("not_version_of_record")
    if r.get("record_verification") != "verified":
        f.append("record_not_verified")
    if r.get("relevance_tier") == "core" and r.get("retraction_check") == "not_checked":
        f.append("core_paper_retraction_status_unchecked")
    return f


def merge(rows):
    """Merge duplicate rows: keep the most verified row, fill blanks from the others."""
    rank = {"verified": 0, "reported": 1, "unverified": 2}
    rows = sorted(rows, key=lambda r: rank.get(r.get("record_verification", "unverified"), 2))
    base = dict(rows[0])
    for other in rows[1:]:
        for k, v in other.items():
            if not base.get(k) and v:
                base[k] = v
    return base


def read_csv(p):
    with open(p, newline="", encoding="utf-8-sig") as fh:
        return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(fh)]


def build(rows, today_year):
    for r in rows:
        r["doi"] = norm_doi(r.get("doi"))
        for k, v in DEFAULTS.items():
            r[k] = r.get(k) or v
    # de-duplicate by DOI, then by normalised title + year
    groups, order = {}, []
    for r in rows:
        k = ("doi", r["doi"]) if r["doi"] else ("title", norm_title(r.get("title")), r.get("year", ""))
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(r)
    merged, dup_notes = [], 0
    for k in order:
        g = groups[k]
        row = merge(g) if len(g) > 1 else g[0]
        row["_dups"] = len(g) - 1
        dup_notes += len(g) - 1
        merged.append(row)
    used_ids = {r["catalog_id"] for r in merged if r.get("catalog_id")}
    used_keys = {r["citation_key"] for r in merged if r.get("citation_key")}
    n = 0
    for r in merged:
        if not r.get("catalog_id"):
            while f"C{n + 1:03d}" in used_ids:
                n += 1
            n += 1
            r["catalog_id"] = f"C{n:03d}"
            used_ids.add(r["catalog_id"])
        if not r.get("citation_key"):
            r["citation_key"] = make_key(r, used_keys)
            used_keys.add(r["citation_key"])
        if r["doi"] and not r.get("doi_url"):
            r["doi_url"] = f"https://doi.org/{r['doi']}"
        if not r.get("suggested_filename"):
            r["suggested_filename"] = f"{r['catalog_id']}_{first_family(r.get('authors', '')).capitalize()}{r.get('year', '')}.pdf"
        flags = validate(r, today_year)
        if r["_dups"]:
            flags.append(f"merged_{r['_dups']}_duplicate_row(s)")
        r["qa_flags"] = "; ".join(flags)
    # near-duplicate titles with different identifiers
    for i, a in enumerate(merged):
        for b in merged[i + 1:]:
            if a["doi"] != b["doi"] and abs(int(a.get("year") or 0) - int(b.get("year") or 0)) <= 1 and a.get("title") and b.get("title"):
                if difflib.SequenceMatcher(None, norm_title(a["title"]), norm_title(b["title"])).ratio() >= 0.92:
                    for x, y in ((a, b), (b, a)):
                        x["qa_flags"] = (x["qa_flags"] + "; " if x["qa_flags"] else "") + f"possible_duplicate_of_{y['catalog_id']}"
    tier = {"core": 0, "supporting": 1, "background": 2}
    merged.sort(key=lambda r: (tier.get(r["relevance_tier"], 3), -int(r.get("year") or 0), r["catalog_id"]))
    return merged


def to_csl(r):
    auth, _ = parse_authors(r.get("authors", ""))
    t = r.get("item_type") or "article-journal"
    item = {"id": r["citation_key"], "type": t if t in CSL_TYPES else "article-journal", "title": r.get("title", "")}
    if auth:
        item["author"] = auth
    if r.get("year", "").isdigit():
        item["issued"] = {"date-parts": [[int(r["year"])]]}
    for src, dst in (("source", "container-title"), ("volume", "volume"), ("issue", "issue"), ("pages", "page"), ("doi", "DOI")):
        if r.get(src):
            item[dst] = r[src]
    if not r.get("doi") and r.get("landing_page_link"):
        item["URL"] = r["landing_page_link"]
    return item


def write_xlsx(rows, path, search_log, scope, coverage, as_of, counts):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws0 = wb.active
    ws0.title = "README"
    lines = [("Literature catalog", True), (f"Catalog date: {as_of}. Records: {len(rows)}.", False), ("", False),
             ("SCOPE", True), (scope or "Scope statement not supplied; see project_brief.md.", False), ("", False),
             ("COVERAGE AND KNOWN GAPS", True), (coverage or "Coverage notes not supplied.", False), ("", False),
             ("IMPORTANT", True),
             ("This is a list of candidate papers found within the stated scope and sources. It is not a claim of completeness.", False),
             ("Access status describes what was observed on the stated date; confirm with your own library or subscription.", False),
             ("fulltext_link is only filled when a route to the full text itself was seen; doi_url and landing_page_link may show only an abstract.", False),
             ("Use only lawful routes (publisher, repository, library, author request). Do not use unauthorised copies.", False), ("", False),
             ("ACCESS STATUS KEY", True)]
    key = {"open_full_text": "Free full text seen at fulltext_link (version in version_type)",
           "open_version_found": "Free preprint/accepted manuscript/repository copy; may differ from published version",
           "subscription_confirmed": "Access via a route the user or a connector confirmed (see access_note)",
           "subscription_possible": "Publisher paywall; may be available via an institution or personal subscription; not verified",
           "paywalled": "No free route found; consider library loan, author request or purchase",
           "unknown": "Access not checked or not determinable"}
    lines += [(f"{k}: {v}", False) for k, v in key.items()]
    for i, (t, b) in enumerate(lines, 1):
        c = ws0.cell(row=i, column=1, value=t)
        c.font = Font(bold=b, size=13 if i == 1 else 11)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws0.column_dimensions["A"].width = 130

    ws = wb.create_sheet("Catalog")
    ws.append(COLS)
    for r in rows:
        ws.append([r.get(c, "") for c in COLS])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="305496")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    widths = {"title": 55, "authors": 35, "source": 28, "relevance_note": 50, "access_note": 40, "uncertainty_note": 40, "qa_flags": 40}
    for i, c in enumerate(COLS, 1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(c, 16)
    for ri, r in enumerate(rows, 2):
        for ci, c in enumerate(COLS, 1):
            cell = ws.cell(row=ri, column=ci)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if c in ("fulltext_link", "landing_page_link", "doi_url") and r.get(c, "").startswith("http"):
                cell.hyperlink = r[c]
                cell.font = Font(color="0563C1", underline="single")
            if c == "access_status":
                cell.fill = PatternFill("solid", fgColor=FILL.get(r.get(c), "FFFFFF"))
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = ws.dimensions
    for col, allowed in VOCAB.items():
        dv = DataValidation(type="list", formula1='"' + ",".join(allowed) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        L = get_column_letter(COLS.index(col) + 1)
        dv.add(f"{L}2:{L}{max(len(rows) + 200, 300)}")

    wl = wb.create_sheet("Search_log")
    if search_log:
        wl.append(list(search_log[0].keys()))
        for row in search_log:
            wl.append(list(row.values()))
        for cell in wl[1]:
            cell.font = Font(bold=True)
    else:
        wl.append(["No search log supplied"])
    wf = wb.create_sheet("QA_flags")
    wf.append(["catalog_id", "title", "qa_flags"])
    for r in rows:
        if r["qa_flags"]:
            wf.append([r["catalog_id"], r.get("title", ""), r["qa_flags"]])
    for cell in wf[1]:
        cell.font = Font(bold=True)
    wf.column_dimensions["B"].width = 70
    wf.column_dimensions["C"].width = 90
    wb.save(path)


def write_report(rows, path, scope, coverage, as_of, search_log):
    n = len(rows)
    def tab(col, vals):
        c = Counter(r.get(col, "") or "(blank)" for r in rows)
        return "\n".join(f"| {v} | {c.get(v, 0)} |" for v in vals + [k for k in c if k not in vals])
    flags = Counter(f.split("_duplicate")[0] for r in rows for f in r["qa_flags"].split("; ") if f)
    md = [f"# Catalog report ({as_of})", "", f"Records: {n}", "", "## Scope", scope or "(not supplied)", "",
          "## Coverage and known gaps", coverage or "(not supplied)", "",
          "## Access status", "| Status | Count |", "|---|---|", tab("access_status", VOCAB["access_status"]), "",
          "## Relevance tier", "| Tier | Count |", "|---|---|", tab("relevance_tier", VOCAB["relevance_tier"]), "",
          "## Record verification", "| Level | Count |", "|---|---|", tab("record_verification", VOCAB["record_verification"]), "",
          "## Most common quality flags", "| Flag | Records |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in flags.most_common(12)] or ["| none | 0 |"]
    md += ["", f"Searches logged: {len(search_log)}", "",
           "This catalog lists candidates found within the stated scope and sources; it is not a claim of completeness."]
    Path(path).write_text("\n".join(md) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--search-log")
    ap.add_argument("--scope-file")
    ap.add_argument("--coverage-file")
    ap.add_argument("--as-of", default=datetime.date.today().isoformat())
    ap.add_argument("--csl-out")
    ap.add_argument("--csl-statuses", default="cited,screened_in")
    ap.add_argument("--cited-from", help="manuscript.md: rows whose citation_key is cited there get use_status=cited")
    a = ap.parse_args()

    rows = read_csv(a.inp)
    if not rows:
        sys.exit("No rows in input; nothing to build.")
    rows = build(rows, datetime.date.today().year)
    if a.cited_from:
        ms = re.sub(r"```.*?```|<!--.*?-->", "", Path(a.cited_from).read_text(encoding="utf-8"), flags=re.S)
        keys = {k.rstrip(".:;,") for k in re.findall(r"(?<![\w@])-?@([A-Za-z0-9_](?:[\w:.#$%&\-+?<>~/]*\w)?)", ms)}
        known = {r["citation_key"] for r in rows}
        for r in rows:
            if r["citation_key"] in keys and r["use_status"] != "excluded":
                r["use_status"] = "cited"
        for k in sorted(keys - known):
            print(f"WARNING: manuscript cites @{k}, which is not in the catalog (add a verified record or remove the citation)")
        a.csl_statuses = "cited"
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    txt = lambda p: Path(p).read_text(encoding="utf-8") if p and Path(p).exists() else ""
    log = read_csv(a.search_log) if a.search_log and Path(a.search_log).exists() else []
    with open(out / "literature_catalog.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    try:
        write_xlsx(rows, out / "literature_catalog.xlsx", log, txt(a.scope_file), txt(a.coverage_file), a.as_of, Counter())
    except ImportError:
        print("openpyxl missing: wrote CSV and report only; the XLSX catalog was NOT produced.")
    write_report(rows, out / "catalog_report.md", txt(a.scope_file), txt(a.coverage_file), a.as_of, log)
    if a.csl_out:
        wanted = set(a.csl_statuses.split(","))
        items = [to_csl(r) for r in rows if r["use_status"] in wanted]
        Path(a.csl_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.csl_out).write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"CSL JSON: {len(items)} item(s) with use_status in {sorted(wanted)} -> {a.csl_out}")
    flagged = sum(1 for r in rows if r["qa_flags"])
    print(f"Catalog: {len(rows)} record(s), {flagged} with quality flags -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
