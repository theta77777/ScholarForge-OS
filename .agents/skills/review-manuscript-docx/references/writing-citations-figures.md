# Writing, citations, figures, and Word conventions

## Contents

- Structure by review type
- Argument and paragraph design
- Language calibrated to evidence
- Citation practice
- Figures and tables
- Declarations and front matter
- Pandoc Markdown conventions for the Word build
- Pre-build checklist

## Structure by review type

Common spine: Title; Abstract (structured if the journal wants it) and keywords; Introduction (why the question matters, what is unresolved,
objective and sub-questions); Methods; the body sections that answer the sub-questions; Discussion (synthesis, what it means, how it
changes the field's picture, comparison with earlier reviews); Limitations (of the evidence and of this review); Conclusions and future
directions; Declarations; References; optional Supplementary material.

- Narrative/critical: Methods is a short transparent paragraph or subsection (sources searched, dates, criteria, how sources were weighed, what was not covered). Body sections are thematic or question-led, never paper-by-paper.
- Scoping: Methods follow PRISMA-ScR items; Results chart the evidence (counts, characteristics table, concept map); no effect conclusions.
- Systematic: full PRISMA 2020 Methods and Results (search strings in a supplement, selection numbers with a flow diagram using real counts, appraisal results, synthesis methods, certainty).
- Disclose every departure from the label's standard (single screener, AI-assisted appraisal, unreachable databases). If the standard is not met, use a different label (see review types).

Include a methods-transparency statement on AI assistance (what the tool did: searching, extraction, drafting, checks) and on what humans must verify.

## Argument and paragraph design

- State the central argument early (two sentences) and make each section's first paragraph say what it contributes to it.
- Paragraph pattern: claim, strongest evidence, comparison or conflict and its explanation, limit, link to the next idea. A paragraph that only lists studies ("A found..., B found...") must be rewritten around a point.
- Present disagreement fairly: give each side its best evidence and say why you weight them as you do.
- Separate four tiers wherever they occur: established (consistent, high-certainty evidence), contested (credible conflicting evidence), plausible interpretation (consistent with evidence, untested), open question. Use these words or equivalents consistently.
- Novelty claims ("first review", "no study has") need a documented search that supports them; otherwise write "to our knowledge, within the sources searched".

## Language calibrated to evidence

| Evidence | Wording |
|---|---|
| Replicated, high certainty, causal design | "demonstrate", "cause" (when the design supports it) |
| Consistent but observational | "are associated with", "is consistent with" |
| Single study or low certainty | "suggests", "one study reports", "preliminary" |
| Your inference across studies | "this pattern may indicate", "a plausible reading is" |
| Absence of evidence | "was not examined in the studies reviewed", not "has no effect" |
Avoid: "proves", "clearly shows", "it is well known", "everyone agrees", unqualified "significant" (say statistically significant or practically important), generalising beyond the populations and
settings studied, and implications for practice or policy stronger than the evidence (for clinical topics add that the review is not clinical advice). Report effect sizes with units, intervals, and sample sizes where they matter.

## Citation practice

- Cite at the claim, not at the paragraph end. Several sources for one claim: `[@a; @b]`. A page or table when a specific number is cited: `[@a, p. 12]` only if the locator is in the ledger.
- Cite primary studies for findings; cite reviews for field-level statements and say they are reviews.
- Do not cite what you did not read for a specific finding. "As reported in X" is the only way to pass on a secondary claim, and avoid it where the primary is available.
- Each key must exist in `references.json`; build with `--cited-from` so the library matches the text exactly.
- Preprints are labelled as such; use the version of record when both exist.
- Self-check: could a reader find the source from the reference alone? DOI or URL present?

## Figures and tables

Purposes that justify a visual: evidence map (sub-question by design or context), study-characteristics table, comparison of effect estimates with intervals (only with
extracted data), timeline of key developments, conceptual framework (labelled schematic), flow diagram (only with real logged counts), summary of certainty by conclusion.

Design rules: every axis labelled with units; bar charts start at zero; intervals or spread shown where available; consistent order and colour meaning;
colour-blind-safe palette and legible greyscale; fonts at or above 8 pt in the final size; no chart junk; one message per figure.
Caption: `Figure N. What it shows. Source/data: ... Abbreviations: ...`. Alt text in the Markdown brackets describes the content for screen readers.
Tables: header row, units in headers, footnotes for abbreviations and sources, no more than about 8 columns portrait; move larger tables to a
supplement (landscape sections are hard to keep stable in this build).
Reproduce nothing from a source figure; "adapted from [@key]" needs a redraw from reported data and a note that permission or licence terms
were checked by the human authors. Generated imagery is never evidence and is labelled "schematic illustration".
Reproducibility: figure scripts take input from `04_analysis/data/`, write to `05_figures_tables/`, set seeds, and print package versions to a log.

## Declarations and front matter

Leave bracketed placeholders for: authors and affiliations, corresponding author, ethics statement (usually "not applicable, no new data"), funding, competing
interests, author contributions (CRediT), data and materials availability (supplementary extraction tables, code), acknowledgements, and the journal's AI-use disclosure
(describe the tools' role accurately; human authors take responsibility). Never fill these with invented content or attribute them to real people.

## Pandoc Markdown conventions for the Word build

- Headings `#`, `##`, `###` become Word Heading 1-3. Do not number manually unless the journal requires it.
- Table with caption above (caption text must start `Table N.` so a SEQ field is created):

```markdown
Table: Table 1. Characteristics of included studies.

| Study | Design | n |
|:--|:--|--:|
| ... | ... | ... |
```
- Figure with caption below (alt text and caption are the bracket text): `![Figure 1. Caption text. Source: ...](../05_figures_tables/figure_01_name.png){width=90%}`
- Page break: a fenced raw block ` ```{=openxml} ` containing `<w:p><w:r><w:br w:type="page"/></w:r></w:p>`
- Equations: `$...$` inline and `$$...$$` display become editable Word equations.
- Footnotes: `text[^1]` with `[^1]: note`. Italic `*x*`, bold `**x**`, subscripts `H~2~O`, superscripts `m^2^`.
- References placement: end the file with `# References` and a `::: {#refs}` / `:::` div so the list lands there.
- Non-breaking details: use real Unicode (en dashes, minus signs, degree and Greek characters) and `smart` typography is on, so type straight quotes.
- In-text references to tables and figures are typed ("Table 2") and not live cross-references; the audit checks they match; tell the user that reordering items needs those mentions updated.

## Pre-build checklist

All ledger claims for this draft exist with a `manuscript_section`; no `[UNVERIFIED]`, `TODO`, `TBD`; every table and figure is mentioned in the text and has a source line; captions numbered
in order; abstract numbers match body numbers; keywords and running title set; declarations placeholders present; word count against the journal limit; every key resolves.
