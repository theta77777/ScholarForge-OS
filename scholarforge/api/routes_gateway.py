from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from ..services.cloud_api_gateway import cloud_gateway

router = APIRouter(prefix="/api/gateway", tags=["Cloud API Gateway"])

class ApiUpdateRequest(BaseModel):
    api_id: str
    endpoint: Optional[str] = None
    rate_rps: Optional[float] = None
    timeout_sec: Optional[float] = None
    retries: Optional[int] = None
    enabled: Optional[bool] = None
    custom_key: Optional[str] = None
    fallback_id: Optional[str] = None

class ApiTestRequest(BaseModel):
    api_id: str
    test_key: Optional[str] = None
    test_endpoint: Optional[str] = None

class DismissAlertRequest(BaseModel):
    alert_id: str

class ResetRequest(BaseModel):
    api_id: Optional[str] = None

class ImportConfigRequest(BaseModel):
    overrides: Dict[str, Any]

@router.get("/apis")
def list_apis():
    """Lists all cloud APIs with live operational metrics, latencies, and user custom overrides."""
    return {
        "status": "success",
        "total_apis": len(cloud_gateway.registry),
        "apis": cloud_gateway.list_all_apis(),
        "active_alerts_count": len(cloud_gateway.alerts)
    }

@router.post("/update")
def update_api(req: ApiUpdateRequest):
    """Developer-grade update for any individual API (endpoint, rate limits, timeouts, credentials, fallback)."""
    if req.api_id not in cloud_gateway.registry:
        raise HTTPException(status_code=404, detail=f"API '{req.api_id}' not found")
    
    updates = req.model_dump(exclude_unset=True)
    updates.pop("api_id", None)
    cloud_gateway.update_api_config(req.api_id, updates)
    
    return {
        "status": "success",
        "message": f"Settings updated for '{req.api_id}'",
        "api": cloud_gateway.registry[req.api_id]
    }

@router.post("/test")
async def test_api_live(req: ApiTestRequest):
    """Executes a real-time HTTP probe against an API with live latency, status code, and header diagnostics."""
    result = await cloud_gateway.probe_api(req.api_id, req.test_key, req.test_endpoint)
    return result

@router.post("/reset")
def reset_to_defaults(req: ResetRequest):
    """Reverts an individual API or the entire 122 API catalog back to factory defaults."""
    cloud_gateway.reset_api_defaults(req.api_id)
    return {
        "status": "success",
        "message": f"Reset {'all APIs' if not req.api_id else req.api_id} to pristine factory defaults."
    }

@router.get("/alerts")
def get_alerts():
    """Returns active intercepted failure alerts (rate-limits, timeouts, missing credentials)."""
    alerts = cloud_gateway._load_alerts()
    return {
        "alerts": alerts,
        "count": len(alerts)
    }

@router.post("/alerts/dismiss")
def dismiss_alert(req: DismissAlertRequest):
    """Dismisses an alert once addressed by the researcher."""
    cloud_gateway.dismiss_alert(req.alert_id)
    return {"status": "success", "message": "Alert dismissed"}

@router.get("/export")
def export_gateway_config():
    """Exports all custom overrides, rate limits, and endpoint configurations as JSON."""
    return {
        "version": "2.1.0",
        "overrides": cloud_gateway.overrides,
        "exported_at": cloud_gateway.registry.get("openalex", {}).get("status")
    }

@router.post("/import")
def import_gateway_config(req: ImportConfigRequest):
    """Imports and applies developer configuration JSON overrides across all APIs."""
    cloud_gateway.overrides = req.overrides
    cloud_gateway._save_overrides()
    cloud_gateway.registry = cloud_gateway._init_registry()
    return {
        "status": "success",
        "message": f"Successfully applied configuration overrides for {len(req.overrides)} APIs."
    }
