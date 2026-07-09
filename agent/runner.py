from __future__ import annotations

import asyncio

from google.adk.runners import InMemoryRunner
from google.genai import types

from agent.agent import command_gateway_tools
from agent.agent import root_agent


APP_NAME = "command_gateway_demo"
USER_ID = "demo-user"
# user_message = (
#     'Use the submit_operation tool. '
#     'Submit this operation with ticket_id INC-TEST-001, technology linux, '
#     'hostname secgcpagent01, command date, and reason testing read-only gateway execution.'
# )


# user_message = (
#     'Use the submit_operation tool. '
#     'Submit this operation with ticket_id INC-TEST-WRITE-001, technology linux, '
#     'hostname secgcpagent01, command "systemctl restart sssd", '
#     'and reason "Testing write command approval flow for SSSD restart".'
# )


user_message = (
    'Use the submit_operation tool. '
    'Submit this operation with ticket_id INC-TEST-BLOCK-001, technology linux, '
    'hostname secgcpagent01, command "rm -rf /", '
    'and reason "Testing destructive command blocking".'
)




async def main() -> None:
  runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
  session = await runner.session_service.create_session(
      app_name=APP_NAME,
      user_id=USER_ID,
  )

  print(f"Created ADK in-memory session: {session.id}", flush=True)
  print(f"User: {user_message}", flush=True)

  content = types.Content(
      role="user",
      parts=[types.Part.from_text(text=user_message)],
  )

  try:
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=content,
    ):
      if not event.content or not event.content.parts:
        continue
      for part in event.content.parts:
        if part.function_call:
          print(
              f"Tool call: {part.function_call.name}"
              f" args={part.function_call.args}",
              flush=True,
          )
        if part.function_response:
          print(
              f"Tool response: {part.function_response.name}"
              f" response={part.function_response.response}",
              flush=True,
          )
        if part.text:
          print(f"{event.author}: {part.text}", flush=True)
  finally:
    await command_gateway_tools.close()


if __name__ == "__main__":
  asyncio.run(main())
