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

### Optional: Proxy or Internal PyPI Mirror

If Docker builds cannot reach public PyPI in your environment, export these
before running `docker compose up --build adk-agent`:

```bash
export HTTP_PROXY="http://squid-proxy.gcp.dbgcloud.io:3128"
export HTTPS_PROXY="http://squid-proxy.gcp.dbgcloud.io:3128"
export NO_PROXY="localhost,127.0.0.1,command-gateway"

# Optional internal package index
export PIP_INDEX_URL="https://pypi.my-company.example/simple"
export PIP_TRUSTED_HOST="pypi.my-company.example"
```

These values are passed to both image builds and running containers.

The agent runner creates an in-memory session and asks:

```text
Execute command "date" on host "localhost".
```

To see the gateway log after the run:

```bash
docker compose logs command-gateway
```
