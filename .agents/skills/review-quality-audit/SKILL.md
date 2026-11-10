---
name: review-quality-audit
description: >-
  Audits and verifies a scientific review manuscript before delivery through five analytic perspectives (subject expert,
  methodology specialist, literature/citation specialist, critical reviewer, editor/figures), automated verification of
  citations, reference library, claims ledger, Word structure, captions, placeholders, and verbatim source overlap,
  claim-level re-verification against source text, and a candid quality report separating verified checks from unverified limitations.
  Use to audit, proofread, fact-check, peer-review, or stress-test review drafts.
---

# Quality Audit Arena & Verification Protocol

Provides rigorous pre-submission verification to ensure factual accuracy, citation integrity, and methodological soundess.

## Step 1: Automated Verification Scripts

Execute the automated audit suite against the compiled manuscript and evidence base:
```powershell
# Check Word structure, table formatting, SEQ captions, and placeholders
python scripts/check_docx.py 08_final/review_manuscript.docx --out 07_quality/checks/docx_check.json

# Cross-verify citations between manuscript text, CSL library, claims ledger, and source register
python scripts/check_citations.py --manuscript 06_manuscript/manuscript.md --bib 06_manuscript/references.json --ledger 03_extraction/claims.csv --register 03_extraction/source_register.csv --out 07_quality/checks/citation_check.json

# Scan for verbatim n-gram overlap against source texts
python scripts/check_overlap.py --manuscript 06_manuscript/manuscript.md --texts 03_extraction/text --out 07_quality/checks/overlap_check.csv
```

## Step 2: 5-Perspective Analytic Review

Conduct structured review passes and log all findings in `07_quality/issues_log.csv`:
1. **Subject-Matter Researcher Pass**: Checks domain nuance, biological plausibility, and field consensus vs. active debate.
2. **Methodology Specialist Pass**: Verifies study design categorization, statistical interpretation, and risk-of-bias consistency.
3. **Citation & Integrity Specialist Pass**: Checks for ghost citations, retracted papers, and citation context drift.
4. **Critical Reviewer Pass (Adversarial)**: Actively constructs the counter-argument to the review's primary theses and checks for contrary evidence.
5. **Editorial & Figure Specialist Pass**: Scans for banned AI clichés, formulaic transitional scaffolding, and figure caption clarity.

## Step 3: Claim-Level Source Re-Verification

Re-read source texts in `03_extraction/text/` for all numerical assertions, causal claims, and superlative statements ("first", "only", "gold standard").
Record results in `07_quality/quality_report.md` with explicit transparency about what was checked vs. what could not be verified.

## References & Scripts

- [Audit Checklists & Quality Protocol](./references/audit-checklists.md)
- [Word Document Checker](./scripts/check_docx.py)
- [Citation Cross-Checker](./scripts/check_citations.py)
- [Verbatim Overlap Checker](./scripts/check_overlap.py)
