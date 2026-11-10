import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# Load local .env file automatically
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv()
except ImportError:
    pass

class ModelSettings(BaseModel):
    default_workhorse: str = "gemini-3.8-flash"
    flash_thinking_budget: str = "high"  # "high", "medium", "off"
    enable_google_search_grounding: bool = True
    
    # Strictly zero OpenAI API billing - use MCP only
    use_openai_api_key: bool = False
    openai_api_key: str = ""
    
    # MCP Connection endpoints
    mcp_enabled: bool = True
    mcp_servers: Dict[str, Any] = Field(default_factory=lambda: {
        "chatgpt_desktop": {"enabled": True, "transport": "stdio", "command": "npx -y @modelcontextprotocol/server-everything"},
        "local_astra": {"enabled": False, "transport": "sse", "url": "http://localhost:8001/sse"},
        "local_sol_6_1": {"enabled": False, "transport": "sse", "url": "http://localhost:8002/sse"}
    })
    
    # Decision Engine: CodeIV alternative
    enable_automated_decisions: bool = False  # False by default (Human-in-the-Loop)
    codeiv_api_url: str = "https://api.codeiv.com/v1"
    codeiv_api_key: str = ""
    
    # Voice Dictation
    voice_mode: str = "google_speech"  # "google_speech", "local_whisper", "gemini_audio"
    local_whisper_model: str = "small.en"

class ApiVaultSettings(BaseModel):
    """Bring-Your-Own-Key (BYOK) Vault for optional commercial/registered APIs."""
    scite_api_key: str = ""
    copyleaks_api_key: str = ""
    gptzero_api_key: str = ""
    deepl_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    cerebras_api_key: str = ""
    serpapi_key: str = ""
    materials_project_key: str = ""
    ncbi_api_key: str = ""
    core_api_key: str = ""
    zenodo_token: str = ""

class ScholarForgeConfig(BaseModel):
    app_name: str = "ScholarForge OS"
    version: str = "2.2.0"
    gemini_api_key: str = ""
    target_journal_preset: str = "nature_reviews"
    workspace_dir: str = str(PROJECT_ROOT / "workspace")
    active_project: str = ""
    enable_jev: bool = True
    jev_profile: str = "auto"
    jev_domain: str = "biomedical"
    api_vault: ApiVaultSettings = Field(default_factory=ApiVaultSettings)
    api_overrides: Dict[str, bool] = Field(default_factory=dict)
    models: ModelSettings = Field(default_factory=ModelSettings)

def get_settings() -> ScholarForgeConfig:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Read API keys and preferences from environment / .env
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    
    if not SETTINGS_FILE.exists():
        cfg = ScholarForgeConfig(gemini_api_key=gemini_key)
        save_settings(cfg)
        return cfg
    
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = ScholarForgeConfig(**data)
        
        # Prefer environment variable if present, or fill if empty
        if gemini_key:
            cfg.gemini_api_key = gemini_key

        # Sync API vault keys from environment / .env
        vault_mapping = [
            ("NCBI_API_KEY", "ncbi_api_key"),
            ("CORE_API_KEY", "core_api_key"),
            ("SERPAPI_KEY", "serpapi_key"),
            ("SCITE_API_KEY", "scite_api_key"),
            ("GROQ_API_KEY", "groq_api_key"),
            ("OPENROUTER_API_KEY", "openrouter_api_key"),
            ("CEREBRAS_API_KEY", "cerebras_api_key"),
            ("DEEPL_API_KEY", "deepl_api_key"),
            ("ZENODO_TOKEN", "zenodo_token"),
            ("MATERIALS_PROJECT_KEY", "materials_project_key"),
        ]
        for env_k, vault_attr in vault_mapping:
            val = os.environ.get(env_k)
            if val:
                setattr(cfg.api_vault, vault_attr, val)

        openai_k = os.environ.get("OPENAI_API_KEY")
        if openai_k:
            cfg.models.openai_api_key = openai_k

        default_workhorse = os.environ.get("DEFAULT_WORKHORSE")
        if default_workhorse:
            cfg.models.default_workhorse = default_workhorse

        return cfg
    except Exception as e:
        print(f"[Warning] Failed loading settings.json ({e}), creating defaults.")
        cfg = ScholarForgeConfig(gemini_api_key=gemini_key)
        save_settings(cfg)
        return cfg

def save_settings(config: ScholarForgeConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)

import re

def slugify_title(text: str) -> str:
    """Converts a review paper title into a filesystem-safe folder slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text[:60].strip('_') or "review_project"

def get_active_workspace(custom_path: Optional[str] = None) -> Path:
    """
    Resolves the active review project workspace.
    Prioritizes explicit paths, then configured active_project, then existing projects with 00_project.
    """
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p
    cfg = get_settings()
    root = Path(cfg.workspace_dir)
    root.mkdir(parents=True, exist_ok=True)
    
    # 1. Check configured active_project
    if cfg.active_project:
        p = root / cfg.active_project
        if (p / "00_project").exists() or p.exists():
            return p
            
    # 2. Check any user project folder (sorted by most recently modified)
    user_projects = []
    for p in root.iterdir():
        if p.is_dir() and not p.name.startswith(".") and not p.name.startswith("_") and (p / "00_project").exists():
            user_projects.append((p.stat().st_mtime, p))
    if user_projects:
        user_projects.sort(key=lambda x: x[0], reverse=True)
        return user_projects[0][1]
            
    # 3. Clean default for new workspace
    fallback = root / "new_paper"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

def set_active_project(slug: str) -> bool:
    """Updates the active project slug in settings.json."""
    cfg = get_settings()
    cfg.active_project = slug
    save_settings(cfg)
    return True

def list_all_projects() -> list:
    """Scans workspace directory for review projects."""
    cfg = get_settings()
    root = Path(cfg.workspace_dir)
    root.mkdir(parents=True, exist_ok=True)
    projects = []
    
    for d in sorted(root.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_") and (d / "00_project").exists():
            brief_file = d / "00_project" / "project_brief.md"
            state_file = d / "00_project" / "STATE.md"
            title = d.name.replace("_", " ").title()
            review_type = "Narrative"
            status = "Initialized"
            
            if brief_file.exists():
                txt = brief_file.read_text(encoding="utf-8")
                t_match = re.search(r"# Project Brief:\s*(.*)", txt)
                if t_match:
                    title = t_match.group(1).strip()
                r_match = re.search(r"- \*\*Review Type\*\*:\s*(.*)", txt)
                if r_match:
                    review_type = r_match.group(1).strip()
            
            if state_file.exists():
                txt = state_file.read_text(encoding="utf-8")
                s_match = re.search(r"- \*\*Current Phase\*\*:\s*(.*)", txt)
                if s_match:
                    status = f"Phase {s_match.group(1).strip()}"
                    
            word_count = 0
            manuscript_file = d / "06_manuscript" / "manuscript.md"
            if manuscript_file.exists():
                words = manuscript_file.read_text(encoding="utf-8").split()
                word_count = len(words)
                
            projects.append({
                "slug": d.name,
                "title": title,
                "review_type": review_type,
                "status": status,
                "word_count": word_count,
                "is_active": (d.name == cfg.active_project),
                "path": str(d)
            })
    return projects

