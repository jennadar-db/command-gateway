"""Client for the downstream Linux MCP server over streamable HTTP."""

from __future__ import annotations

from typing import Any, Dict

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from gateway.config import settings


def _derive_mcp_url() -> str:
    return settings.linux_mcp_url


def _coerce_call_tool_result(result: Any) -> Dict[str, Any]:
    is_error = bool(getattr(result, "isError", False))
    structured = getattr(result, "structuredContent", None)

    if isinstance(structured, dict):
        normalized = dict(structured)
        if is_error and normalized.get("status") == "success":
            normalized["status"] = "failed"
        return normalized

    content = getattr(result, "content", None) or []
    text_chunks: list[str] = []

    for item in content:
        text = getattr(item, "text", None)
        if isinstance(text, str) and text:
            text_chunks.append(text)

    if text_chunks:
        return {
            "status": "failed" if is_error else "success",
            "execution_performed": not is_error,
            "output": "\n".join(text_chunks),
        }

    return {
        "status": "failed" if is_error else "success",
        "execution_performed": not is_error,
    }


async def execute_linux_tool(
    *,
    hostname: str,
    command: str,
    selected_mcp_tool: str,
    ticket_id: str,
    reason: str,
) -> Dict[str, Any]:
    mcp_url = _derive_mcp_url()
    if not mcp_url:
        return {
            "status": "failed",
            "execution_performed": False,
            "reason": "LINUX_MCP_URL is not configured.",
        }

    payload: Dict[str, Any] = {
        "hostname": hostname,
        "command": command,
        "ticket_id": ticket_id,
        "reason": reason,
    }

    try:
        async with streamablehttp_client(mcp_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(selected_mcp_tool, payload)
                return _coerce_call_tool_result(result)
    except httpx.HTTPError as exc:
        return {
            "status": "failed",
            "execution_performed": False,
            "reason": f"Failed to call Linux MCP server over HTTP: {exc}",
        }
    except Exception as exc:  # pragma: no cover - safeguard for SDK/runtime mismatch
        return {
            "status": "failed",
            "execution_performed": False,
            "reason": f"Failed to call Linux MCP tool {selected_mcp_tool}: {exc}",
        }
