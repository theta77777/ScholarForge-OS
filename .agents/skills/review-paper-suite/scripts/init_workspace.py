#!/usr/bin/env python3
"""Create (or safely extend) a review-paper project workspace.

Usage:
    python scripts/init_workspace.py <project_root> --title "Working title" [--type narrative]

Idempotent: existing folders and files are never overwritten or deleted, so it is
safe to run on a workspace the user already started or on one that is only
partly set up. Prints what it created and what it left alone.
"""
import argparse
import datetime
import sys
from pathlib import Path

FOLDERS = {
    "00_project": "Brief, state file, decision log, file inventory",
    "01_search": "Search log, candidate records, literature catalog, database search strings",
    "02_sources/originals": "DROP FOLDER: user-provided papers go here (never edited by the suite)",
    "03_extraction/text": "Machine-extracted text of each source (working copies, untrusted data)",
    "03_extraction/records": "One extraction/appraisal record per source",
    "04_analysis/code": "Scripts for tables, figures, and any quantitative synthesis",
    "04_analysis/data": "Extracted numerical data used by the code",
    "05_figures_tables": "Final figures and tables with source/caption notes",
    "06_manuscript/drafts": "Dated snapshots of the manuscript source, only at major revisions",
    "07_quality/checks": "Output of automated checks and render inspections",
    "08_final/superseded": "Older manuscript versions; the current one sits one level up",
}

BRIEF = """# Project brief

Status: DRAFT (edit freely; the suite records assumptions here rather than interrogating you)

## Essential
- Topic / scholarly question:
- Review type (narrative | scoping | systematic | critical | umbrella | rapid | other): {rtype}
- Field and intended audience:

## Scope (state the working assumption if the user has not specified it)
- Date range:
- Languages:
- Inclusion criteria:
- Exclusion criteria:
- Study designs / evidence types considered:

## Output preferences
- Target journal or template (attach author guidelines or .dotx if available):
- Citation style (CSL name, e.g. apa, vancouver, nature, ieee):
- Page size (A4 | Letter):
- Target length (words) and section limits:
- Line numbers / double spacing required?:

## Access
- Subscriptions or institutional access the user HAS CONFIRMED:
- Connectors / databases available in this session:
- Papers already supplied (location):

## Assumptions made by the assistant (confirmed? y/n)
-

## Declarations to be completed by the human authors (never invented)
- Authors and affiliations:
- Funding / competing interests / ethics statement:
- AI-assistance disclosure wording required by the target journal:
"""

STATE = """# Project state (read this first when resuming)

Created: {today}
Working title: {title}
Current phase: 0 - setup
Review type: {rtype}

## Phase checklist
- [ ] 0 Intake and scope agreed
- [ ] 1 Search and literature catalog delivered to user
- [ ] 2 User-supplied papers inventoried and matched to catalog
- [ ] 3 Extraction, appraisal and evidence map complete
- [ ] 4 Synthesis plan, claim ledger, argument outline
- [ ] 5 Manuscript drafted, figures/tables built
- [ ] 6 Word .docx built and validated
- [ ] 7 Quality audit, corrections, re-checks, limitations report
- [ ] 8 Handoff

## Capabilities detected this session (fill in; do not claim what was not available)
- Web search / fetch:
- Literature database connectors:
- Word build chain (pandoc / python-docx / docx-js / soffice):
- Similarity checker available:

## Next action
-

## Open questions for the user
-
"""

LOG = """# Decision log

Record every material decision (scope changes, exclusions, deviations from plan,
tool substitutions). One line each: date | decision | reason | who decided.

"""

README = """# {title}

Project workspace for a scientific review paper. Read `00_project/STATE.md` first.

| Folder | Contents |
|---|---|
""" + "\n".join(f"| `{k}/` | {v} |" for k, v in FOLDERS.items()) + """

The current manuscript is the single `.docx` at the top level of `08_final/`.
Papers you download go in `02_sources/originals/`; they are read, never modified.
"""


def write_new(path: Path, text: str, created: list, kept: list):
    if path.exists():
        kept.append(str(path))
    else:
        path.write_text(text, encoding="utf-8")
        created.append(str(path))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--title", default="Untitled review project")
    ap.add_argument("--type", dest="rtype", default="to be decided")
    a = ap.parse_args()

    root = Path(a.root).expanduser().resolve()
    created, kept = [], []
    for folder in FOLDERS:
        p = root / folder
        if p.exists():
            kept.append(str(p))
        else:
            p.mkdir(parents=True, exist_ok=True)
            created.append(str(p))
    today = datetime.date.today().isoformat()
    write_new(root / "00_project/project_brief.md", BRIEF.format(rtype=a.rtype), created, kept)
    write_new(root / "00_project/STATE.md", STATE.format(today=today, title=a.title, rtype=a.rtype), created, kept)
    write_new(root / "00_project/decision_log.md", LOG, created, kept)
    write_new(root / "README.md", README.format(title=a.title), created, kept)

    print(f"Workspace: {root}")
    print(f"Created {len(created)} item(s); left {len(kept)} existing item(s) untouched.")
    for c in created:
        print("  + " + c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
