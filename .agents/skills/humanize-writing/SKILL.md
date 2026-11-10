---
name: humanize-writing
description: >-
  Rewrites or drafts text to eliminate formulaic, repetitive, or robotic AI writing patterns (such as those documented
  on Wikipedia's 'Signs of AI writing'), restoring natural sentence variety and human academic voice while strictly
  maintaining factual fidelity, citations, tables, and numerical precision. Trigger ONLY when the user explicitly asks
  by name (e.g. 'humanize this', 'make this not sound like AI', 'run the humanizer', 'de-AI this').
---

# Humanize Writing (AI-Tell Auditing & Natural Flow)

Audits and eliminates artificial, formulaic AI writing patterns while preserving 100% of the underlying factual, numerical, and citation content.

## Key Tells Eliminated

- **Overused AI Clichés**: "delve into", "beacon of hope", "tapestry", "crucial role", "testament to", "game-changer", "pivotal", "in conclusion, it is important to remember".
- **Uniform Sentence Cadence**: Replaces monotonous subject-verb-object structures with varied rhythms, compound-complex sentences, and natural pauses.
- **Superficial Symmetry**: Eliminates mechanically balanced three-part bullet structures when evidence is uneven.
- **Empty Framing**: Removes throat-clearing introductory and concluding scaffolding that adds no informational value.

## Scripts & References

- [Inventory of AI Tells](./references/tells.md)
- [Text Audit Script](./scripts/audit.py)
- [Word Document Patcher Script](./scripts/docx_apply.py)
