# Workspace layout and file contracts

All five skills read and write this layout. `scripts/init_workspace.py <root> --title ... --type ...` creates it
without overwriting anything. Paths are relative to the project root. If a user already has their own structure,
keep it, map it in `00_project/STATE.md`, and never move their files.

## Contents

- Folder map
- Naming and versioning rules
- File schemas (CSV columns)
- Evidence access levels
- Who writes what

## Folder map

| Path | Purpose | Written by |
|---|---|---|
| `README.md` | Folder guide and current-manuscript pointer | orchestrator |
| `00_project/project_brief.md` | Question, scope, preferences, assumptions | orchestrator |
| `00_project/STATE.md` | Phase checklist, capabilities, next action (read first on resume) | all |
| `00_project/decision_log.md` | Material decisions with reasons | all |
| `01_search/search_log.csv`, `candidates.csv` | Every search run; raw candidate records | catalog |
| `01_search/catalog/` | `literature_catalog.xlsx/.csv`, `catalog_report.md` | catalog |
| `01_search/database_search_strings.md` | Strings for databases the assistant could not reach | catalog |
| `02_sources/originals/` | User's papers; never edited | user |
| `02_sources/source_inventory.csv` | One row per file: hash, text status, catalog match | evidence |
| `03_extraction/text/` | Extracted text (untrusted data) | evidence |
| `03_extraction/records/` | One extraction and appraisal record per source | evidence |
| `03_extraction/source_register.csv` | Per-source access level and status | evidence |
| `03_extraction/evidence_matrix.csv` | Cross-study comparison grid | evidence |
| `03_extraction/claims.csv` | Claim ledger | evidence, manuscript |
| `04_analysis/code`, `data` | Scripts and extracted numerical data | manuscript |
| `05_figures_tables/` | Final figures, tables, source notes | manuscript |
| `06_manuscript/` | `manuscript.md`, `references.json`, `citation_style.csl`, `reference.docx`, `drafts/` | manuscript |
| `07_quality/` | `quality_report.md`, `issues_log.csv`, `checks/` | audit |
| `08_final/` | The one current `.docx`; `superseded/` for older versions | manuscript |

## Naming and versioning

- Catalog IDs `C001...` are permanent and never reused. Citation keys (`smith2021effects`) are permanent once cited.
- Downloaded papers should be named `C012_Smith2021.pdf` (the catalog's `suggested_filename`); matching also works by DOI or title.
- One working manuscript source (`06_manuscript/manuscript.md`). Snapshots go in `drafts/manuscript_YYYYMMDD.md` only at major revisions.
- Exactly one `.docx` at the top of `08_final/`, named `<short_slug>_review_manuscript.docx`. On rebuild, move the previous file to `08_final/superseded/<slug>_review_manuscript_YYYYMMDD-HHMM.docx`. Never use "final", "final2" or "v-final".
- Temporary renders go to a temp directory and are deleted after inspection; keep only what the quality report cites, under `07_quality/checks/`.

## File schemas

`01_search/search_log.csv`: `date, source_or_database, access_used, query, filters, results_reviewed, candidates_added, notes`
(`access_used`: open web, publisher site, connector name, user-supplied export, or none-reachable).

`01_search/catalog/literature_catalog.csv`: columns defined in `review-literature-catalog/scripts/build_catalog.py`
(catalog_id, citation_key, title, authors as "Family, Given; Family, Given", year, item_type, source, doi, access_status,
fulltext_link, landing_page_link, record_verification, relevance_tier, use_status, qa_flags, ...).

`03_extraction/source_register.csv`: `catalog_id, citation_key, evidence_access_level, extraction_status, record_path, appraisal_tool, appraisal_summary, notes`

`03_extraction/claims.csv` (claim ledger): `claim_id, claim, claim_type, citation_keys, locator, support_level, caveats, manuscript_section, status`
- `claim_type`: finding | interpretation | method | background | synthesis
- `support_level`: direct | indirect | inferred | abstract_only
- `status`: draft | verified | revised | dropped

`03_extraction/evidence_matrix.csv`: leading columns `catalog_id, citation_key, design, population_or_system, n_or_scale, exposure_or_intervention_or_method, outcome_or_measure, key_result, direction, limitations, appraisal_rating`, then any topic-specific columns.

`07_quality/issues_log.csv`: `issue_id, perspective, severity, location, description, evidence, action, status, recheck_result`
(severity: critical | major | minor | info; status: open | fixed | wont_fix | needs_user).

## Evidence access levels (used in the register)

| Level | Meaning | What may be claimed |
|---|---|---|
| `full_text` | Whole paper read from the user's file or a lawful full-text page | Methods, results, limitations, with locators |
| `abstract_only` | Only title and abstract seen | Abstract-level statements, labelled |
| `secondary_only` | Known only through another paper | "As reported in X"; avoid where possible |
| `not_retrieved` | Metadata only | Existence only; do not characterise findings |

## Who writes what

Only the owning skill rewrites its files. Others append or update specific columns (for example the audit may set
`status` in the ledger and add rows to `issues_log.csv`). Record any structural deviation in `decision_log.md`.
