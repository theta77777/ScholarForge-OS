---
name: review-manuscript-docx
description: >-
  Drafts the scientific review manuscript from an evidence base and compiles it into an editable Microsoft Word .docx
  and Typst PDF with academic heading styles, formatted in-text citations and reference list, native tables, embedded
  high-resolution figures (300 DPI vector SVG/PNG), Word SEQ-field captions, page numbers, and optional line numbers.
  Use when the user wants a review paper written, a draft turned into Word or PDF, publication figures/tables generated,
  or a rebuild after edits.
---

# Review Manuscript Drafting & Word/PDF Typesetting

Constructs camera-ready scholarly manuscripts from the evidence matrix, claims ledger, and synthesis outline.

## Drafting Guidelines

- **Lead with an Argument, Not a Study List**: Avoid sequential paper summaries ("Author A found X. Author B found Y."). Structure by biological mechanisms, methodological contrasts, clinical controversies, or emerging paradigms.
- **Evidence-Linked Claims**: Size every claim to its evidentiary basis (`support_level`, study design, sample size). Use bracketed citation anchors: `[@AuthorYear]` or `[@AuthorYear, p. 14]`.
- **Reproducible Scientific Figures**:
  - Render plots using Python `matplotlib`/`seaborn` at 300 DPI PNG and vector SVG.
  - Store plotting scripts in `04_analysis/code/` and outputs in `05_figures_tables/figures/`.
  - Every visual must have an informative caption beginning with `Figure N.` or `Table N.` and a corresponding in-text callout.

## Document Compilation

Compile the Markdown draft into a fully styled Word document and Typst PDF:
```powershell
# 1. Update references and cited keys
python ../review-literature-catalog/scripts/build_catalog.py --in 01_search/catalog/literature_catalog.csv --out-dir 01_search/catalog --cited-from 06_manuscript/manuscript.md --csl-out 06_manuscript/references.json

# 2. Build camera-ready Word document
python scripts/build_docx.py --md 06_manuscript/manuscript.md --bib 06_manuscript/references.json --out 08_final/review_manuscript.docx --title "Review Title" --running-head "Short Title" --page a4 --spacing 1.15
```

## References & Scripts

- [Academic Writing, Citations & Figure Design](./references/writing-citations-figures.md)
- [Word Document Builder Script](./scripts/build_docx.py)
