from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from gateway import server


@pytest.mark.asyncio
async def test_execute_command_schema_only_exposes_agent_arguments():
  result = await server.handle_list_tools(ctx=None, params=None)

  execute_command = result.tools[0]
  assert execute_command.name == "execute_command"
  assert execute_command.inputSchema["required"] == ["hostname", "command"]
  assert set(execute_command.inputSchema["properties"]) == {
      "hostname",
      "command",
  }


@pytest.mark.asyncio
async def test_execute_command_uses_headers_without_executing(caplog):
  ctx = SimpleNamespace(
      request=SimpleNamespace(
          headers={
              "x-session-id": "session-123",
              "x-requestor-url": "https://requestor.example/demo",
          }
      )
  )
  params = SimpleNamespace(
      arguments={"hostname": "localhost", "command": "date"}
  )

  with caplog.at_level(logging.INFO, logger=server.LOGGER_NAME):
    result = await server.handle_call_tool(ctx, params)

  assert "Simulated command request" in caplog.text
  assert "session-123" in caplog.text
  assert "https://requestor.example/demo" in caplog.text
  assert "localhost" in result.content[0].text
  assert "date" in result.content[0].text
  assert "not executed" in result.content[0].text
