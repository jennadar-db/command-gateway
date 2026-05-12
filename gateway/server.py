from __future__ import annotations

import logging
import os
from typing import Any

from mcp import types
from mcp.server.fastmcp import Context
from mcp.server.fastmcp import FastMCP


LOGGER_NAME = "command_gateway"
logger = logging.getLogger(LOGGER_NAME)

SESSION_ID_HEADER = "x-session-id"
REQUESTOR_URL_HEADER = "x-requestor-url"

mcp = FastMCP(
    "command-gateway",
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8000")),
    streamable_http_path="/mcp",
)


def _get_header_from_request(request: Any, name: str) -> str:
  headers = getattr(request, "headers", {}) or {}
  return headers.get(name, headers.get(name.lower(), ""))


def _get_request_from_context(ctx: Context | Any) -> Any:
  request_context = getattr(ctx, "request_context", None)
  return getattr(request_context, "request", None) or getattr(ctx, "request", None)


def _simulate_execute_command(
    *,
    hostname: str,
    command: str,
    request: Any,
) -> str:
  session_id = (
      _get_header_from_request(request, SESSION_ID_HEADER)
      or "missing-session-id"
  )
  requestor_url = (
      _get_header_from_request(request, REQUESTOR_URL_HEADER)
      or "missing-requestor-url"
  )

  logger.info(
      "Simulated command request: hostname=%s command=%r session_id=%s"
      " requestor_url=%s",
      hostname,
      command,
      session_id,
      requestor_url,
  )

  return (
      "Command request accepted for logging only; command was not"
      f" executed. hostname={hostname}, command={command},"
      f" session_id={session_id}, requestor_url={requestor_url}"
  )


@mcp.tool()
async def execute_command(
    hostname: str,
    command: str,
    ctx: Context,
) -> str:
  """Log a command request without executing it."""
  request = _get_request_from_context(ctx)
  return _simulate_execute_command(
      hostname=hostname,
      command=command,
      request=request,
  )


async def handle_list_tools(
    ctx: Any | None,
    params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
  del ctx, params
  return types.ListToolsResult(tools=await mcp.list_tools())


async def handle_call_tool(
    ctx: Any,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
  arguments = params.arguments or {}
  hostname = str(arguments.get("hostname", ""))
  command = str(arguments.get("command", ""))
  request = _get_request_from_context(ctx)
  text = _simulate_execute_command(
      hostname=hostname,
      command=command,
      request=request,
  )

  return types.CallToolResult(
      content=[
          types.TextContent(
              type="text",
              text=text,
          )
      ]
  )


def create_app():
  return mcp.streamable_http_app()


def main() -> None:
  logging.basicConfig(
      level=os.environ.get("LOG_LEVEL", "INFO").upper(),
      format="%(asctime)s %(levelname)s %(name)s %(message)s",
  )
  mcp.run(transport="streamable-http")


if __name__ == "__main__":
  main()
