# ScholarForge OS 🎓🔬
### Autonomous PhD-Grade Scientific Review Paper Engine & Desktop Research Workbench

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Typst: 0.14.9](https://img.shields.io/badge/Typst-0.14.9-orange.svg)](https://typst.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern_Async_Backend-teal.svg)](https://fastapi.tiangolo.com)
[![PRISMA 2020 Compliant](https://img.shields.io/badge/Protocol-PRISMA_2020-emerald.svg)](https://www.prisma-statement.org/)

**ScholarForge OS** is an end-to-end, local-first autonomous research platform and desktop operating system designed to produce publication-grade scientific review papers (systematic, scoping, narrative, critical) across any scientific or engineering inquiry from scratch.

Unlike superficial AI text wrappers or single-pass summary tools, ScholarForge OS implements a rigorous **9-directory scientific review pipeline** grounded in verbatim empirical extractions, Primary Citation Isolation, 300 DPI vector diagrams, Booktabs tables, live DOI hyperlinks, and a multi-perspective pre-submission audit.

---

## 🏛️ Architecture: The 9-Directory Pipeline

Every research project initialized in ScholarForge OS generates an isolated, verifiable workspace structure:

```
workspace/<project_slug>/
├── 00_project/             # Project briefs, state machine, and journal calibration
├── 01_search/              # Federated search queries, catalog, and screened candidate sets
├── 02_sources/             # Acquired local PDFs/text and institutional subscription lists
│   └── originals/          # Full-text research papers saved locally to disk
├── 03_extraction/          # Layout-aware extraction records, PICO matrix, and claims ledger
│   ├── records/            # Per-paper individual markdown extraction files
│   ├── text/               # Raw layout-extracted full text
│   ├── evidence_matrix.csv # Consolidated Cochrane/PICO matrix across all studies
│   └── claims.csv          # Verifiable Primary Claims Ledger with exact source locators
├── 04_evidence/            # Synthesis plans, effect trajectory clusters, and risk of bias
├── 05_figures_tables/      # Dynamic 300 DPI publication figures & PRISMA 2020 flowchart
│   └── figures/            # Vector SVG and high-resolution PNG exports
├── 06_manuscript/          # Canonical Markdown draft, structured sections, and BibTeX
├── 07_quality/             # 7-perspective pre-submission quality audit reports
└── 08_final/               # Typeset camera-ready deliverables (Word, Typst PDF, Excel)
    ├── <slug>.docx         # Microsoft Word with Booktabs Table 1 & active DOI links
    ├── <slug>_typst.pdf    # Vector Typst PDF (2-column Nature/IEEE layout)
    ├── <slug>_latex.zip    # Overleaf-ready LaTeX bundle with BibTeX references
    └── review_evidence_matrix.xlsx # Styled multi-tab Excel evidence workbook
```

---

## ⚡ Key Features (1 through 20)

### 🔍 Discovery & Acquisition (Features 1–8)
1. **Federated Multi-Database Search**: Parallel querying across OpenAlex (>250M records), Crossref DOI registry, Semantic Scholar, PubMed/MEDLINE, arXiv, and DuckDuckGo for broad web literature.
2. **Dynamic Academic Keyword & Concept Formulation**: Multi-word compound academic entities without word-splitting or artificial domain constraints.
3. **Conversational Query Sanitizer**: Automatically cleans user inquiries into scholarly titles.
4. **Intelligent Deduplication**: Cross-matches DOIs, normalized URLs, and Levenshtein title similarity.
5. **Uncapped Concurrent Mass Downloader**: Races working open-access and repository endpoints to save real full-text PDFs locally into `02_sources/originals/`.
6. **Institutional Subscription Verification List**: Separates paywalled or institutional-access articles into a dedicated tracking list with direct publisher and repository links, exported to CSV/JSON.
7. **AI-Assisted Abstract Screening**: Evaluates abstracts against inquiry scope to categorize candidates into Core, Supporting, and Irrelevant tiers.
8. **Universal Drag-and-Drop Local Ingestion**: Drop external PDFs, Word `.docx`, or text files directly into the active library.

### 🔬 Evidence Extraction & Synthesis (Features 9–13)
9. **Verifiable Primary Claims Ledger**: Relational schema assigning unique identifiers (`CLM_C001_01`) to empirical observations with exact source locators (e.g. `Page 4, Results`), enforcing Primary Citation Isolation.
10. **300 DPI Publication-Grade Vector Figures**: Dynamically writes and executes bespoke Matplotlib visualization code derived directly from the project's evidence matrix and manuscript data.
11. **Styled Multi-Tab Excel Workbook**: Compiles `review_evidence_matrix.xlsx` with zebra striping, dark navy headers, auto-fit columns, PICO analysis, and full claims ledger.
12. **Full-Length Thematic Manuscript Synthesizer**: Produces a comprehensive 5-section scholarly manuscript using Gemini 3.8 Flash structured JSON reasoning with automatic fallback cascades.
13. **Human-in-the-Loop Steering Directives**: Custom user prompts inject top-priority focus constraints into the drafting and thematic synthesis engine.

### 📑 Typesetting & Quality Assurance (Features 14–20)
14. **Camera-Ready Word Document (.docx) Typesetter**: Implements authentic Booktabs 3-line borders for Table 1, embeds 300 DPI figures with Word SEQ-field captions, and builds clickable citation hyperlinks.
15. **Instant Typst Vector PDF Compiler**: Compiles 2-column vector PDFs via Typst 0.14.9 with sanitized math delimiters and native font typography.
16. **Deterministic PRISMA 2020 SVG Flowchart**: Generates publication-standard PRISMA flowcharts calculated from screening protocol study counts.
17. **7-Perspective Pre-Submission Quality Auditor**: Audits drafts across 7 analytical lenses (Editorial, Critical Reviewer, Citations, Evidence Grounding, Methodology, Figures, and Typesetting).
18. **In-Browser Citation Inspector**: Clicking any in-text citation pill `[key]` opens a side drawer displaying verbatim findings, confidence scores, risk of bias, and embedded PDF preview.
19. **Desktop Windows File Explorer Integration**: Direct buttons trigger native `os.startfile` to open `02_sources/originals/` and `08_final/` directly on the user's desktop.
20. **JEV Decision Engine & BYOK Vault**: Classifies inquiry domains, vectors to optimal endpoints, and securely manages API credentials with zero OpenAI API billing.

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/theta77777/scholarforge-os.git
cd scholarforge-os
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Optional: If `typst` is needed for vector PDF compilation: `pip install typst`)*

### 3. Configure Credentials (.env)
Copy the example environment file and add your `GEMINI_API_KEY`:
```bash
cp .env.example .env
```
*(Your `.env` file is gitignored and will never be committed to public repositories).*

### 4. Launch ScholarForge OS

#### Option A: Native Desktop Application (Electron)
Launch as a standalone native desktop research workbench:
```bash
npm start
# Or double-click launch_desktop.bat on Windows
```
The Electron runner automatically manages the local Python server lifecycle and opens the studio in a dedicated desktop window.

#### Option B: Web Browser Mode
```bash
python run_server.py
```
Open your browser at **`http://localhost:8008`** to access the research dashboard.

---

## 📋 Recommended Workflow

1. **Step 1: Inquiry Formulation** — Enter any research title or question. Choose *Full Title* mode or generate *Multi-Word Academic Concepts*.
2. **Step 2: Candidate Screening & Acquisition** — Run federated search, review deduplicated items, and click **Download All Selected Literature**.
3. **Step 3: Deep Evidence Extraction** — Run the layout-aware extraction engine to populate the PICO Evidence Matrix and Verifiable Claims Ledger.
4. **Step 4: Steering & Compilation** — Provide custom steering prompts (e.g. *Focus on interfacial charge transfer resistance*) and click **Draft Manuscript & Compile Word/PDF**.
5. **Step 5: Review & Audit** — Inspect the compiled Word `.docx`, Typst `.pdf`, multi-tab Excel `.xlsx`, and review the 7-perspective Quality Audit report.

---

## 🛡️ License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

