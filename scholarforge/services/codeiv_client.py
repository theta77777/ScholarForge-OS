import httpx
from typing import Dict, Any, Optional
from ..core.config import get_settings
from ..core.database import DatabaseManager

class CodeIVDecisionEngine:
    """
    Alternative decision engine utilizing CodeIV's 100M free token tier.
    RULE: Only active when 'enable_automated_decisions' is toggled ON in Settings.
    If OFF (default), all decisions pause for human approval.
    """
    def __init__(self):
        self.config = get_settings().models
        self.db = DatabaseManager()

    @property
    def is_active(self) -> bool:
        return bool(self.config.enable_automated_decisions and self.config.codeiv_api_key)

    async def evaluate_decision(self, project_slug: str, step: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a workflow decision (e.g. should a paper be included, or does an extraction need more data?).
        """
        if not self.is_active:
            # Human-in-the-Loop default
            return {
                "decision": "awaiting_human_approval",
                "mode": "human",
                "step": step,
                "message": "Automated AI decision-making is OFF. Please review and make your choice in the UI.",
                "context": context
            }

        # If CodeIV is activated in settings, dispatch decision evaluation
        headers = {
            "Authorization": f"Bearer {self.config.codeiv_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "step": step,
            "context": context,
            "instruction": (
                "You are an academic review paper decision policy model. "
                "Evaluate the context and output a structured decision: 'proceed', 'request_more_data', or 'reject'."
            )
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.config.codeiv_api_url}/decisions/evaluate",
                    headers=headers,
                    json=payload
                )
                if resp.status_code == 200:
                    result = resp.json()
                    self.db.log_decision(
                        project_slug=project_slug,
                        step=step,
                        decision_maker="codeiv",
                        details=result,
                        confidence=result.get("confidence", 0.95)
                    )
                    return {
                        "decision": result.get("decision", "proceed"),
                        "mode": "codeiv",
                        "confidence": result.get("confidence", 0.95),
                        "rationale": result.get("rationale", "")
                    }
        except Exception as e:
            print(f"[Warning] CodeIV decision evaluation failed: {e}. Falling back to human gate.")

        # Fallback to human approval on any error
        return {
            "decision": "awaiting_human_approval",
            "mode": "human",
            "step": step,
            "message": "Automated decision call failed or timed out. Human review required."
        }

