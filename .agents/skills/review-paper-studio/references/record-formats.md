# Helper inputs and actual research states

Helpers do not search, appraise or verify claims automatically. Populate them only with work actually performed. All paths below are relative to an individual review project.

## project.json

init_review.py copies assets/defaults.json and adds title, field, undecided review_type, unselected journal and figure_label_words=0. Preserve explicit overrides in PROJECT_CONTROL.md and update corresponding config fields. If the target changes from 6500 to 4500, update main_words_target/min/max together. Set whole_words_max to the agreed ceiling or null when there is no whole-paper cap. Count visible figure labels from final editable artwork; do not leave zero for labelled figures. The reference interval is a preference, not a scientific requirement.

The initializer uses --out, --title and optional --field. Reusing a folder with the same title preserves existing files; a different title raises an error. It does not mark any research complete. Start a new project for a new paper.

## references.json

An ordered list, one record per cited bibliographic identity. Required checker fields: number (integer starting at 1), report_id (unique stable ID), title, citation (the exact bibliography paragraph excluding its numeric prefix), identity_status="verified", identity_source (actual original/authoritative URL or source location), identity_checked_at (actual ISO date). DOI is optional; use ISBN/edition/authoritative URL when appropriate. Include source_access, reading_status, extraction_status, appraisal_status, publication_status and limits for research, even though the mechanical helper does not certify them.

Schema illustration, not a real source or a claim of verification:

```json
[
  {
    "number": 1,
    "report_id": "R0001",
    "title": "Actual verified title",
    "citation": "Exact verified formatted citation",
    "doi": "",
    "isbn_or_identifier": "actual identifier when applicable",
    "identity_status": "verified",
    "identity_source": "actual authoritative source location",
    "identity_checked_at": "actual verification date",
    "source_access": "fulltext or abstract or metadata",
    "reading_status": "actual status",
    "extraction_status": "actual status",
    "appraisal_status": "actual status",
    "publication_status": "actual checked status and limits",
    "limits": "source-specific limitations"
  }
]
```

Do not set verified merely to satisfy the checker. The supplied state is self-reported execution evidence and needs preserved source support. Keep RIS/BibTeX consistent with this library.

## MANUSCRIPT.md

Use # for title and ## for major sections. The helper recognizes Introduction, with optional numeric prefix, as the start of main prose. It excludes sections named Tables, Figures, Statements and Declarations or Declarations, and stops at References. If a later prose section follows an interleaved Tables/Figures section, that prose resumes counting. Embedded table rows, headings, image markup and numeric citation groups are excluded. The whole count includes textual content and adds figure_label_words separately. Counts are whitespace conventions, not the target journal's definitive counter.

For the numeric-style helper, use [1], [2,3] or [4–6] citations and one complete numbered reference paragraph per Markdown line under the single final ## References section. The citation content must exactly match references.json. Put no notes, headings or audit text after references. Author-date/footnote styles need a matching checker rather than pretending numeric verification covers them.

## Commands

```text
python scripts/init_review.py --out <project> --title "Title" --field "Field"
python scripts/check_manuscript.py --project <project>
python scripts/build_document.py --source <project>/MANUSCRIPT.md --out <project>/output/Main_Paper --config <project>/project.json
python scripts/build_document.py --source <project>/SUPPORTING_MATERIAL.md --out <project>/output/Supporting_Material --config <project>/project.json
python scripts/audit_pdf.py --pdf <project>/output/Main_Paper.pdf --qa-dir <project>/qa/main --render
```

Discover the runtime first. build_document.py needs python-docx, reportlab and Pillow plus actual Times New Roman regular/bold/italic/bold-italic files; pass --font-dir if needed. audit_pdf.py needs pypdf; pdfplumber is optional for character bounds; --render also needs pdf2image and Poppler, with --poppler-dir where necessary. Use existing host document/PDF tools instead if these are unavailable. Do not install paid services, change unrelated settings or fabricate output as a workaround.

For richer equations, chemical structures or exact publisher templates, use a proper typesetter/document engine. The basic builder rejects raw maths/code fences, embeds bitmap figures and preserves editable masters separately. Inspect both final Word and PDF when both are delivered; basic paired generation does not establish layout equality.

## Visual record

audit_pdf.py always starts visual inspection as pending. Its VISUAL_REVIEW.<hash>.json identifies the final PDF and each page. After opening every page image, record inspected=true and actual status/notes with truthful inspector_type (AI, human or both). Pending pages or a mismatched PDF hash cannot count as completed inspection. Mechanical_status=PASS, renderer success and recorded verification states are not scientific or submission clearance.
