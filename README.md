# Command Gateway MCP Demo

Command Gateway is an MCP proxy that sits between an agent and a Linux execution service.
It classifies requested operations into policy categories, enforces approvals for write actions,
and routes allowed commands to a downstream Linux executor.

## What This Repo Runs

Docker Compose starts three services:

- command-gateway
  - MCP Streamable HTTP server on port 8000.
  - Exposes tools for operation submission, approval check, and local mock approval.
  - Applies policy classification: READ_ONLY, WRITE, BLOCKED, UNKNOWN.
- adk-agent
  - Google ADK-based agent container.
  - Connects to the gateway MCP endpoint and sends gateway headers.
- linux-mcp
  - FastAPI service on port 9001.
  - Executes only a strict allowlist of safe commands for demo purposes.

## Request Flow

1. Agent calls submit_operation with:
   - ticket_id
   - technology (linux)
   - hostname
   - command
   - reason
2. Gateway classifies command by deterministic regex policy.
3. Outcome by class:
   - READ_ONLY: routed immediately to linux-mcp execute endpoint.
   - WRITE: approval request is created and stored locally.
   - BLOCKED or UNKNOWN: rejected by policy.
4. For WRITE operations, agent calls check_approval_and_execute after approval.

In mock mode, local testing can use approve_request_for_local_test to mark a pending request approved.

## MCP Tools Exposed By Gateway

- submit_operation(ticket_id, technology, hostname, command, reason)
- check_approval_and_execute(approval_request_id)
- approve_request_for_local_test(approval_request_id)
- get_gateway_status()

## Prerequisites

- Docker with Compose plugin
- Google Cloud authentication for ADK model access (Vertex AI)

Authenticate and set cloud variables:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

## Environment Variables

Core runtime values:

```bash
export LINUX_MCP_URL="http://linux-mcp:9001/mcp"
export LINUX_MCP_EXECUTE_URL="http://linux-mcp:9001/execute"
export APPROVAL_MODE="mock"  # mock | jira
export APPROVAL_STORE_PATH="/tmp/command_gateway_approvals.json"
export ADK_MODEL="gemini-2.5-flash"
```

Proxy and package mirror values (optional, for restricted networks):

```bash
export HTTP_PROXY="http://proxy.example:3128"
export HTTPS_PROXY="http://proxy.example:3128"
export NO_PROXY="localhost,127.0.0.1,command-gateway,linux-mcp"

# Optional internal package index
export PIP_INDEX_URL="https://pypi.my-company.example/simple"
export PIP_TRUSTED_HOST="pypi.my-company.example"
```

Notes:

- Compose already reads values from a local .env file if present.
- In current code, APPROVAL_MODE=jira is not implemented yet and raises NotImplementedError.

## Run

Build and start everything:

```bash
docker compose up --build
```

Or run only the demo agent flow:

```bash
docker compose up --build adk-agent
```

## Verify Service Health

Linux executor health:

```bash
curl -s http://localhost:9001/health
```

Gateway status via MCP tool can be checked through the connected agent,
or by inspecting logs:

```bash
docker compose logs -f command-gateway
```

## Try The Policy Paths

The demo runner inside adk-agent currently sends a fixed test request. You can change
the message in agent/runner.py to test each path.

Examples:

READ_ONLY example (direct execution):

```text
Use the submit_operation tool. Submit this operation with ticket_id INC-TEST-001,
technology linux, hostname secgcpagent01, command date,
and reason testing read-only gateway execution.
```

WRITE example (requires approval):

```text
Use the submit_operation tool. Submit this operation with ticket_id INC-TEST-WRITE-001,
technology linux, hostname secgcpagent01, command "systemctl restart sssd",
and reason "Testing write command approval flow for SSSD restart".
```

BLOCKED example (rejected):

```text
Use the submit_operation tool. Submit this operation with ticket_id INC-TEST-BLOCK-001,
technology linux, hostname secgcpagent01, command "rm -rf /",
and reason "Testing destructive command blocking".
```

## Approval Behavior (Mock Mode)

For WRITE commands:

1. submit_operation returns approval_required and an approval_request_id.
2. approve_request_for_local_test marks that request approved.
3. check_approval_and_execute performs execution once.

Approvals are single-use and persisted in APPROVAL_STORE_PATH.

## Linux Executor Safety Constraints

linux-mcp is intentionally strict for demo safety.

- Exact command allowlist execution for a small set of commands (for example: date, hostname, uptime, whoami, id, df -h, free -m, free -h).
- ad_check commands return a mocked success response.
- Any non-allowlisted execute request returns HTTP 403.

## Known Limitations

- Jira mode is scaffolded but not implemented.
- Gateway header extraction helper is currently a best-effort stub.
- Policy definitions exist in both code and YAML, but code-based classifier is the active enforcement path.

## Development

Run tests:

```bash
pytest -q
```

Stop services:

```bash
docker compose down
```
