"""Command Gateway MCP proxy server.

This replaces the original logging-only execute_command gateway with a barrier that:
- receives operation requests from TSA/ADK,
- decides READ_ONLY vs WRITE vs BLOCKED,
- creates approval requests for WRITE commands,
- routes allowed/approved requests to the downstream Linux MCP server/host.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request

from gateway.config import settings
from gateway.core.policy_engine import PolicyEngine
from gateway.core.types import CommandRequest

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("command_gateway")

mcp = FastMCP("command-gateway", host="0.0.0.0", port=8000)
policy_engine = PolicyEngine()


def _get_headers() -> Dict[str, str]:
    """Best-effort header extraction.

    FastMCP streamable HTTP makes headers available depending on SDK/runtime version.
    Keep this lightweight; absence of headers should not break local testing.
    """
    return {}


@mcp.tool()
async def submit_operation(
    ticket_id: str,
    technology: str,
    hostname: str,
    command: str,
    reason: str,
) -> Dict[str, Any]:
    """Submit a command/operation request to the Command Gateway.

    The agent must not provide downstream MCP tool names, approval ticket ids, or
    approval hashes. The Gateway owns classification, approval and routing.
    """
    request = CommandRequest(
        ticket_id=ticket_id,
        technology=technology,
        hostname=hostname,
        command=command,
        reason=reason,
    )
    logger.info(
        "Received submit_operation: ticket_id=%s technology=%s hostname=%s command=%r reason=%r",
        ticket_id, technology, hostname, command, reason,
    )
    return await policy_engine.submit_operation(request)


@mcp.tool()
async def check_approval_and_execute(approval_request_id: str) -> Dict[str, Any]:
    """Execute a previously submitted WRITE operation after human approval.

    The agent only sends approval_request_id. The Gateway retrieves the original
    command and validates approval before execution.
    """
    logger.info("Received check_approval_and_execute: approval_request_id=%s", approval_request_id)
    return await policy_engine.check_approval_and_execute(approval_request_id)


@mcp.tool()
def approve_request_for_local_test(approval_request_id: str) -> Dict[str, Any]:
    """Local-only helper to simulate HITL approval in APPROVAL_MODE=mock.

    Remove or disable this tool before production.
    """
    if settings.approval_mode != "mock":
        return {"status": "blocked", "reason": "Local approval helper is only allowed in mock mode."}
    logger.info("Mock-approving approval_request_id=%s", approval_request_id)
    return policy_engine.approve_request_for_local_test(approval_request_id)


@mcp.tool()
def get_gateway_status() -> Dict[str, Any]:
    """Return basic gateway routing/config status."""
    return {
        "status": "ok",
        "service": "command-gateway",
        "approval_mode": settings.approval_mode,
        "linux_mcp_url_configured": bool(settings.linux_mcp_url),
    }


if __name__ == "__main__":
    # Streamable HTTP server. Matches your existing /mcp gateway behavior.
    mcp.run(transport="streamable-http")
