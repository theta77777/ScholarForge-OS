from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .routes_settings import router as settings_router
from .routes_models import router as models_router
from .routes_search import router as search_router
from .routes_workspace import router as workspace_router
from .routes_extraction import router as extraction_router
from .routes_manuscript import router as manuscript_router
from .routes_audit import router as audit_router
from .routes_figures import router as figures_router
from .routes_detector import router as detector_router
from .routes_grounded import router as grounded_router
from .routes_jev import router as jev_router
from .routes_gateway import router as gateway_router
from ..core.config import get_settings, get_active_workspace
from ..core.agent_logs import AgentLogger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = PROJECT_ROOT / "scholarforge" / "static"

app = FastAPI(
    title="ScholarForge OS API",
    description="Backend engine for autonomous, publication-grade scientific review papers.",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(settings_router)
app.include_router(models_router)
app.include_router(search_router)
app.include_router(workspace_router)
app.include_router(extraction_router)
app.include_router(manuscript_router)
app.include_router(audit_router)
app.include_router(figures_router)
app.include_router(detector_router)
app.include_router(grounded_router)
app.include_router(jev_router)
app.include_router(gateway_router)

@app.get("/figures/{filename}")
def serve_dynamic_figure(filename: str):
    """Dynamically serves publication figures from the currently active workspace."""
    ws = get_active_workspace()
    fig_path = ws / "05_figures_tables" / "figures" / filename
    if fig_path.exists():
        media = "image/svg+xml" if filename.endswith(".svg") else "image/png"
        return FileResponse(fig_path, media_type=media)
    raise HTTPException(status_code=404, detail=f"Figure '{filename}' not found.")


@app.get("/source-pdf/{filename}")
def serve_source_pdf(filename: str):
    """Dynamically serves ingested source scholarly PDFs for in-browser citation inspection."""
    ws = get_active_workspace()
    orig_dir = ws / "02_sources" / "originals"
    if orig_dir.exists():
        pdf_path = orig_dir / filename
        if pdf_path.exists():
            return FileResponse(pdf_path, media_type="application/pdf")
        
        if not filename.endswith(".pdf"):
            pdf_path = orig_dir / f"{filename}.pdf"
            if pdf_path.exists():
                return FileResponse(pdf_path, media_type="application/pdf")

        for f in orig_dir.glob("*.pdf"):
            if filename.lower() in f.name.lower():
                return FileResponse(f, media_type="application/pdf")

    raise HTTPException(status_code=404, detail=f"Source PDF '{filename}' not found.")

@app.get("/")
def serve_dashboard():
    """Serves the Developer Coding-Agent HUD Web Dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "ScholarForge OS API is running. Visit /docs for OpenAPI documentation."}

@app.get("/api/agent/logs")
@app.get("/api/logs")
def get_live_agent_logs():
    """Returns streaming telemetry logs for the developer terminal HUD."""
    return {"logs": AgentLogger.get_logs()}

@app.get("/api/pdf/{filename}")
def view_pdf_inline(filename: str):
    """
    Serves the compiled Typst PDF inline for immediate in-browser reading,
    reviewing, and page-by-page scrolling.
    """
    ws = get_active_workspace()
    target = ws / "08_final" / filename
    if target.exists():
        return FileResponse(
            target,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'}
        )
    for f in (ws / "08_final").glob(f"*{filename}*"):
        if f.suffix.lower() == ".pdf":
            return FileResponse(
                f,
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="{f.name}"'}
            )
    raise HTTPException(status_code=404, detail=f"PDF '{filename}' not found.")

@app.get("/api/download/{filename}")
def download_artifact(filename: str):
    """
    1-Click Download Handler:
    Searches active workspace 08_final/, 05_figures_tables/figures/, 03_extraction/, and 06_manuscript/.
    """
    ws = get_active_workspace()
    search_dirs = [
        ws / "08_final",
        ws / "05_figures_tables" / "figures",
        ws / "03_extraction",
        ws / "06_manuscript",
    ]
    
    for d in search_dirs:
        if not d.exists():
            continue
        target = d / filename
        if target.exists():
            return FileResponse(
                target,
                filename=filename,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

    # If exact name not matched, look for wildcard
    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.glob(f"*{filename}*"):
            return FileResponse(
                f,
                filename=f.name,
                headers={"Content-Disposition": f'attachment; filename="{f.name}"'}
            )

    raise HTTPException(status_code=404, detail=f"Artifact '{filename}' not found.")

@app.get("/api/workspace/tree")
def get_workspace_tree():
    """Returns the full 9-directory tree with file sizes and download URLs."""
    ws = get_active_workspace()
    tree = {}
    for d in sorted(ws.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            files = []
            for f in sorted(d.rglob("*.*")):
                if not f.name.startswith("."):
                    rel = f.relative_to(ws)
                    files.append({
                        "name": f.name,
                        "relative_path": str(rel).replace("\\", "/"),
                        "size_bytes": f.stat().st_size,
                        "download_url": f"/api/download/{f.name}"
                    })
            tree[d.name] = files
    return {"workspace": ws.name, "tree": tree}

@app.get("/api/health")
def health_check():
    cfg = get_settings()
    return {
        "status": "online",
        "app": cfg.app_name,
        "version": cfg.version,
        "primary_model": cfg.models.default_workhorse,
        "automated_decisions": cfg.models.enable_automated_decisions
    }
