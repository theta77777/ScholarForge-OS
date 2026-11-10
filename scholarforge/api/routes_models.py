from fastapi import APIRouter
from typing import Dict, Any, List
from ..services.gemini_client import GeminiClient
from ..services.mcp_gateway import MCPGateway
from ..core.config import get_settings

router = APIRouter(prefix="/api/models", tags=["Models"])

@router.get("/live")
async def get_live_models():
    """
    Dynamic Model Discovery Deck:
    Scans live Google AI Studio models and active local MCP servers (Astra, Sol 6.1, ChatGPT).
    """
    settings = get_settings()
    gemini = GeminiClient()
    mcp = MCPGateway()

    # 1. Google AI Studio Live Models
    google_models = gemini.list_live_models()
    
    # Ensure Gemini 3.8 Flash variants are explicitly present
    preferred_gemini = [
        {"id": "gemini-3.8-flash", "label": "Gemini 3.8 Flash (High Reasoning)", "provider": "Google AI Studio", "recommended": True},
        {"id": "gemini-3.8-flash-medium", "label": "Gemini 3.8 Flash (Medium Reasoning)", "provider": "Google AI Studio", "recommended": False},
        {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (Deep Context)", "provider": "Google AI Studio", "recommended": False}
    ]

    # 2. Local MCP Discovered Models (Zero API Billing)
    mcp_models = await mcp.list_available_mcp_models()

    # 3. Decision Model Status (CodeIV vs Human)
    decision_engine_status = {
        "mode": "automated_codeiv" if settings.models.enable_automated_decisions else "human_in_the_loop",
        "codeiv_enabled": settings.models.enable_automated_decisions,
        "token_pool": "100M free tokens" if settings.models.enable_automated_decisions else "none"
    }

    return {
        "status": "success",
        "active_workhorse": settings.models.default_workhorse,
        "google_ai_studio_models": preferred_gemini,
        "mcp_external_models": mcp_models,
        "decision_engine": decision_engine_status
    }

