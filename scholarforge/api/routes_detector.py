from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.ai_plagiarism_detector import AIPlagiarismDetector
from ..core.config import get_active_workspace
from ..core.agent_logs import AgentLogger

router = APIRouter(prefix="/api/detector", tags=["AI & Plagiarism Detector"])

class ScanRequest(BaseModel):
    text: Optional[str] = None
    workspace_path: Optional[str] = None

class HumanizeRequest(BaseModel):
    text: str
    workspace_path: Optional[str] = None

@router.post("/scan")
def scan_content(req: ScanRequest):
    """
    Scans the provided text (or active manuscript.md) for:
    - AI writing tells, burstiness, formulaic transitions, sentence length variance.
    - Verbatim n-gram overlap against local extracted source papers.
    """
    ws = get_active_workspace(req.workspace_path)
    detector = AIPlagiarismDetector(ws)

    text_to_scan = req.text
    if not text_to_scan:
        manuscript_path = ws / "06_manuscript" / "manuscript.md"
        if manuscript_path.exists():
            text_to_scan = manuscript_path.read_text(encoding="utf-8")
        else:
            raise HTTPException(status_code=400, detail="No text provided and 06_manuscript/manuscript.md not found.")

    AgentLogger.log("DETECTOR", f"Scanning {len(text_to_scan.split())} words for AI markers & verbatim overlap...", "info")
    report = detector.scan_text(text_to_scan)
    AgentLogger.log("DETECTOR", f"Scan complete: AI Score: {report['ai_score']}% | Originality: {report['originality_score']}%", "success")
    return report

@router.post("/humanize")
def humanize_content(req: HumanizeRequest):
    """
    Applies humanize-writing rules:
    Eliminates Wikipedia AI tells, formulaic phrases, and buzzwords while strictly
    preserving all empirical data, numbers, p-values, citations, and units.
    """
    ws = get_active_workspace(req.workspace_path)
    detector = AIPlagiarismDetector(ws)

    humanized = detector.humanize_text(req.text)
    AgentLogger.log("HUMANIZER", "Rewrote text adhering to humanize-writing fidelity rules", "success")
    return {
        "status": "success",
        "original_text": req.text,
        "humanized_text": humanized
    }

