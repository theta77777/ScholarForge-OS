import csv
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from ..services.quality_auditor import QualityAuditor
from ..services.voice_engine import VoiceEngine
from ..core.config import get_settings, get_active_workspace

router = APIRouter(prefix="/api/audit", tags=["Quality Audit & Voice"])

class AuditRequest(BaseModel):
    slug: str = "review_manuscript"
    workspace_path: Optional[str] = None

@router.post("/run")
async def run_quality_audit(req: AuditRequest):
    """
    Runs the 5-Perspective Quality Audit Arena:
    - Subject-Matter Researcher pass
    - Methodology Specialist pass
    - Citation & Integrity pass (checking ghost citations & DOI validity)
    - Critical Reviewer pass (hedging & over-generalization)
    - Editorial pass (scanning banned AI clichés)
    """
    workspace = get_active_workspace(req.workspace_path)
    auditor = QualityAuditor(workspace)
    
    result = await auditor.run_full_audit(slug=req.slug)
    return result

@router.get("/report")
def get_quality_report(workspace_path: Optional[str] = None):
    """Reads the generated 07_quality/quality_report.md."""
    workspace = get_active_workspace(workspace_path)
    report_file = workspace / "07_quality" / "quality_report.md"

    if not report_file.exists():
        return {"report": "No audit has been run yet.", "status": "pending"}

    return {"report": report_file.read_text(encoding="utf-8"), "status": "completed"}

@router.get("/issues")
def get_issues_log(workspace_path: Optional[str] = None):
    """Reads 07_quality/issues_log.csv."""
    workspace = get_active_workspace(workspace_path)
    issues_file = workspace / "07_quality" / "issues_log.csv"

    if not issues_file.exists():
        return {"issues": []}

    issues = []
    with open(issues_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            issues.append(r)

    return {"count": len(issues), "issues": issues}

@router.post("/voice/process")
async def process_voice_dictation(audio: UploadFile = File(...)):
    """
    Processes audio input (dictation or voice-to-edit command).
    """
    engine = VoiceEngine()
    temp_path = Path("temp_audio.wav")
    
    try:
        content = await audio.read()
        temp_path.write_bytes(content)
        result = await engine.transcribe_and_interpret(temp_path)
        return result
    finally:
        if temp_path.exists():
            temp_path.unlink()

