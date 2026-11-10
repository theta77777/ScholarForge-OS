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


class TaskProgressTracker:
    """
    Tracks and broadcasts real-time percentage progress (0-100%) and live task execution telemetry
    across Steps 1 to 4 and the autonomous pipeline.
    """
    _state: Dict[str, Any] = {
        "active": False,
        "task_name": "Idle",
        "step": 0,
        "total_steps": 4,
        "percentage": 0,
        "message": "Ready to launch research pipeline",
        "timestamp": "",
        "start_time": 0
    }

    @classmethod
    def set_progress(cls, task_name: str, percentage: int, message: str, step: int = 1, total_steps: int = 4):
        now = time.time()
        start = cls._state.get("start_time") or now
        cls._state = {
            "active": True,
            "task_name": task_name,
            "step": step,
            "total_steps": total_steps,
            "percentage": max(0, min(100, int(percentage))),
            "message": message,
            "timestamp": time.strftime("%H:%M:%S"),
            "start_time": start,
            "elapsed_seconds": int(now - start) if start else 0
        }
        AgentLogger.log(task_name.upper()[:12], f"[{int(percentage)}%] {message}", "info")

    @classmethod
    def complete(cls, task_name: str, message: str = "Completed successfully"):
        start = cls._state.get("start_time") or time.time()
        cls._state = {
            "active": False,
            "task_name": task_name,
            "step": 4,
            "total_steps": 4,
            "percentage": 100,
            "message": message,
            "timestamp": time.strftime("%H:%M:%S"),
            "start_time": 0,
            "elapsed_seconds": int(time.time() - start) if start else 0
        }
        AgentLogger.log(task_name.upper()[:12], f"[100%] {message}", "success")

    @classmethod
    def get_progress(cls) -> Dict[str, Any]:
        return cls._state

    @classmethod
    def reset(cls):
        cls._state = {
            "active": False,
            "task_name": "Idle",
            "step": 0,
            "total_steps": 4,
            "percentage": 0,
            "message": "Ready to launch research pipeline",
            "timestamp": time.strftime("%H:%M:%S"),
            "start_time": 0,
            "elapsed_seconds": 0
        }


