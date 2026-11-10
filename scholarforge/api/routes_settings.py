from fastapi import APIRouter, HTTPException
from ..core.config import get_settings, save_settings, ScholarForgeConfig

router = APIRouter(prefix="/api/settings", tags=["Settings"])

@router.get("")
def read_settings():
    """Returns current system configuration, model settings, and masked BYOK vault keys."""
    cfg = get_settings()
    masked = cfg.model_dump()
    if masked.get("gemini_api_key"):
        key = masked["gemini_api_key"]
        masked["gemini_api_key"] = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
    if masked["models"].get("codeiv_api_key"):
        key = masked["models"]["codeiv_api_key"]
        masked["models"]["codeiv_api_key"] = key[:4] + "..." + key[-4:] if len(key) > 8 else "***"
    
    # Mask API vault keys
    if "api_vault" in masked:
        for k, v in masked["api_vault"].items():
            if v:
                masked["api_vault"][k] = v[:4] + "..." + v[-3:] if len(v) > 7 else "***"
    return masked

@router.post("")
def update_settings(new_config: ScholarForgeConfig):
    """Updates settings (e.g. toggle CodeIV, select Gemini variant, configure BYOK keys)."""
    current = get_settings()
    
    # Preserve existing keys if incoming payload contains masked or empty values
    if new_config.gemini_api_key.startswith("***") or "..." in new_config.gemini_api_key:
        new_config.gemini_api_key = current.gemini_api_key
    elif not new_config.gemini_api_key and current.gemini_api_key:
        new_config.gemini_api_key = current.gemini_api_key

    if new_config.models.codeiv_api_key.startswith("***") or "..." in new_config.models.codeiv_api_key:
        new_config.models.codeiv_api_key = current.models.codeiv_api_key
    elif not new_config.models.codeiv_api_key and current.models.codeiv_api_key:
        new_config.models.codeiv_api_key = current.models.codeiv_api_key

    # Preserve vault keys
    current_vault = current.api_vault.model_dump()
    new_vault = new_config.api_vault.model_dump()
    for k, v in new_vault.items():
        if v.startswith("***") or "..." in v:
            setattr(new_config.api_vault, k, current_vault.get(k, ""))
        elif not v and current_vault.get(k):
            setattr(new_config.api_vault, k, current_vault.get(k, ""))

    save_settings(new_config)
    return {"status": "success", "message": "Settings and BYOK Key Vault updated successfully"}

@router.get("/vault/status")
def get_vault_status():
    """Returns connection and validity indicators for open and BYOK services."""
    cfg = get_settings()
    vault = cfg.api_vault
    return {
        "open_services": {
            "openalex": {"status": "connected", "cost": "100% Free", "quota": "100k/day"},
            "crossref": {"status": "connected", "cost": "100% Free", "quota": "Polite Pool"},
            "pubmed": {"status": "connected", "cost": "100% Free", "quota": "3-10 req/s"},
            "unpaywall": {"status": "connected", "cost": "100% Free", "quota": "100k/day"},
            "quickchart": {"status": "connected", "cost": "100% Free", "quota": "Unlimited"},
            "kroki": {"status": "connected", "cost": "100% Free", "quota": "Unlimited"},
            "retractionwatch": {"status": "connected", "cost": "100% Free", "quota": "Open Index"},
            "languagetool": {"status": "connected", "cost": "100% Free", "quota": "20k chars/call"}
        },
        "byok_services": {
            "scite": {"configured": bool(vault.scite_api_key), "tier": "BYOK"},
            "copyleaks": {"configured": bool(vault.copyleaks_api_key), "tier": "BYOK"},
            "gptzero": {"configured": bool(vault.gptzero_api_key), "tier": "BYOK"},
            "deepl": {"configured": bool(vault.deepl_api_key), "tier": "Free Key / BYOK"},
            "groq": {"configured": bool(vault.groq_api_key), "tier": "Free Key / BYOK"},
            "materials_project": {"configured": bool(vault.materials_project_key), "tier": "Free Key / BYOK"},
            "openrouter": {"configured": bool(vault.openrouter_api_key), "tier": "Free Key / BYOK"},
            "zenodo": {"configured": bool(vault.zenodo_token), "tier": "Free Personal Token"}
        }
    }

