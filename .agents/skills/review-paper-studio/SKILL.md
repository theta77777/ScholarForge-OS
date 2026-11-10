---
name: review-paper-studio
description: >-
  Autonomous all-in-one scientific review paper engine. Produces complete, publication-ready scholarly review papers across
  scientific domains with verified citations, 300 DPI scientific diagrams, camera-ready Word .docx and PDF manuscripts,
  and separate supporting research records in a single cohesive workflow. Use when the user requests end-to-end review paper
  generation from a title or research question in one prompt.
---

# Review Paper Studio (All-in-One Engine)

Produces a publication-grade review paper supported by verified evidence, reproducible figures, and structured records.
A title and field are sufficient to begin. The studio handles scope intake, journal candidate matching, systematic literature search,
PICO data extraction, evidence synthesis, 300 DPI figure generation, and camera-ready document typesetting.

## Default Production Profile

Configured via [assets/defaults.json](./assets/defaults.json):
- **Word Target**: ~6,500 main-prose words (typical range 6,400–6,800; ceiling 11,000 words including references).
- **Citations**: 90–100 relevant, verified scholarly references.
- **Typography & Layout**: Times New Roman (Title 18 pt, Headings 14 pt, Body 12 pt), 1.15 line spacing, A4 page size.
- **Journal Target**: Profiles suitable journals with verified JIF, checking word limits, unsolicited review eligibility, and fee policies.
- **Deliverables**: Main camera-ready Word `.docx` and Typst `.pdf`, separate supporting evidence matrix, and reproducible figure code.

## Autonomous Workflow Stages

1. **Intake & Journal Selection**: Initialize project records (`python scripts/init_review.py --out ./workspace/<slug> --title "..." --field "..."`). Screen 5 candidate journals.
2. **Systematic Retrieval**: Query academic databases (PubMed, Europe PMC, OpenAlex, Crossref), record search strings, and verify DOIs.
3. **Data Extraction & Claims Ledger**: Extract findings with exact source locators (Section, Page, Table).
4. **Figure Studio**: Render publication figures using Python Matplotlib/Seaborn at 300 DPI following [assets/figure_style.json](./assets/figure_style.json).
5. **Typesetting & Build**: Compile camera-ready document with [scripts/build_document.py](./scripts/build_document.py).
6. **Pre-Submission Audit**: Run automated checks with [scripts/check_manuscript.py](./scripts/check_manuscript.py) and [scripts/audit_pdf.py](./scripts/audit_pdf.py).

## References & Assets

- [Journal Selection & Length Rules](./references/journals-and-length.md)
- [Research Methods & Synthesis Designs](./references/research-methods.md)
- [Evidence Records & Machine-Readable Formats](./references/record-formats.md)
- [Scientific Writing & Figure Design](./references/writing-and-figures.md)
- [Production & Pre-Submission Audit](./references/production-and-audit.md)
- [Platform Setup & Prompts](./references/platforms-and-use.md)
- [Default Configurations](./assets/defaults.json)
- [Scientific Figure Styling Specification](./assets/figure_style.json)
- [Review Initializer Script](./scripts/init_review.py)
- [Document Builder Script](./scripts/build_document.py)
- [Manuscript Checker Script](./scripts/check_manuscript.py)
- [PDF Layout Auditor Script](./scripts/audit_pdf.py)
