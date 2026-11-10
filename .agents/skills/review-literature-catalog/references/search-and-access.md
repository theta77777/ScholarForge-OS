# Search strategy, verification, and access determination

## Contents

- Building the search
- Verification ladder
- Determining access status
- Retraction and correction checks
- Database strings for the user to run
- Importing user exports
- Coverage notes template
- Common failure modes

## Building the search

1. Concept table: one row per concept (population/system, exposure or method, outcome, context). Columns: preferred term, synonyms, acronyms, spelling variants (British/American), broader and narrower terms, controlled-vocabulary terms.
2. Query combinations: OR within a concept, AND between concepts. Start broad (two concepts), then narrow. Run each combination in web search as natural-language queries and as quoted phrases; add `review`, `systematic review`, `meta-analysis`, `trial`, `benchmark`, `survey` as study-type probes, and year constraints for recency.
3. Seed papers: identify 3-5 key reviews and seminal papers. Read their reference lists (backward chasing) and look for "cited by" or "related articles" on their pages (forward chasing). Papers that appear in several independent lists are likely core.
4. Date and language scope: obey the brief. Always check for seminal works outside the date range and flag them as `background` with a note.
5. Grey literature and preprints: include only if the scope allows; mark `version_type` and `study_type` so the manuscript can discount them.
6. Saturation: when three consecutive new queries return no new core candidate, stop and say so. If you stopped because of effort or tool limits, say that instead.
7. Log every query, including empty ones. A search log that shows only successes misstates coverage.

## Verification ladder

| Level | Evidence | Allowed use |
|---|---|---|
| `verified` | Publisher, DOI, repository page, or connector record opened; title, authors, year, venue read from it | Catalog, citation |
| `reported` | Title and details seen in a search snippet, a list, or another paper's references | Catalog with flag; verify before citing |
| `unverified` | Recalled from memory, or only partly matched | Do not present as fact; verify or drop |

If title and DOI disagree, record `uncertainty_note: DOI resolves to a different title` and do not guess. If search
snippets conflict (year of online-first versus issue), record the version-of-record year and note the other.

## Determining access status

Look at the record page and at free-access indicators; do not infer from the publisher's reputation.

- Free full text: the page shows an open-access label and a downloadable PDF or full HTML; or the paper is in PMC/Europe PMC; or on arXiv/bioRxiv/medRxiv; or in an institutional or subject repository. Open the link and confirm it lands on the paper's full text, not a login, abstract, or "get access" page. Fill `fulltext_link` with that link and set `fulltext_link_type` (`publisher_pdf`, `publisher_html`, `pmc`, `preprint_server`, `repository`).
- Version: a free copy that is not the version of record is `open_version_found`; set `version_type` (`preprint`, `accepted_manuscript`) and note that numbers or wording may differ from the published paper.
- Subscription: publisher page shows "purchase", "log in", "institutional access", or an abstract only. Use `subscription_possible` and say so in `access_note`. Do not say "you can get it through your library"; say "may be available through an institution or subscription".
- `subscription_confirmed` only when the user stated which subscriptions they hold, or a connector returned the full text. Describe the route.
- `paywalled` when no free route was found; suggest interlibrary loan, contacting the corresponding author (publicly listed), or purchase.
- `unknown` when you did not check. It is better than a guess.
- If a site blocks you or you cannot open the page, record that in `access_note` and leave `access_status` as `unknown`.
- Never link to Sci-Hub-type sites, scraped PDF mirrors, or file-sharing copies; if one appears in results, ignore it. Prefer the publisher or a recognised repository even when a mirror is easier.
- Licence: if a licence is visible (CC BY etc.), note it in `access_note`; it tells the user what reuse is allowed.

## Retraction and correction checks

For every `core` paper and any paper that will carry a headline claim, look for notices on the publisher page
(banners such as "retracted", "expression of concern", "correction"), the DOI landing page, or a retraction database
if reachable. Set `retraction_check` to `clear` only if you looked; `flagged` with details in `uncertainty_note`
otherwise; `not_checked` if not done. Never cite a retracted paper as evidence of an effect; discuss it as a retraction
case only if relevant.

## Database strings for the user to run

When a subscription database or a database you cannot reach would normally be searched, write
`01_search/database_search_strings.md` with one block per database: the exact string, field tags, filters, and the date
range, plus a line telling the user to export RIS or CSV and drop it in `01_search/`. Syntax notes:

- PubMed: `("term"[Title/Abstract] OR "MeSH term"[MeSH Terms]) AND ...`; date filter `("2015/01/01"[Date - Publication] : "3000"[Date - Publication])`
- Scopus: `TITLE-ABS-KEY(("a" OR "b") AND ("c")) AND PUBYEAR > 2014`
- Web of Science: `TS=(("a" OR "b") AND ("c"))` with `PY=2015-2026`
- Embase (Embase.com): `('a':ti,ab,kw OR 'b'/exp) AND ...` with Emtree terms
- PsycINFO (Ovid): `(a or b).ti,ab. AND ...` plus subject headings with `exp`
- IEEE Xplore / ACM DL / arXiv: field search or advanced search; mention that Boolean support and truncation differ
Say these strings were not run by the assistant. A systematic review needs them run and reported (see review types).

## Importing user exports

RIS, BibTeX, or CSV from a database export: parse with a short script (pandas for CSV, `rispy` if installed, or a
hand-written RIS parser), map fields to the candidate columns, set `found_via` to the database name and export date,
`record_verification: verified` (the export is the database's own record), and `access_status: unknown`. Then
re-run `build_catalog.py`; duplicates against existing rows are merged by DOI or normalised title and year.

## Coverage notes template (`01_search/coverage_notes.md`)

- Sources searched (name, date, access route) and sources not reachable
- Query families and where the strings are in the search log
- Date, language, and study-type limits applied
- Saturation statement (reached or not, and why)
- Known gaps: subscription databases, non-English literature, grey literature, paywalled full texts, regions or populations under-represented
- What the catalog does not claim

## Common failure modes

Treating a DOI link as a full-text link; marking a preprint as the published paper; copying details from an AI-written
summary rather than the record; missing seminal pre-range papers; relying on one search engine's first page; ignoring
review articles that define the field's vocabulary; forgetting to log empty searches; letting the catalog balloon with
loosely related papers (a catalog of 500 weak candidates is less useful than 120 well-tiered ones).
