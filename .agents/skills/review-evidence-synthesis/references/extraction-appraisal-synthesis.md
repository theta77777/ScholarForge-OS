# Extraction, appraisal, and synthesis methods

## Contents

- Extraction record template
- Numeric accuracy protocol
- Appraisal tools by design
- Generic appraisal rubric
- Certainty of evidence
- Synthesis methods
- Quantitative pooling conditions
- Special situations

## Extraction record template (`03_extraction/records/<catalog_id>.md`)

```markdown
# C012 smith2021effects
Citation: (from catalog; do not retype from memory)
Evidence access level: full_text | abstract_only | secondary_only   Text status: ok | ocr-verify
Design / article type:
Setting, population or system, sample size or scale:
Methods (exposure/intervention/model/instrument, comparator, measures, analysis):
Key results (each with locator): 
  - R1: [result in own words, numbers with units and CI/SD] — p.7, Table 2
Authors' stated limitations (locator):
Funding / conflicts of interest / data and code availability:
Relation to the review's sub-questions (which, and how):
Appraisal (tool, domain judgements with the supporting text and locator; "provisional: single AI reviewer"):
Concerns to verify (inconsistencies, unclear methods, suspected overlap with other papers):
Short quotations (under 15 words, exact, with locator) — only where wording matters:
```

## Numeric accuracy protocol

1. Record numbers from tables or figures first, then compare with the text; if they disagree note both and use the table unless the paper explains otherwise.
2. Keep original units; add a harmonised column only after converting with the formula noted.
3. Record denominators, time frames, subgroup definitions, and whether estimates are adjusted.
4. For key numbers that will appear in the paper, re-read the source passage a second time before the ledger row is marked verified.
5. OCR-derived or figure-read numbers are marked approximate and checked against the page image.

## Appraisal tools by design (use what fits; name the tool in the record)

| Design | Tool |
|---|---|
| Randomised trial | RoB 2 |
| Non-randomised intervention | ROBINS-I |
| Cohort, case-control | Newcastle-Ottawa Scale or JBI checklist |
| Cross-sectional | AXIS or JBI |
| Diagnostic accuracy | QUADAS-2 |
| Prediction models | PROBAST |
| Systematic review / meta-analysis | AMSTAR 2 or ROBIS |
| Animal studies | SYRCLE risk of bias; ARRIVE reporting |
| Qualitative | CASP or JBI; GRADE-CERQual for confidence in findings |
| Mixed methods | MMAT |
| Economic evaluation | CHEERS (reporting) with a quality checklist |
| Computational / ML | Generic rubric below plus leakage, baselines, ablations, variance across seeds, compute and data disclosure |
| Laboratory / physical science | Generic rubric plus calibration, controls, replication, uncertainty propagation |
| Theory, conceptual, historical | Source criticism: provenance, internal consistency, engagement with counterevidence |

## Generic appraisal rubric (rate each domain: low / some / high concern, with the reason and locator)

1. Fit between question and design (can this design support the claim made?)
2. Sampling or selection (representativeness, selection effects, exclusions)
3. Measurement validity and reliability (instruments, operationalisation, blinding where relevant)
4. Confounding, controls, comparators, baselines
5. Analysis (appropriate methods, multiplicity, missing data, model assumptions, uncertainty reported)
6. Reporting completeness (selective reporting, outcomes pre-specified or not, data and code available)
7. Independence and conflicts (funding, author stakes, duplicate publication)
8. Consistency with the rest of the evidence (outlier? explained?)
Overall: state the main reasons the result may be wrong, and how much weight the finding bears in the synthesis.

## Certainty of evidence

For each main conclusion state certainty (high, moderate, low, very low) from: risk of bias; inconsistency across studies; indirectness
(population, setting, outcome); imprecision (wide intervals, small samples); publication or reporting bias; and factors that raise
certainty (large consistent effects, dose-response). Say "adapted from GRADE; formal GRADE not performed" unless a formal assessment with
a summary-of-findings table was actually done. For qualitative findings use GRADE-CERQual domains. For non-clinical fields phrase it as
"strength of evidence" with the same reasons.

## Synthesis methods

- Evidence matrix: rows are studies, columns are design, population or system, method, outcome, result, direction, quality. Sort by sub-question and by design strength; look at it, not only through it.
- Thematic or conceptual synthesis: group findings by mechanism or construct, not by paper; each theme gets a claim, the supporting sources, the dissenting sources, and the explanation for differences.
- Explaining conflict: test whether disagreement tracks population, dose or intensity, measurement, era, geography, design, funding, or analysis choice; say when it cannot be explained.
- Temporal and developmental view: how questions, methods, and findings changed; whether newer, better designs changed older conclusions.
- Gap analysis: studied versus unstudied combinations of population, method, outcome, context; tabulate counts only for the included set and say so.
- Structured narrative (SWiM): state grouping rationale, standardised metric, synthesis method, how heterogeneity was investigated, and certainty. Do not count votes by direction; weigh by design, precision, and bias.
- Critical analysis: expose assumptions shared by a literature, circularity, construct problems, and incentives, with evidence.
- Overlap control: identical cohorts, datasets, or benchmarks across papers count once for strength-of-evidence purposes.

## Quantitative pooling conditions

Pool only when all hold: the same estimand and comparable effect measures are extractable; study designs are compatible; the number of
studies and their precision allow a meaningful estimate; the model (fixed, random-effects) and heterogeneity measures (tau-squared,
I-squared, prediction interval) are chosen in advance and reported; sensitivity analyses (leave-one-out, risk-of-bias strata) and a
small-study check are run when 10 or more studies exist. Save the extracted data (`04_analysis/data/`) and the code
(`04_analysis/code/`, with package versions and seed) so every number and forest plot can be regenerated. If any condition fails, do not
pool; explain why and synthesise narratively. Never invent or impute missing effect sizes silently; if you must, name the method and test its impact.

## Special situations

- Abstract-only sources: use for existence, stated aim, and headline finding as the abstract states it; label as such; not for methodological critique or fine detail.
- Preprint and published versions: cite the version of record when both exist and note differences you saw.
- Retracted or corrected papers: exclude from evidence; discuss only as part of the literature's integrity if relevant; check core papers.
- Non-English sources: summarise only if you can read them reliably; otherwise flag as not appraised.
- Missing supplements or data: note the dependency; do not assume contents.
- Paper contradicts the catalog record (title, year, DOI): stop, record the conflict, ask the user.
- Source asserts consensus: look for the evidence, not the assertion.
- Self-citation or review-of-review chains inflating apparent support: trace to primary studies.
