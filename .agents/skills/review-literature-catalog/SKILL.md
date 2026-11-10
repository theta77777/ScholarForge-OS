---
name: review-literature-catalog
description: >-
  Builds a verified catalog of candidate scientific papers within an agreed scope, with title, authors, year, journal,
  DOI, relevance tier (core, supporting, background), access status (open full text, free repository version, subscription,
  paywalled), direct landing/PDF links, and search logs. Use whenever the user asks to find, list, collect, map, or
  catalog literature on a topic, wants a reading list for a review, or needs academic database search strings.
---

# Literature Catalog & Systematic Search

Produces `01_search/catalog/literature_catalog.xlsx` (primary), `.csv`, and `catalog_report.md`, alongside `search_log.csv`.
The catalog provides a transparent, defensible audit trail of literature exploration before data extraction begins.

## Search Strategy & Antigravity Tools

When conducting literature searches in Antigravity:
1. **Academic Database Skills**: Query installed Antigravity science skills when available:
   - `pubmed-database`: PubMed/MEDLINE clinical and biomedical search.
   - `literature-search-europepmc`: Europe PMC open-access papers and full-text XML.
   - `literature-search-openalex`: Comprehensive scholarly metadata and citation graphs.
   - `clinical-trials-database`: Registered clinical trial protocols (NCT IDs).
2. **Web & Open Access Repositories**: Use `search_web` to discover seminal papers, high-impact review articles, and preprint servers (arXiv, bioRxiv, medRxiv).
3. **Citation Chasing**: Trace references backward from landmark reviews and search forward citations.

## Logging & Verification Rules

Every search query MUST be logged in `01_search/search_log.csv` (`date, source_or_database, access_used, query, filters, results_reviewed, candidates_added, notes`).

For each candidate paper:
- Verify DOI and bibliographic metadata against the official landing page.
- Assign `relevance_tier`:
  - `core`: Seminal trials, direct PICO matches, or foundational mechanistic studies.
  - `supporting`: Corroborating cohorts, secondary endpoints, or mechanistic analogies.
  - `background`: General epidemiology, clinical context, or historical framing.
- Record `access_status`: `open_full_text`, `open_version_found`, `subscription_confirmed`, or `paywalled`. Never mislabel an abstract as full-text.

## Catalog Compilation Script

Compile the candidate list into a polished CSL bibliography and multi-format catalog:
```powershell
python scripts/build_catalog.py --in 01_search/candidates.csv --out-dir 01_search/catalog
```

## References & Assets

- [Search Strategy & Verification Ladder](./references/search-and-access.md)
- [Candidate Catalog Template](./assets/candidates_template.csv)
- [Catalog Builder Script](./scripts/build_catalog.py)
