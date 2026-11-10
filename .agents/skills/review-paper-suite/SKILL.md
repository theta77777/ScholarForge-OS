---
name: review-paper-suite
description: >-
  Orchestrates rigorous, PhD-level scientific review papers (narrative, scoping, systematic, critical, umbrella, rapid)
  from a topic and literature to an editable Word .docx and Typst PDF manuscript with a literature catalog, evidence records,
  reference library, and 7-perspective quality audit. Use whenever the user wants to write, plan, continue, upgrade, or
  check a literature review, review article, state-of-the-art survey, or systematic/scoping review.
---

# Review Paper Suite (Orchestrator)

Goal: Deliver the strongest review paper the evidence, tools, and supplied materials can support, packaged as an editable
Word `.docx`, Typst `.pdf`, and Overleaf-ready LaTeX bundle with fully traceable evidence records. Never promise "guaranteed
publication" or "100% human-scored" results; aim for the highest defensible scholarly standard and make all limitations visible.

## Suite Architecture & Stages

The review paper workflow is structured into discrete, cooperating stages that share an on-disk project workspace:

| Skill | Stage | Primary Function |
|---|---|---|
| `review-literature-catalog` | Stage 1 | Systematic search across academic databases, deduplication, and candidate catalog generation |
| `review-evidence-synthesis` | Stages 2-4 | Source inventory (SHA-256), PICO extraction records, Cochrane/ROBINS-I appraisal, claim ledger |
| `review-manuscript-docx` | Stages 5-6 | Synthesis drafting with narrative through-lines, 300 DPI figures, and camera-ready Word/PDF building |
| `review-quality-audit` | Stage 7 | 5-7 perspective adversarial audit arena, automated citation/overlap checks, and quality report |
| `review-paper-suite` (this) | Stages 0, 8 | Intake, scope formulation, project workspace setup, state tracking (`STATE.md`), and final delivery |

## Workspace Directory Layout

Every paper project maintains an isolated, reproducible 9-directory structure:
```text
00_project/       # STATE.md, project_brief.md, decision_log.md
01_search/        # search_log.csv, candidates.csv, catalog/
02_sources/       # source_inventory.csv, originals/ (user/downloaded PDFs)
03_extraction/    # records/ (C001.md...), evidence_matrix.csv, claims.csv, text/
04_analysis/      # data/, code/ (data wrangling and summary scripts)
05_figures_tables/# figures/ (PNG, SVG), tables/
06_manuscript/    # manuscript.md, references.json, citation_style.csl
07_quality/       # issues_log.csv, quality_report.md, checks/
08_final/         # Final camera-ready .docx, .pdf, .zip artifacts
```

## Step 0: Orient and Initialize

1. Check for an existing workspace or `00_project/STATE.md`.
2. If starting fresh, initialize the workspace using:
   ```powershell
   python scripts/init_workspace.py ./workspace/<slug> --title "<Title>" --type narrative
   ```
3. Record initial scope assumptions in `00_project/project_brief.md`: research question, date boundaries, target journal profile.

## References & Helpers

- [Review Types & Criteria](./references/review-types.md)
- [Scholarly Integrity & Tool Ethics](./references/integrity-and-tools.md)
- [Workspace Layout Specification](./references/workspace-layout.md)
- [End-to-End Workflow Runbook](./references/workflow.md)
- [Workspace Initializer Script](./scripts/init_workspace.py)
