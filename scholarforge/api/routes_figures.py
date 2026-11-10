from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..services.figure_generator import FigureGenerator
from ..core.config import get_active_workspace

router = APIRouter(prefix="/api/figures", tags=["Scientific Figures & Code Runner"])

class ExecutePlotCodeRequest(BaseModel):
    code: str
    output_filename: Optional[str] = "custom_figure.png"
    workspace_path: Optional[str] = None

@router.get("/list")
def list_figures(workspace_path: Optional[str] = None):
    """Returns metadata and preview URLs for all figures in the active workspace."""
    ws = get_active_workspace(workspace_path)
    fg = FigureGenerator(ws)
    templates = fg.get_figure_templates()
    
    figures = []
    # Add PRISMA flowchart
    prisma_path = ws / "05_figures_tables" / "figures" / "prisma_flowchart.svg"
    if prisma_path.exists():
        figures.append({
            "figure_id": "prisma_flowchart",
            "title": "PRISMA 2020 Flow Diagram",
            "filename": "prisma_flowchart.svg",
            "png_url": "/figures/prisma_flowchart.svg",
            "svg_url": "/figures/prisma_flowchart.svg",
            "code": "# Generated deterministically from PRISMA 2020 protocol study counts",
            "status": "active"
        })

    for fig_id, info in templates.items():
        png_path = ws / "05_figures_tables" / "figures" / info["filename"]
        svg_path = ws / "05_figures_tables" / "figures" / info["filename"].replace(".png", ".svg")
        figures.append({
            "figure_id": fig_id,
            "title": info["title"],
            "filename": info["filename"],
            "png_url": f"/figures/{info['filename']}" if png_path.exists() else None,
            "svg_url": f"/figures/{info['filename'].replace('.png', '.svg')}" if svg_path.exists() else None,
            "code": info["code"],
            "status": "active" if png_path.exists() else "not_generated"
        })

    return {"count": len(figures), "figures": figures}

@router.get("/code/{figure_id}")
def get_figure_code(figure_id: str, workspace_path: Optional[str] = None):
    """Retrieves the source Python plotting code for a given figure ID."""
    ws = get_active_workspace(workspace_path)
    fg = FigureGenerator(ws)
    templates = fg.get_figure_templates()

    if figure_id in templates:
        return {"figure_id": figure_id, "code": templates[figure_id]["code"], "title": templates[figure_id]["title"]}
    
    raise HTTPException(status_code=404, detail=f"Figure '{figure_id}' code not found.")

@router.post("/execute-code")
def execute_plot_code(req: ExecutePlotCodeRequest):
    """Executes user-edited Python Matplotlib/Seaborn code and saves the figure at 300 DPI."""
    ws = get_active_workspace(req.workspace_path)
    fg = FigureGenerator(ws)
    res = fg.execute_custom_plot_code(req.code, req.output_filename or "custom_figure.png")
    return res

@router.post("/generate-all")
def generate_all_publication_figures(workspace_path: Optional[str] = None):
    """Generates all 4 standard scientific figures + saves in 05_figures_tables/figures/."""
    ws = get_active_workspace(workspace_path)
    fg = FigureGenerator(ws)
    results = fg.generate_all_figures()
    return {"status": "success", "count": len(results), "figures": results}

