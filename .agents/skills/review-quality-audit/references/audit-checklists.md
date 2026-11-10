# Audit checklists, protocols, and report template

## Contents

- Issues log and severity scale
- Perspective checklists
- Claim verification protocol
- Number and consistency checks
- Reference verification protocol
- Word and layout checklist
- Overlap and originality protocol
- Quality report template

## Issues log and severity scale

`07_quality/issues_log.csv` columns: `issue_id, perspective, severity, location, description, evidence, action, status, recheck_result`.

| Severity | Meaning | Example |
|---|---|---|
| critical | Makes a claim false, a source nonexistent, or the label dishonest; blocks delivery | Fabricated or unverifiable reference; flow diagram with invented counts; "systematic" label without method |
| major | Materially misleads or weakens the argument | Causal wording for observational data; number disagrees with source; unaddressed strong counterevidence |
| minor | Reduces quality, not validity | Inconsistent terminology; unclear caption; missing alt text |
| info | Note or preference | Optional additional figure |

Status: `open`, `fixed`, `wont_fix` (with reason), `needs_user`. Critical and major issues are fixed or explicitly carried in the report before the final gate.

## Perspective checklists

### Subject-matter researcher
- Is the framing, terminology, and sequence of ideas what practitioners of the field would recognise? Any outdated concepts or superseded findings?
- Are key sub-areas, landmark works, and recent developments present? What would a reviewer in the field say is missing?
- Are mechanisms, scales, units, and conditions stated correctly? Are claims placed in the right context (species, population, material, regime, dataset)?
- Does the paper separate what is known, contested, plausible, and open?
- Are practical, clinical, or policy implications proportionate and caveated?

### Methods specialist
- Does the review label match what was done (review types)? Are Methods complete enough to repeat?
- Are inclusion rules applied consistently; are exclusions justified; is selection bias from access (only free papers) disclosed?
- Were appraisal tools suited to the designs; are ratings supported by text; is single-reviewer appraisal disclosed?
- Are effect sizes, intervals, denominators, units, and time frames correct and comparable? Any double-counted cohorts?
- Is causal language earned by design? Is certainty stated with reasons? Is pooling justified or avoided appropriately?

### Literature and citation specialist
- Coverage against the stated scope: seminal works, major reviews, opposing groups, recent years, non-US/EU or non-English work if in scope.
- Reference accuracy: authors, year, title, venue, DOI; version (preprint versus record); retractions and corrections.
- Read-level honesty: every cited source for a specific finding has `full_text`; abstract-only sources are labelled in text.
- Primary versus secondary citation discipline; no citation padding; no orphan references; no missing ones.
- Citation style consistency and completeness for the target journal.

### Critical reviewer
- State the strongest argument against the central thesis; find evidence for it; check whether the paper confronts it.
- Which three claims are weakest? What would falsify them?
- Are there alternative explanations for the patterns synthesised? Selection by the review's own search?
- Does the conclusion go beyond the results? Are limitations real (not decorative)?
- Are novelty, consensus, or "first" claims supported by the documented search?

### Editor and figure specialist
- Structure: logical order, signposting, section balance, no repetition or contradiction, abstract matches body.
- Language: precise, concise, consistent terminology and abbreviations defined at first use, no filler, no unexplained jargon, hedging used deliberately.
- Figures: purpose, honest axes, uncertainty, labels, units, legibility at final size, colour accessibility, caption sufficient to stand alone, source line, reproducible from code.
- Tables: needed, readable, consistent decimals and units, footnotes.
- Word file: styles used correctly, captions numbered, navigation works, references formatted, no stray formatting.

## Claim verification protocol

1. Select: all rows with numbers, causal verbs, superlatives or consensus language, characterisations of core papers; plus a random or evenly spaced sample of at least 20 percent of the rest (minimum 25 if that many exist).
2. For each: open the source passage at the recorded locator in the extracted text (or the original file if the text is OCR or unclear); compare the claim's number, direction, population, setting, comparator, and qualifiers.
3. Outcomes: `verified` (faithful), `revised` (edit manuscript and ledger to match the source), `dropped` (unsupported), or `needs_user` (cannot be checked, for example abstract-only).
4. Hedging audit: wording strength must not exceed `support_level` and certainty.
5. Record counts: claims total, checked, verified, revised, dropped, unchecked.

## Number and consistency checks

Recompute sums, percentages, and rates from the data files; check rounding conventions; compare every number that appears in more than one place (abstract, text, tables, figures, captions); check that units and
scales agree across tables and figures; confirm counts of studies and participants against the register and matrix; check dates and years in the narrative against the library; look for contradictory statements across sections.

## Reference verification protocol

For each reference in the check set: (1) open the DOI or publisher/repository page or connector record; (2) compare first author, year, title, venue; (3) note retractions or corrections; (4) record result in the issues log if different.
Outcomes: matches, corrected from record, could not be verified (reason), not checked. Where no web access exists, mark all as "not verified against external records" and say that the check was limited to internal consistency.
If a reference cannot be located anywhere, treat it as critical: remove its citations or replace the support with a verified source.

## Word and layout checklist

Run `check_docx.py` and then view rendered pages: title block; heading levels; paragraph spacing; table borders, header repeat, widths, no clipped columns; figures sized to the text width, not split from captions; captions in order; reference list hanging indent;
page numbers and running head; line numbers if requested; fonts consistent; no empty pages; hyperlinks readable; equations present in the XML even if the renderer omits them. Confirm the file opens with python-docx and that `validate.py` (docx skill) reported no `document.xml` errors; note the known
pandoc-stock-style nits in styles, numbering, and settings if they appear. Confirm exactly one current `.docx` is at the top of `08_final/` and that no PDF was produced unless requested.

## Overlap and originality protocol

Run `check_overlap.py`. For each unquoted run: rewrite the passage in new structure and words, keeping the citation. For quoted runs: confirm the quotation is exact, short, and attributed. Re-run until no unquoted runs remain or the remainder is accounted for (for example standard terms or method names).
Report that the check compared only against supplied source texts and exact word sequences. If an external similarity tool was run by the user, record the service, date, overall score, and how overlaps were handled; if not, state "not run". Never rewrite solely to lower a score, and never present any score as proof of originality.

## Quality report template (`07_quality/quality_report.md`)

```markdown
# Quality and limitations report
Manuscript: <file name, build date>   Review label: <type>   Prepared with AI assistance; not expert-validated.

## 1. Checks performed (status: passed | fixed and rechecked | open issues | not possible)
| Check | Status | Scope / denominator | Notes |
Automated Word structure | ... ; Citation and library consistency | ... ; Ledger-to-source verification | verified X of Y claims | ... ;
Reference existence check | N of M verified externally | ... ; Retraction check on core papers | ... ; Numeric recomputation | ... ;
Local overlap check | against N supplied texts, exact runs >= 8 words | ... ; External similarity screen | not run / run by user, see below ;
Visual render inspection | pages viewed | ... ; Docx XML validation | ...

## 2. Issues by severity and disposition (counts, then critical and major listed)

## 3. Unresolved items and what would resolve them

## 4. Limitations
Evidence base (coverage, access mix, full-text depth); process (single AI reviewer, provisional appraisal, unreachable databases, search saturation); manuscript (claims carried at low certainty).

## 5. Decisions for the human authors
Authors and declarations; AI-use disclosure wording; journal fit and template; independent expert review; second screener or appraiser if a systematic label is intended.
```
