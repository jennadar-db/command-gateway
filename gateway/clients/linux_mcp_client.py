"""Client for the downstream Linux MCP server/host.

For MVP, this client calls a REST /execute endpoint on the Linux MCP host because it
is easier to test from the gateway. The Linux MCP can still expose MCP /mcp for other
clients. Later you can replace this with a proper MCP client call.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from gateway.config import settings


def _derive_execute_url() -> str:
    if settings.linux_mcp_execute_url:
        return settings.linux_mcp_execute_url
    if settings.linux_mcp_url:
        # If LINUX_MCP_URL=http://host:9001/mcp, call http://host:9001/execute for MVP.
        return settings.linux_mcp_url.rstrip("/").removesuffix("/mcp") + "/execute"
    return ""


async def execute_linux_tool(
    *,
    hostname: str,
    command: str,
    selected_mcp_tool: str,
    ticket_id: str,
    reason: str,
) -> Dict[str, Any]:
    execute_url = _derive_execute_url()
    if not execute_url:
        return {
            "status": "failed",
            "execution_performed": False,
            "reason": "LINUX_MCP_URL or LINUX_MCP_EXECUTE_URL is not configured.",
        }

    payload = {
        "hostname": hostname,
        "command": command,
        "tool": selected_mcp_tool,
        "ticket_id": ticket_id,
        "reason": reason,
    }

    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        response = await client.post(execute_url, json=payload)
        response.raise_for_status()
        data = response.json()

    return data
