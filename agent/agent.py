from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset


MCP_URL = os.environ.get("MCP_URL", "http://command-gateway:8000/mcp")
REQUESTOR_URL = os.environ.get(
    "REQUESTOR_URL", "https://command-gateway-demo.local/requestor"
)
MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")


def dynamic_headers(readonly_context: ReadonlyContext) -> dict[str, str]:
  return {
      "X-Session-Id": readonly_context.session.id,
  }


command_gateway_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=MCP_URL,
        headers={
            "X-Requestor-Url": REQUESTOR_URL,
        },
    ),
    header_provider=dynamic_headers,
)


root_agent = Agent(
    name="command_gateway_agent",
    model=MODEL,
    instruction=(
        #"You request command execution through the command gateway tool. "
        #"When the user asks to execute a command on a host, call "
        #"execute_command with only hostname and command."
        "Submit linux command 'date' on host 'secgcpagent01' for ticket 'INC-TEST-001' because we are testing read-only gateway execution."
    ),
    tools=[command_gateway_tools],
)
