# Command Gateway MCP Demo

This demo has two Docker containers:

- `command-gateway`: an MCP Streamable HTTP server exposing
  `execute_command(hostname, command)`.
- `adk-agent`: a Google ADK agent that connects to the MCP server over HTTP.

The gateway expects these values as HTTP headers:

- `X-Session-Id`: set dynamically by the ADK `header_provider` from the current
  in-memory ADK session.
- `X-Requestor-Url`: set statically in the MCP connection parameters.

The gateway logs command requests but never executes the command.

## Run

This demo is configured to use Vertex AI as the ADK LLM provider.

Set your Google Cloud project and authenticate with Application Default
Credentials:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

Then run:

```bash
docker compose up --build adk-agent
```

The agent runner creates an in-memory session and asks:

```text
Execute command "date" on host "localhost".
```

To see the gateway log after the run:

```bash
docker compose logs command-gateway
```
