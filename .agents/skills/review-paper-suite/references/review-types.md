# Choosing and labelling the review type

The label is a promise about method. Use a label only when the work meets its requirements; otherwise use the
honest label and disclose the departures. Read this in Phase 0 and again before writing the Methods section.

## Contents

- Decision guide
- Requirements by type
- Labelling rules when rigour cannot be met
- Reporting guidelines by type and field
- Field adaptations
- Question formulation frames

## Decision guide

| The user wants... | Type |
|---|---|
| A reasoned overview that builds an argument across a field | Narrative (state-of-the-art) review |
| To question assumptions, expose weak foundations, propose a framework | Critical review |
| To map what exists, how it is studied, and where the gaps are, without judging effect sizes | Scoping review |
| A reproducible answer to a focused question with explicit methods | Systematic review (with or without meta-analysis) |
| To synthesise existing reviews | Umbrella review / overview of reviews |
| A quick evidence summary for a decision | Rapid review (state the shortcuts) |

If the user says "systematic" the standard is systematic. If they say "literature review" with no more, deliver a
structured narrative or critical review and say which in the Methods. Do not upgrade the label to look stronger.

## Requirements by type

| Type | Search | Selection | Appraisal | Synthesis | Reporting |
|---|---|---|---|---|---|
| Narrative / critical | Documented, multi-source, purposive; state limits | Stated criteria, flexible | Informal but explicit; weigh design and bias in text | Thematic, argument-led | SANRA as a self-check; transparent Methods paragraph |
| Scoping | Systematic-style, documented, multi-database where possible | Stated criteria, screening log | Optional; if skipped say so | Charting table, counts, concept map | PRISMA-ScR; JBI/Arksey-O'Malley-Levac framework |
| Systematic | Pre-specified strategy, at least two bibliographic databases plus citation chasing, full strings reported, dates run | Two-stage (title/abstract, full text) with logged reasons; independent second screener | Validated tool per design | Narrative (SWiM) or meta-analysis if data allow | PRISMA 2020, protocol (PRISMA-P; register in PROSPERO or OSF when appropriate), flow diagram with real counts |
| Meta-analysis | As systematic | As systematic | As systematic plus small-study/publication-bias checks | Pooled estimates, heterogeneity, sensitivity analysis, code and data saved | PRISMA 2020; MOOSE for observational |
| Umbrella | Search for reviews | Overlap of primary studies assessed | AMSTAR 2 or ROBIS | Tabulated, overlap-adjusted | PRIOR |
| Rapid | Narrowed, stated shortcuts | Single screener acceptable if disclosed | Reduced, disclosed | Narrative | PRISMA with shortcut disclosure |

## Labelling rules when rigour cannot be met

The suite is usually one assistant plus whatever databases and full texts are reachable. For a systematic review
that typically means: no guaranteed access to Embase, Scopus, Web of Science or PsycINFO; one screener (the
assistant) rather than two independent humans; AI-assisted appraisal. Therefore:

1. Ask the user to run the supplied database search strings and export results (RIS/CSV); import them as candidates. Without that, do not call the work a systematic review.
2. Recommend a second human screener for a sample (at least 20 percent of full-text decisions) and record agreement if done.
3. If conditions are not met, label it "structured literature review" or "systematic-style review", list each departure in Methods and Limitations, and never fill a PRISMA flow diagram with invented or estimated counts.
4. Register or publish a protocol only through the user; never claim a protocol was registered.

## Reporting guidelines (name what you followed, tick what you met, disclose what you did not)

- PRISMA 2020 and PRISMA-S (search reporting); PRISMA-P (protocols); PRISMA-ScR (scoping)
- SWiM (synthesis without meta-analysis); MOOSE (observational meta-analysis); PRIOR (overviews)
- SANRA (narrative review self-check); ENTREQ (qualitative synthesis); RAMESES (realist)
- ROSES (environmental evidence); Kitchenham and Charters (software engineering SLRs)
- Appraisal and certainty: RoB 2, ROBINS-I, QUADAS-2, PROBAST, AMSTAR 2, ROBIS, JBI checklists, CASP, MMAT, NOS, SYRCLE, GRADE, GRADE-CERQual
If a journal specifies a checklist, it overrides these defaults. Do not tick items you cannot support.

## Field adaptations

- Clinical and public health: PICO/PECO, study-design hierarchy, patient-relevant outcomes, GRADE; avoid clinical recommendations unless the evidence and user role justify them, and say they are not medical advice.
- Social science and education: construct validity, sampling frames, measurement invariance, context dependence; mixed-methods appraisal (MMAT).
- Engineering, computing and AI: benchmark validity, leakage, baselines, compute and data disclosure, reproducibility (code/data availability), version dependence; preprints are common, so mark them.
- Physical, chemical and earth sciences: measurement uncertainty, calibration, model validation, units, scale; reconcile conflicting parameter values explicitly.
- Humanities and theory-led reviews: source criticism, historiographic framing; "appraisal" is interpretive, so say how sources were weighed.

## Question formulation frames

PICO / PECO (population, intervention or exposure, comparator, outcome); PCC (population, concept, context) for
scoping; SPIDER for qualitative; or a free-form question with named sub-questions. Write the question and sub-questions
in the brief, and make section headings answer them.
