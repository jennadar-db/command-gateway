"""Technology router for downstream MCP execution."""

from __future__ import annotations

from typing import Any, Dict

from gateway.clients.linux_mcp_client import execute_linux_tool
from gateway.core.types import CommandRequest, Classification


async def route_to_mcp(request: CommandRequest, classification: Classification) -> Dict[str, Any]:
    if request.technology.lower() == "linux":
        return await execute_linux_tool(
            hostname=request.hostname,
            command=request.command,
            selected_mcp_tool=classification.selected_mcp_tool or "linux_execute_command",
            ticket_id=request.ticket_id,
            reason=request.reason,
        )

    return {
        "status": "failed",
        "execution_performed": False,
        "reason": f"Unsupported technology route: {request.technology}",
    }
