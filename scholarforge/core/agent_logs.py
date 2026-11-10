import time
from typing import List, Dict, Any

class AgentLogger:
    """
    In-memory live streaming log ring-buffer for the Developer Agent Terminal HUD.
    """
    _logs: List[Dict[str, Any]] = []
    MAX_LOGS = 200

    @classmethod
    def log(cls, agent: str, message: str, level: str = "info", details: str = ""):
        timestamp = time.strftime("%H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "agent": agent.upper(),
            "message": message,
            "level": level,  # 'info', 'success', 'warning', 'error', 'system'
            "details": details
        }
        cls._logs.append(entry)
        if len(cls._logs) > cls.MAX_LOGS:
            cls._logs.pop(0)

    @classmethod
    def get_logs(cls) -> List[Dict[str, Any]]:
        if not cls._logs:
            cls.log("SYSTEM", "ScholarForge Agent Kernel initialized in Local-First Mode.", "system")
            cls.log("GATEWAY", "Gemini 3.8 Flash High registered with live Google Search grounding.", "info")
            cls.log("MCP", "Local MCP Gateway ready (Zero OpenAI API billing enforced).", "success")
        return cls._logs

    @classmethod
    def clear(cls):
        cls._logs.clear()

