from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..core.config import get_settings, save_settings, get_active_workspace
from ..services.jev_router import JEVDecisionEngine

router = APIRouter(prefix="/api/jev", tags=["JEV Decision Engine"])

class TitleRequest(BaseModel):
    title: str
    description: Optional[str] = ""

class ProfileSelectRequest(BaseModel):
    profile: str

class JevToggleRequest(BaseModel):
    enabled: bool

@router.get("/profiles")
def get_all_profiles():
    """Returns all 8 JEV profiles with metadata, target completion times, and execution tiers."""
    return {
        "profiles": JEVDecisionEngine.PROFILES,
        "default": "auto"
    }

@router.get("/active")
def get_active_jev_state():
    """Returns the currently active JEV profile, domain, and API roster for the active project."""
    cfg = get_settings()
    workspace = get_active_workspace()
    
    # Try reading scope from active project
    scope_file = workspace / "00_project" / "scope.json"
    title = cfg.active_project.replace("_", " ").title()
    desc = ""
    
    if scope_file.exists():
        try:
            import json
            with open(scope_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                title = data.get("title", title)
                desc = data.get("description", "")
        except Exception:
            pass

    resolved = JEVDecisionEngine.resolve_active_apis(title, desc)
    return {
        "active_project": cfg.active_project,
        "configured_profile": getattr(cfg, "jev_profile", "auto"),
        **resolved
    }

@router.post("/classify")
def classify_scope(req: TitleRequest):
    """
    Evaluates research title/abstract and provides instant JEV recommendations:
    predicted domain, best profile, and recommended cloud API toolset.
    """
    domain = JEVDecisionEngine.classify_domain(req.title, req.description)
    resolved = JEVDecisionEngine.resolve_active_apis(req.title, req.description)
    return {
        "input_title": req.title,
        "predicted_domain": domain,
        "recommended_profile": resolved["selected_profile"],
        "profile_meta": resolved["profile_meta"],
        "recommended_apis": resolved["apis"]
    }

@router.post("/select")
def select_profile(req: ProfileSelectRequest):
    """Sets the active JEV execution profile in system settings."""
    if req.profile != "auto" and req.profile not in JEVDecisionEngine.PROFILES:
        raise HTTPException(status_code=400, detail=f"Invalid profile '{req.profile}'")
    
    cfg = get_settings()
    cfg.jev_profile = req.profile
    if req.profile == "manual":
        cfg.enable_jev = False
    else:
        cfg.enable_jev = True
    save_settings(cfg)
    return {
        "status": "success",
        "message": f"JEV profile updated to '{req.profile}'",
        "profile": req.profile
    }

@router.post("/toggle")
def toggle_jev(req: JevToggleRequest):
    """Enables or completely disables the JEV autonomous decision engine."""
    cfg = get_settings()
    cfg.enable_jev = req.enabled
    if not req.enabled:
        cfg.jev_profile = "manual"
    save_settings(cfg)
    return {
        "status": "success",
        "enable_jev": cfg.enable_jev,
        "message": "JEV Decision Engine turned ON" if req.enabled else "JEV Decision Engine turned OFF (Direct Manual Mode Active)"
    }

