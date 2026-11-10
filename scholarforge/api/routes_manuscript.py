from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..services.manuscript_synthesizer import ManuscriptSynthesizer
from ..services.document_builder import DocumentBuilder
from ..core.config import get_settings, get_active_workspace
from ..core.agent_logs import AgentLogger
import re
import csv

router = APIRouter(prefix="/api/manuscript", tags=["Manuscript & Typesetting"])

class DraftManuscriptRequest(BaseModel):
    title: str
    authors: str = "Author, A.; Co-Author, B."
    target_journal: str = "Nature Reviews"
    slug: str = "review_manuscript"
    workspace_path: Optional[str] = None

class SaveManuscriptRequest(BaseModel):
    content: str
    slug: Optional[str] = None
    workspace_path: Optional[str] = None
    recompile: bool = True

@router.post("/draft")
async def generate_manuscript(req: DraftManuscriptRequest):
    """
    Synthesizes the literature review paper:
    - Generates 06_manuscript/manuscript.md
    - Builds Camera-Ready Word .docx
    - Compiles Typst PDF
    - Creates Overleaf-ready LaTeX .zip
    - Generates PRISMA 2020 Vector SVG Flowchart
    """
    workspace = get_active_workspace(req.workspace_path)
    synthesizer = ManuscriptSynthesizer(workspace)

    result = await synthesizer.draft_manuscript(
        title=req.title,
        authors=req.authors,
        target_journal=req.target_journal,
        slug=req.slug
    )
    return result

@router.get("/content")
def get_manuscript_content(workspace_path: Optional[str] = None):
    """Returns the current canonical Markdown manuscript."""
    workspace = get_active_workspace(workspace_path)
    md_file = workspace / "06_manuscript" / "manuscript.md"
    
    if not md_file.exists():
        return {"content": "", "status": "not_drafted"}

    return {"content": md_file.read_text(encoding="utf-8"), "status": "available"}

@router.get("/artifacts")
def list_publication_artifacts(workspace_path: Optional[str] = None):
    """Lists compiled Word .docx, Typst PDF, LaTeX .zip, and PRISMA diagrams."""
    workspace = get_active_workspace(workspace_path)
    final_dir = workspace / "08_final"
    figures_dir = workspace / "05_figures_tables" / "figures"

    artifacts = []
    if final_dir.exists():
        for f in final_dir.glob("*.*"):
            artifacts.append({
                "type": f.suffix.lstrip(".").upper(),
                "filename": f.name,
                "filepath": str(f),
                "size_bytes": f.stat().st_size
            })

    if figures_dir.exists():
        for f in figures_dir.glob("*.svg"):
            artifacts.append({
                "type": "SVG_DIAGRAM",
                "filename": f.name,
                "filepath": str(f),
                "size_bytes": f.stat().st_size
            })

    return {"artifacts": artifacts}

@router.post("/save")
async def save_manuscript_and_recompile(req: SaveManuscriptRequest):
    """
    Saves manually edited Markdown manuscript and automatically recompiles
    Word .docx, Typst .pdf, and LaTeX .zip in real time.
    """
    workspace = get_active_workspace(req.workspace_path)
    md_file = workspace / "06_manuscript" / "manuscript.md"
    md_file.write_text(req.content, encoding="utf-8")
    
    word_count = len(req.content.split())
    AgentLogger.log("EDITOR", f"Manual edits saved to manuscript.md ({word_count:,} words).", "info")

    if not req.recompile:
        return {"status": "saved", "word_count": word_count}

    # Parse metadata and sections for recompilation
    lines = req.content.splitlines()
    title = "Systematic Review Manuscript"
    authors = "ScholarForge Investigator"
    abstract = ""
    sections = []
    references = []

    current_heading = None
    current_body = []
    in_abstract = False
    in_refs = False

    for line in lines:
        if line.startswith("# ") and not current_heading:
            title = line.replace("# ", "").strip()
        elif line.startswith("**Authors**:"):
            authors = line.replace("**Authors**:", "").strip()
        elif line.startswith("## Abstract"):
            in_abstract = True
            in_refs = False
        elif line.startswith("## References"):
            if current_heading:
                sections.append({"heading": current_heading, "body": "\n".join(current_body).strip()})
                current_heading = None
                current_body = []
            in_refs = True
            in_abstract = False
        elif line.startswith("## ") and not in_refs:
            if in_abstract:
                abstract = "\n".join(current_body).strip()
                in_abstract = False
                current_body = []
            elif current_heading:
                sections.append({"heading": current_heading, "body": "\n".join(current_body).strip()})
                current_body = []
            current_heading = line.replace("## ", "").strip()
        else:
            if in_refs:
                if line.strip().startswith("- "):
                    references.append(line.strip()[2:])
            else:
                current_body.append(line)

    if in_abstract and current_body:
        abstract = "\n".join(current_body).strip()
    elif current_heading and current_body:
        sections.append({"heading": current_heading, "body": "\n".join(current_body).strip()})

    # Read evidence matrix
    matrix_rows = []
    mat_file = workspace / "03_extraction" / "evidence_matrix.csv"
    if mat_file.exists():
        with open(mat_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            matrix_rows = list(reader)

    # Recompile with DocumentBuilder
    slug = req.slug or workspace.name or "review_manuscript"
    builder = DocumentBuilder(workspace)
    
    docx_path = builder.build_docx(
        title=title,
        authors=authors,
        abstract=abstract,
        sections=sections,
        references=references,
        matrix_rows=matrix_rows,
        slug=slug
    )

    typst_path = builder.build_typst_pdf(
        title=title,
        authors=authors,
        abstract=abstract,
        sections=sections,
        references=references,
        matrix_rows=matrix_rows,
        slug=slug
    )

    bib_entries = [
        f"@article{{{r.get('citation_key')},\n  title={{{r.get('title', r.get('citation_key'))}}},\n  author={{{r.get('authors', 'Unknown')}}},\n  year={{2026}}\n}}"
        for r in matrix_rows if r.get('citation_key')
    ]
    latex_path = builder.build_latex_bundle(
        title=title,
        authors=authors,
        abstract=abstract,
        sections=sections,
        bib_entries=bib_entries,
        matrix_rows=matrix_rows,
        slug=slug
    )

    AgentLogger.log("TYPESETTER", f"Recompiled all formats: Word ({docx_path.stat().st_size:,} B), Typst PDF ({typst_path.stat().st_size:,} B), LaTeX ({latex_path.stat().st_size:,} B).", "success")

    return {
        "status": "recompiled",
        "word_count": word_count,
        "docx_filename": docx_path.name,
        "typst_filename": typst_path.name,
        "latex_filename": latex_path.name,
        "docx_url": f"/api/download/{docx_path.name}",
        "typst_url": f"/api/download/{typst_path.name}",
        "latex_url": f"/api/download/{latex_path.name}"
    }

@router.get("/export/docx")
def export_docx(slug: Optional[str] = None, workspace_path: Optional[str] = None):
    """Downloads the compiled Microsoft Word .docx manuscript."""
    cfg = get_settings()
    if slug:
        ws = Path(cfg.workspace_dir) / slug
    else:
        ws = get_active_workspace(workspace_path)
    final_dir = ws / "08_final"
    if final_dir.exists():
        for f in final_dir.glob("*.docx"):
            return FileResponse(
                f,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=f.name,
                headers={"Content-Disposition": f'attachment; filename="{f.name}"'}
            )
    raise HTTPException(status_code=404, detail="Word document (.docx) not found for this review.")

@router.get("/export/typst")
def export_typst_pdf(slug: Optional[str] = None, workspace_path: Optional[str] = None):
    """Downloads or previews the compiled Typst PDF manuscript."""
    cfg = get_settings()
    if slug:
        ws = Path(cfg.workspace_dir) / slug
    else:
        ws = get_active_workspace(workspace_path)
    final_dir = ws / "08_final"
    if final_dir.exists():
        for f in final_dir.glob("*.pdf"):
            return FileResponse(
                f,
                media_type="application/pdf",
                filename=f.name,
                headers={"Content-Disposition": f'inline; filename="{f.name}"'}
            )
    raise HTTPException(status_code=404, detail="Typst publication PDF not found for this review.")

@router.get("/export/latex")
def export_latex_zip(slug: Optional[str] = None, workspace_path: Optional[str] = None):
    """Downloads the Overleaf-ready LaTeX and BibTeX ZIP archive."""
    cfg = get_settings()
    if slug:
        ws = Path(cfg.workspace_dir) / slug
    else:
        ws = get_active_workspace(workspace_path)
    final_dir = ws / "08_final"
    if final_dir.exists():
        for f in final_dir.glob("*.zip"):
            return FileResponse(
                f,
                media_type="application/zip",
                filename=f.name,
                headers={"Content-Disposition": f'attachment; filename="{f.name}"'}
            )
    raise HTTPException(status_code=404, detail="LaTeX & BibTeX zip bundle not found for this review.")


