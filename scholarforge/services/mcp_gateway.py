import asyncio
import json
import httpx
from typing import Dict, Any, List, Optional
from ..core.config import get_settings

class MCPGateway:
    """
    Gateway to interact with local Model Context Protocol (MCP) servers.
    Zero OpenAI API billing: routes through local subscriptions and MCP agent bridges.
    """
    def __init__(self):
        self.settings = get_settings().models

    async def list_available_mcp_models(self) -> List[Dict[str, Any]]:
        """
        Discovers models exposed by active local MCP servers (e.g. Astra, Sol 6.1, ChatGPT).
        """
        discovered = []
        if not self.settings.mcp_enabled:
            return discovered

        for server_name, server_cfg in self.settings.mcp_servers.items():
            if not server_cfg.get("enabled", False):
                continue
            
            transport = server_cfg.get("transport", "")
            if transport == "sse":
                url = server_cfg.get("url", "")
                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        resp = await client.get(f"{url}/models")
                        if resp.status_code == 200:
                            data = resp.json()
                            discovered.append({
                                "server": server_name,
                                "type": "mcp_sse",
                                "models": data.get("models", [server_name])
                            })
                except Exception:
                    # Server not currently running; record as offline
                    discovered.append({
                        "server": server_name,
                        "type": "mcp_sse",
                        "status": "offline",
                        "models": [server_name]
                    })
            elif transport == "stdio":
                discovered.append({
                    "server": server_name,
                    "type": "mcp_stdio",
                    "status": "configured",
                    "models": [f"{server_name}-mcp"]
                })
        return discovered

    async def call_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes an MCP tool on a target server.
        """
        server_cfg = self.settings.mcp_servers.get(server_name)
        if not server_cfg or not server_cfg.get("enabled"):
            raise ValueError(f"MCP server '{server_name}' is not enabled or configured.")

        transport = server_cfg.get("transport")
        if transport == "sse":
            url = server_cfg.get("url")
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{url}/tools/{tool_name}",
                    json={"arguments": arguments}
                )
                resp.raise_for_status()
                return resp.json()
        elif transport == "stdio":
            # For stdio, can be driven directly by Antigravity or local process bridge
            return {"status": "dispatched", "server": server_name, "tool": tool_name}
        
        raise NotImplementedError(f"Unsupported transport: {transport}")

