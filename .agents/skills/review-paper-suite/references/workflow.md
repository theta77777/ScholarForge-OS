# Workflow: phases, exit criteria, perspective passes

## Contents

- Phase details with exit criteria
- The five perspective passes
- Calibrating effort to project size
- Pausing, resuming, and user checkpoints

## Phase details

### 0. Intake and scope
Do: infer topic, field, audience, review type; write the question and sub-questions (`review-types.md` frames); draft
inclusion and exclusion rules, date range, languages, evidence types; note access and tools; run
`python scripts/init_workspace.py <root> --title "..." --type ...`; fill `project_brief.md` with every assumption marked.
Exit: brief written; scope statement of 5-10 lines that the catalog can quote. Do not stall for confirmation unless a
choice is expensive to reverse (for example a clinical-versus-policy framing).

### 1. Search and catalog (`review-literature-catalog`)
Deliver the catalog before drafting anything from abstracts. The user reviews it, downloads papers lawfully and
places them in `02_sources/originals/`. End the turn with: where the catalog is, how many records, the access mix,
search boundaries and known gaps, the naming convention for files, and the exact sentence to ask when ready.
Exit: `01_search/catalog/` populated; `search_log.csv` complete; coverage notes written.

### 2. Handoff and inventory (`review-evidence-synthesis`)
Run `scripts/inventory_sources.py`. Report: files found, matched, unmatched, duplicates, scanned or unreadable files,
conflicts between file and catalog record, core papers still missing. Offer to proceed with what is available and to
catalog gaps. Unmatched but relevant files are added to the catalog as `found_via: user_supplied`.
Exit: `source_inventory.csv` current; each file has a status; user told what is missing.

### 3. Extraction and appraisal
One source at a time, to disk, using the record template. Set `evidence_access_level` honestly. Appraise with a tool
suited to the design and mark the judgement provisional (single AI reviewer). Update `source_register.csv`.
Exit: every included source has a record and register row; excluded sources have reasons.

### 4. Evidence map, claim ledger, synthesis, outline
Build `evidence_matrix.csv`; look across studies for patterns, conflicts and their explanations, time trends and
gaps; draft the claim ledger for the claims the paper will make; state the central argument in two sentences; write
an outline whose headings answer the sub-questions. Run the critical-reviewer pass on the plan (below).
Exit: ledger drafted; argument and outline recorded in `00_project/decision_log.md`; weak spots listed.

### 5. Drafting and visuals (`review-manuscript-docx`)
Draft `manuscript.md` with `[@key]` citations; build figures and tables from code and extracted data into
`05_figures_tables/`; every visual has a purpose, source line, and a sentence in the text.
Exit: complete draft; references library built; no `[UNVERIFIED]` markers; figures regenerate from code.

### 6. Word build
Run `scripts/build_docx.py`; inspect a render; fix. Exit: one `.docx` in `08_final/`, zero unresolved citations.

### 7. Audit (`review-quality-audit`)
Run the automated checks, the five perspective passes, claim-level verification, fixes, and re-checks. Write the
quality report. Exit: issues logged and resolved or explicitly carried; report written.

### 8. Final gate and handoff
Apply the gate in `SKILL.md`. Update `STATE.md`, `README.md`, and the file inventory.

## The five perspective passes

Each pass has a question it must answer and an artifact. Record findings in `07_quality/issues_log.csv` during the
audit; the first four also inform Phases 3-4.

| Perspective | Core question | Where it runs | Artifact |
|---|---|---|---|
| Subject-matter researcher | Is the science right, current, and framed as practitioners would frame it? What would an expert say is missing or mischaracterised? | Phase 4 plan, Phase 7 | Corrections, missing-topic list |
| Methods specialist | Are designs, appraisal, and synthesis choices sound? Are effect sizes, units, denominators, and causal language correct? Does the label match the method? | Phase 3 appraisal, Phase 7 | Appraisal table, methods-conformance list |
| Literature and citation specialist | Is coverage adequate for the stated scope? Are references real, complete, correctly attributed, and read at the level claimed? | Phase 1, Phase 7 | Coverage-gap note, reference audit |
| Critical reviewer | What is the strongest counterargument or counterevidence? Where is the argument weakest? Which claims exceed their evidence? | Phase 4, Phase 7 | Red-team list, revised claim wording |
| Editor and figure specialist | Is structure clear, language precise, and each visual honest, accessible, reproducible, and necessary? Does the Word file work? | Phase 5-6, Phase 7 | Edits, figure and layout fixes |

Adapt the lenses to the field and state which were used. These are analytic perspectives, not people.

## Calibrating effort to project size

| Size | Sources read in full | Approach |
|---|---|---|
| Small (about 15-30) | all | One pass per phase; ledger of 40-80 claims; audit verifies most numeric and causal claims |
| Standard (30-100) | all core, abstract-level for background | Group sources by sub-question; extraction in batches saved after each; ledger of 80-200 claims; verify all numeric, causal, "first/only/consensus" claims plus a 20 percent sample of the rest |
| Large (100+) | all core and a defined subset in full; the rest charted | Sub-theme syntheses written as separate sections of the outline; matrix-first analysis; state plainly in Limitations which tiers were read at which depth |

Depth is set by the evidence the question needs, not by a target page count. Do not enlarge a section to look
thorough; cut sections the evidence cannot support.

## Pausing, resuming, and user checkpoints

- Natural stopping points: after Phase 1 (user downloads papers), after Phase 2 (missing papers), after Phase 4 (optional outline check for big projects). Do not stop elsewhere to ask permission.
- On resume: read `STATE.md`, the decision log, and `source_inventory.csv`; re-run the inventory (it skips unchanged hashes); list what changed; continue from the recorded phase.
- If the user changes scope mid-way, log it, re-run affected phases (catalog gaps, extraction, ledger), and say what became stale.
- If a phase cannot be completed (no full texts, no database access), record the consequence in `STATE.md`, adjust the review label if needed, and proceed with the strongest supported alternative.
