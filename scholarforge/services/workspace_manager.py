import csv
import json
from pathlib import Path
from typing import Dict, Any, Optional

class WorkspaceManager:
    """
    Manages the 9-directory PhD-grade review workspace and STATE.md machine.
    Directly adheres to the file contracts in review-paper-suite.
    """
    FOLDERS = [
        "00_project",
        "01_search",
        "01_search/catalog",
        "02_sources",
        "02_sources/originals",
        "03_extraction",
        "03_extraction/text",
        "03_extraction/records",
        "04_analysis",
        "04_analysis/code",
        "04_analysis/data",
        "05_figures_tables",
        "05_figures_tables/figures",
        "05_figures_tables/tables",
        "06_manuscript",
        "06_manuscript/drafts",
        "07_quality",
        "07_quality/checks",
        "08_final",
        "08_final/superseded"
    ]

    def __init__(self, root: Path):
        self.root = root

    def initialize(self, title: str, review_type: str = "systematic", target_journal: str = "Nature Reviews") -> Dict[str, Any]:
        """Creates the full workspace directory tree and core state files."""
        self.root.mkdir(parents=True, exist_ok=True)
        
        for sub in self.FOLDERS:
            (self.root / sub).mkdir(parents=True, exist_ok=True)

        # 1. 00_project/project_brief.md
        brief_path = self.root / "00_project" / "project_brief.md"
        if not brief_path.exists():
            brief_content = f"""# Project Brief: {title}

- **Review Type**: {review_type}
- **Target Journal**: {target_journal}
- **Status**: Initialized
- **Automated Decisions**: Configurable in Settings (Default: Human-in-the-Loop)
- **Primary Model**: Gemini 3.8 Flash High/Medium with Google Search Grounding
- **External Models**: MCP Bridge (Astra, Sol 6.1, ChatGPT) - Zero API Token Cost
"""
            brief_path.write_text(brief_content, encoding="utf-8")

        # 2. 00_project/STATE.md
        state_path = self.root / "00_project" / "STATE.md"
        if not state_path.exists():
            state_content = f"""# Review Paper State Tracker

- **Current Phase**: 0 (Intake & Scope)
- **Active Task**: Ready for Phase 1 Search
- **Last Updated**: Workspace initialized
- **Checkpoint Status**:
  - [x] Phase 0: Intake, Scope & Workspace Init
  - [ ] Phase 1: Federated Search & Literature Catalog
  - [ ] Phase 2: PDF Ingestion & Source Inventory
  - [ ] Phase 3: Extraction Matrix & Claim Ledger
  - [ ] Phase 4: Synthesis & Section Drafting
  - [ ] Phase 5: Quality Audit & Multi-Format Typeset
"""
            state_path.write_text(state_content, encoding="utf-8")

        # 3. 00_project/decision_log.md
        decision_path = self.root / "00_project" / "decision_log.md"
        if not decision_path.exists():
            decision_path.write_text("# Decision Log\n\n| Timestamp | Step | Maker | Decision | Rationale |\n|---|---|---|---|---|\n", encoding="utf-8")

        # 4. 03_extraction/claims.csv (The Claim Ledger)
        claims_path = self.root / "03_extraction" / "claims.csv"
        if not claims_path.exists():
            with open(claims_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "claim_id", "claim", "claim_type", "citation_keys", 
                    "locator", "support_level", "caveats", "manuscript_section", "status"
                ])

        # 5. 03_extraction/evidence_matrix.csv
        matrix_path = self.root / "03_extraction" / "evidence_matrix.csv"
        if not matrix_path.exists():
            with open(matrix_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "catalog_id", "citation_key", "design", "population_or_system",
                    "n_or_scale", "exposure_or_intervention", "outcome_or_measure",
                    "key_result", "direction", "limitations", "appraisal_rating"
                ])

        # 6. 02_sources/source_inventory.csv
        inv_path = self.root / "02_sources" / "source_inventory.csv"
        if not inv_path.exists():
            with open(inv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "catalog_id", "filename", "sha256", "access_level", 
                    "pages", "extraction_status", "notes"
                ])

        return {
            "status": "ready",
            "workspace_path": str(self.root),
            "title": title,
            "review_type": review_type
        }

