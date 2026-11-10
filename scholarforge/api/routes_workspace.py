import os
import subprocess
import hashlib
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..services.workspace_manager import WorkspaceManager
from ..services.pipeline_orchestrator import AutonomousPipelineOrchestrator
from ..services.search_engine import FederatedSearchEngine
from ..core.config import (
    get_settings,
    get_active_workspace,
    list_all_projects,
    set_active_project,
    slugify_title
)
from ..core.database import DatabaseManager
from ..core.agent_logs import AgentLogger

router = APIRouter(prefix="/api/workspace", tags=["Workspace & Project Switcher"])

class CreateWorkspaceRequest(BaseModel):
    title: str
    topic_field: Optional[str] = "Biomedical / Materials Science"
    review_type: str = "systematic"
    target_journal: str = "Nature Reviews"
    run_pipeline: bool = False

class SwitchWorkspaceRequest(BaseModel):
    slug: str

class RunPipelineRequest(BaseModel):
    title: str
    topic_field: Optional[str] = "Biomedical / Materials Science"
    review_type: str = "systematic"
    target_journal: str = "Nature Reviews"
    slug: Optional[str] = None

@router.get("/list")
def list_projects():
    """
    Returns all review projects in the workspace directory with their title,
    review type, word count, phase status, and whether they are active.
    """
    projects = list_all_projects()
    active_slug = ""
    cfg = get_settings()
    if cfg.active_project and any(p["slug"] == cfg.active_project for p in projects):
        active_slug = cfg.active_project
    elif projects:
        active_slug = projects[0]["slug"]
    return {
        "active_slug": active_slug,
        "count": len(projects),
        "projects": projects
    }

@router.post("/switch")
def switch_active_project(req: SwitchWorkspaceRequest):
    """
    Switches the globally active review project.
    """
    cfg = get_settings()
    target_dir = Path(cfg.workspace_dir) / req.slug
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project '{req.slug}' not found.")
    
    set_active_project(req.slug)
    AgentLogger.log("WORKSPACE", f"Switched active project to: {req.slug}", "success")
    return {
        "status": "success",
        "active_slug": req.slug,
        "workspace_path": str(target_dir)
    }

@router.post("/create")
async def create_new_project(req: CreateWorkspaceRequest):
    """
    Initializes a new PhD-grade review paper workspace with the full 9-folder architecture.
    Optionally launches the autonomous pipeline immediately.
    """
    slug = slugify_title(req.title)
    cfg = get_settings()
    target_dir = Path(cfg.workspace_dir) / slug

    mgr = WorkspaceManager(target_dir)
    init_res = mgr.initialize(
        title=req.title,
        review_type=req.review_type,
        target_journal=req.target_journal
    )
    set_active_project(slug)
    AgentLogger.log("WORKSPACE", f"Created new review project '{req.title}' ({slug})", "success")

    pipeline_result = None
    if req.run_pipeline:
        orchestrator = AutonomousPipelineOrchestrator(target_dir)
        pipeline_result = await orchestrator.run_full_pipeline(
            title=req.title,
            topic_field=req.topic_field or "Biomedical / Materials Science",
            review_type=req.review_type,
            target_journal=req.target_journal,
            slug=slug
        )

    return {
        "status": "success",
        "slug": slug,
        "title": req.title,
        "workspace_path": str(target_dir),
        "pipeline_result": pipeline_result
    }

@router.post("/pipeline/run")
async def run_autonomous_pipeline(req: RunPipelineRequest):
    """
    Runs the complete end-to-end autonomous review pipeline:
    Search -> Ingestion -> PICO Extraction -> Figures & Excel -> Synthesis -> Typesetting -> Quality Audit.
    """
    slug = req.slug or slugify_title(req.title)
    cfg = get_settings()
    target_dir = Path(cfg.workspace_dir) / slug

    orchestrator = AutonomousPipelineOrchestrator(target_dir)
    result = await orchestrator.run_full_pipeline(
        title=req.title,
        topic_field=req.topic_field or "Biomedical / Materials Science",
        review_type=req.review_type,
        target_journal=req.target_journal,
        slug=slug
    )
    return result

@router.get("/state")
def get_workspace_state(workspace_path: Optional[str] = None):
    """Retrieves current workspace status, phase, and PRISMA statistics."""
    workspace = get_active_workspace(workspace_path)
    db = DatabaseManager()
    
    state_file = workspace / "00_project" / "STATE.md"
    state_content = state_file.read_text(encoding="utf-8") if state_file.exists() else "Not initialized"
    
    prisma = db.get_prisma_stats(workspace.name)
    
    return {
        "slug": workspace.name,
        "workspace_path": str(workspace),
        "state_content": state_content,
        "prisma_counts": prisma
    }

class KeywordsRequest(BaseModel):
    title: str
    topic_field: Optional[str] = "Open Interdisciplinary Science"

class StageSearchRequest(BaseModel):
    title: str
    topic_field: Optional[str] = "Open Interdisciplinary Science"
    target_total: Optional[int] = 120
    include_academic: Optional[bool] = True
    include_web: Optional[bool] = True
    custom_keywords: Optional[List[str]] = None
    slug: Optional[str] = None

class StageDeduplicateRequest(BaseModel):
    candidates: List[Dict[str, Any]]
    slug: Optional[str] = None

class StageOrganizeRequest(BaseModel):
    candidates: List[Dict[str, Any]]
    topic: str
    slug: Optional[str] = None

class StageDownloadRequest(BaseModel):
    candidates: List[Dict[str, Any]]
    slug: Optional[str] = None

class StageExtractRequest(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None

class StageDraftSectionRequest(BaseModel):
    section_key: str
    title: str
    authors: Optional[str] = "ScholarForge Autonomous Research Consortium"
    user_guidance: Optional[str] = None
    target_journal: Optional[str] = "Nature Reviews"
    slug: Optional[str] = None

class StageCompileRequest(BaseModel):
    title: str
    authors: Optional[str] = "ScholarForge Autonomous Research Consortium"
    target_journal: Optional[str] = "Nature Reviews"
    slug: Optional[str] = None
    user_guidance: Optional[str] = None

class OpenExplorerRequest(BaseModel):
    workspace_path: Optional[str] = None
    subfolder: Optional[str] = None

@router.post("/open-explorer")
def open_in_windows_explorer(req: Optional[OpenExplorerRequest] = None, workspace_path: Optional[str] = None, subfolder: Optional[str] = None):
    """
    Pops open the physical Windows File Explorer on the user's PC to view/add files directly.
    Can open root workspace or specific subfolders (e.g. 02_sources/originals or 08_final).
    """
    ws_param = (req.workspace_path if req and req.workspace_path else workspace_path)
    sub_param = (req.subfolder if req and req.subfolder else subfolder)

    ws = get_active_workspace(ws_param)
    target = (ws / sub_param) if sub_param else ws
    target.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == 'nt':
            os.startfile(str(target))
        else:
            subprocess.Popen(['xdg-open', str(target)])
        AgentLogger.log("EXPLORER", f"Opened folder '{target}' in Windows Explorer.", "success")
        return {"status": "success", "workspace_path": str(target), "target_name": target.name}
    except Exception as e:
        AgentLogger.log("EXPLORER", f"Failed opening Windows Explorer: {e}", "warning")
        return {"status": "error", "message": str(e), "workspace_path": str(target)}

@router.post("/open-originals")
def open_originals_folder(req: Optional[OpenExplorerRequest] = None):
    """Convenience endpoint to immediately open 02_sources/originals in Windows Explorer."""
    ws_param = req.workspace_path if req else None
    return open_in_windows_explorer(workspace_path=ws_param, subfolder="02_sources/originals")

@router.post("/open-final")
def open_final_folder(req: Optional[OpenExplorerRequest] = None):
    """Convenience endpoint to immediately open 08_final in Windows Explorer."""
    ws_param = req.workspace_path if req else None
    return open_in_windows_explorer(workspace_path=ws_param, subfolder="08_final")

@router.get("/tree")
def get_detailed_workspace_tree(workspace_path: Optional[str] = None):
    """
    Returns full recursive file system tree of the 9 project subfolders with file details.
    """
    ws = get_active_workspace(workspace_path)
    tree: Dict[str, List[Dict[str, Any]]] = {}

    for d in sorted(ws.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            files = []
            for f in sorted(d.rglob("*.*")):
                if not f.name.startswith("."):
                    rel = str(f.relative_to(ws)).replace("\\", "/")
                    ext = f.suffix.lower()
                    size_b = f.stat().st_size
                    if size_b < 1024:
                        size_fmt = f"{size_b} B"
                    elif size_b < 1024 * 1024:
                        size_fmt = f"{size_b / 1024:.1f} KB"
                    else:
                        size_fmt = f"{size_b / (1024 * 1024):.1f} MB"
                    
                    is_preview = ext in [".md", ".txt", ".csv", ".json", ".svg", ".py", ".html", ".typ"]
                    files.append({
                        "name": f.name,
                        "relative_path": rel,
                        "size_bytes": size_b,
                        "size_formatted": size_fmt,
                        "extension": ext,
                        "is_previewable": is_preview,
                        "download_url": f"/api/download/{f.name}"
                    })
            tree[d.name] = files

    return {
        "status": "success",
        "workspace_name": ws.name,
        "workspace_path": str(ws),
        "tree": tree
    }

@router.get("/file/preview")
def preview_workspace_file(path: str, workspace_path: Optional[str] = None):
    """
    Returns content of any text/data file in active workspace for instant in-browser inspection.
    """
    ws = get_active_workspace(workspace_path)
    target = (ws / path).resolve()
    if not str(target).startswith(str(ws.resolve())):
        raise HTTPException(status_code=403, detail="Access denied: path outside workspace.")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"File '{path}' not found.")

    ext = target.suffix.lower()
    if ext == ".svg":
        return FileResponse(target, media_type="image/svg+xml")
    elif ext in [".png", ".jpg", ".jpeg"]:
        return FileResponse(target, media_type=f"image/{ext.lstrip('.')}")
    elif ext == ".pdf":
        return FileResponse(target, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{target.name}"'})
    
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return {
            "status": "success",
            "path": path,
            "filename": target.name,
            "extension": ext,
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

@router.post("/file/upload")
async def upload_files_to_workspace(
    files: List[UploadFile] = File(...),
    subfolder: str = Form("02_sources/originals"),
    workspace_path: Optional[str] = None
):
    """
    Universal Drag & Drop file uploader directly into any folder (e.g. 02_sources/originals/).
    Computes SHA-256 for each uploaded file and logs to telemetry.
    """
    ws = get_active_workspace(workspace_path)
    target_dir = (ws / subfolder).resolve()
    if not str(target_dir).startswith(str(ws.resolve())):
        raise HTTPException(status_code=403, detail="Invalid subfolder destination.")
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for f in files:
        safe_name = os.path.basename(f.filename)
        dest = target_dir / safe_name
        content = await f.read()
        dest.write_bytes(content)
        sha256 = hashlib.sha256(content).hexdigest()
        saved_files.append({
            "filename": safe_name,
            "size_bytes": len(content),
            "sha256": sha256,
            "relative_path": f"{subfolder}/{safe_name}"
        })
        AgentLogger.log("UPLOAD", f"Uploaded file saved to {subfolder}/{safe_name} ({len(content):,} bytes)", "success")

    return {
        "status": "success",
        "uploaded_count": len(saved_files),
        "files": saved_files
    }

@router.post("/stage/keywords")
async def stage_generate_keywords(req: KeywordsRequest):
    """Stage 1A: AI generates multi-faceted search keywords, subtopics, and query vectors."""
    strategy = await FederatedSearchEngine.generate_search_strategy(req.title, req.topic_field)
    AgentLogger.log("AI_KEYWORDS", f"Formulated {len(strategy.get('core_keywords', []))} keywords for '{req.title[:40]}...'", "success")
    return {"status": "success", "strategy": strategy}

@router.post("/stage/search")
async def stage_run_search(req: StageSearchRequest):
    """Stage 1B: Universal federated and web search returning 100+ verified candidates."""
    slug = req.slug or slugify_title(req.title)
    set_active_project(slug)
    cfg = get_settings()
    root_dir = Path(cfg.workspace_dir) / slug
    
    orchestrator = AutonomousPipelineOrchestrator(root_dir)
    candidates = await orchestrator.stage_search(
        title=req.title,
        target_total=req.target_total or 120,
        include_academic=req.include_academic if req.include_academic is not None else True,
        include_web=req.include_web if req.include_web is not None else True,
        custom_keywords=req.custom_keywords,
        slug=slug
    )
    return {
        "status": "success",
        "slug": slug,
        "count": len(candidates),
        "candidates": candidates
    }

@router.post("/stage/deduplicate")
def stage_deduplicate(req: StageDeduplicateRequest):
    """Removes duplicate candidate papers across DOIs, URLs, and fuzzy title matching, merging metadata."""
    original_count = len(req.candidates)
    deduped = FederatedSearchEngine.deduplicate_candidates(req.candidates)
    removed_count = original_count - len(deduped)

    cfg = get_settings()
    root_dir = Path(cfg.workspace_dir) / (req.slug or cfg.active_project or "new_paper")
    cand_file = root_dir / "01_search" / "candidates.csv"
    if cand_file.exists():
        try:
            import csv
            fieldnames = ["catalog_id", "citation_key", "type", "source", "title", "authors", "year", "journal", "doi", "relevance_tier", "relevance_score", "relevance_reason", "access_status", "abstract", "pdf_url", "landing_url"]
            with open(cand_file, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                w.writeheader()
                for c in deduped:
                    w.writerow(c)
        except Exception as e:
            AgentLogger.log("DEDUPLICATE", f"Note writing candidates.csv: {e}", "warning")

    AgentLogger.log("DEDUPLICATE", f"Cleaned candidate pool: {original_count} -> {len(deduped)} ({removed_count} duplicates removed)", "success")
    return {
        "status": "success",
        "original_count": original_count,
        "count": len(deduped),
        "removed_count": removed_count,
        "candidates": deduped
    }

@router.post("/stage/organize-candidates")
def stage_organize_candidates(req: StageOrganizeRequest):
    """AI evaluates candidate abstracts, scores relevance (0-100%), and groups by tier (core, supporting, irrelevant)."""
    organized = FederatedSearchEngine.organize_candidates_by_abstract(req.candidates, req.topic)
    core_count = sum(1 for c in organized if c.get("relevance_tier") == "core")
    supporting_count = sum(1 for c in organized if c.get("relevance_tier") == "supporting")
    irrelevant_count = sum(1 for c in organized if c.get("relevance_tier") == "irrelevant")

    cfg = get_settings()
    root_dir = Path(cfg.workspace_dir) / (req.slug or cfg.active_project or "new_paper")
    cand_file = root_dir / "01_search" / "candidates.csv"
    if cand_file.exists():
        try:
            import csv
            fieldnames = ["catalog_id", "citation_key", "type", "source", "title", "authors", "year", "journal", "doi", "relevance_tier", "relevance_score", "relevance_reason", "access_status", "abstract", "pdf_url", "landing_url"]
            with open(cand_file, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                w.writeheader()
                for c in organized:
                    w.writerow(c)
        except Exception as e:
            AgentLogger.log("ORGANIZE", f"Note writing candidates.csv: {e}", "warning")

    AgentLogger.log("ORGANIZE", f"AI abstract screening complete: {core_count} Core, {supporting_count} Supporting, {irrelevant_count} Irrelevant (auto-unselected)", "success")
    return {
        "status": "success",
        "count": len(organized),
        "core_count": core_count,
        "supporting_count": supporting_count,
        "irrelevant_count": irrelevant_count,
        "candidates": organized
    }

@router.get("/subscription-list")
def get_subscription_list(workspace_path: Optional[str] = None):
    """
    Returns the list of papers requiring institutional subscription or manual access
    from 02_sources/subscription_manual_verification_list.json.
    """
    ws = get_active_workspace(workspace_path)
    sub_json = ws / "02_sources" / "subscription_manual_verification_list.json"
    items = []
    if sub_json.exists():
        import json
        try:
            items = json.loads(sub_json.read_text(encoding="utf-8"))
        except Exception:
            items = []
    return {
        "status": "success",
        "count": len(items),
        "items": items,
        "csv_available": (ws / "02_sources" / "subscription_manual_verification_list.csv").exists()
    }

@router.get("/download-subscription-csv")
def download_subscription_csv(workspace_path: Optional[str] = None):
    """Downloads the CSV of papers requiring manual institutional access."""
    ws = get_active_workspace(workspace_path)
    sub_csv = ws / "02_sources" / "subscription_manual_verification_list.csv"
    if not sub_csv.exists():
        raise HTTPException(status_code=404, detail="Subscription verification list CSV not found.")
    return FileResponse(
        path=str(sub_csv),
        filename=f"{ws.name}_subscription_manual_verification_list.csv",
        media_type="text/csv"
    )

@router.get("/sources-inventory")
def get_sources_inventory(workspace_path: Optional[str] = None):
    """Returns all files currently present in 02_sources/originals with file sizes and relative paths."""
    ws = get_active_workspace(workspace_path)
    orig_dir = ws / "02_sources" / "originals"
    orig_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for f in orig_dir.iterdir():
        if f.is_file():
            files.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "extension": f.suffix.lower(),
                "relative_path": f"02_sources/originals/{f.name}"
            })
    return {
        "count": len(files),
        "files": files,
        "folder_path": str(orig_dir)
    }

@router.post("/stage/download")
async def stage_run_download(req: StageDownloadRequest):
    """Stage 2: Mass downloads selected candidate items, returning acquired and paywalled lists."""
    if req.slug:
        set_active_project(req.slug)
    cfg = get_settings()
    root_dir = Path(cfg.workspace_dir) / (req.slug or cfg.active_project or "new_paper")
    orchestrator = AutonomousPipelineOrchestrator(root_dir)
    result = await orchestrator.stage_download(req.candidates, slug=req.slug)
    return {
        "status": "success",
        "slug": root_dir.name,
        **result
    }

@router.post("/stage/extract")
async def stage_run_extract(req: StageExtractRequest):
    """Stage 3: Layout-aware deep extraction matrix across all downloaded and uploaded files."""
    if req.slug:
        set_active_project(req.slug)
    cfg = get_settings()
    root_dir = Path(cfg.workspace_dir) / (req.slug or cfg.active_project or "new_paper")
    orchestrator = AutonomousPipelineOrchestrator(root_dir)
    result = await orchestrator.stage_extract(title=req.title, slug=req.slug)
    return result

@router.post("/stage/draft-section")
async def stage_draft_section(req: StageDraftSectionRequest):
    """Stage 4A: Drafts section with interactive human steering prompt."""
    if req.slug:
        set_active_project(req.slug)
    cfg = get_settings()
    root_dir = Path(cfg.workspace_dir) / (req.slug or cfg.active_project or "new_paper")
    orchestrator = AutonomousPipelineOrchestrator(root_dir)
    result = await orchestrator.stage_draft_section(
        section_key=req.section_key,
        title=req.title,
        authors=req.authors or "ScholarForge Autonomous Research Consortium",
        user_guidance=req.user_guidance,
        target_journal=req.target_journal or "Nature Reviews",
        slug=req.slug
    )
    return result

@router.post("/stage/compile")
async def stage_compile_final(req: StageCompileRequest):
    """Stage 4B: Compiles final Word .docx and Typst .pdf with quality audit."""
    if req.slug:
        set_active_project(req.slug)
    cfg = get_settings()
    root_dir = Path(cfg.workspace_dir) / (req.slug or cfg.active_project or "new_paper")
    orchestrator = AutonomousPipelineOrchestrator(root_dir)
    result = await orchestrator.stage_compile(
        title=req.title,
        authors=req.authors or "ScholarForge Autonomous Research Consortium",
        target_journal=req.target_journal or "Nature Reviews",
        slug=req.slug,
        user_guidance=req.user_guidance
    )
    return result
