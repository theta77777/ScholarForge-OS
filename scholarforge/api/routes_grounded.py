from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.grounded_ai import GroundedAIService
from ..core.config import get_active_workspace
from ..core.agent_logs import AgentLogger

router = APIRouter(prefix="/api/grounded", tags=["Grounded AI Studio"])

class GroundedQueryRequest(BaseModel):
    selected_files: List[str]
    prompt: str
    output_format: str = "json"  # "json", "markdown_src", "pico_table"
    workspace_path: Optional[str] = None

@router.get("/files")
def get_selectable_files(workspace_path: Optional[str] = None):
    """
    Returns the indexed list of all readable project documents,
    categorized for the interactive Document & Context Selector.
    """
    ws = get_active_workspace(workspace_path)
    service = GroundedAIService(ws)
    files = service.get_selectable_files()
    return {
        "workspace": ws.name,
        "count": len(files),
        "files": files
    }

@router.post("/query")
async def execute_grounded_query(req: GroundedQueryRequest):
    """
    Executes an evidentiary grounded AI prompt using ONLY the user-selected documents.
    Returns response in JSON, raw Markdown/SRC, or structured PICO table format.
    """
    if not req.selected_files:
        raise HTTPException(status_code=400, detail="Please select at least one document or folder for grounding.")
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    ws = get_active_workspace(req.workspace_path)
    service = GroundedAIService(ws)

    result = await service.execute_grounded_synthesis(
        selected_rel_paths=req.selected_files,
        prompt=req.prompt,
        output_format=req.output_format
    )
    return result

