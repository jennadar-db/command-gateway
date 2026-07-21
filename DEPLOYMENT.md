# Cloud Run Deployment Guide

This guide covers everything needed to build, push, and deploy **linux-mcp** and **command-gateway** to Google Cloud Run manually, including all required IAM permissions and policy bindings.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Variables](#2-project-variables)
3. [Artifact Registry Setup](#3-artifact-registry-setup)
4. [Service Accounts](#4-service-accounts)
5. [IAM Bindings](#5-iam-bindings)
6. [Build and Push Images](#6-build-and-push-images)
7. [Deploy linux-mcp](#7-deploy-linux-mcp)
8. [Deploy command-gateway](#8-deploy-command-gateway)
9. [Wire the Services Together](#9-wire-the-services-together)
10. [Smoke Test](#10-smoke-test)
11. [Redeployment (Updates)](#11-redeployment-updates)
12. [Teardown](#12-teardown)

---

## 1. Prerequisites

- `gcloud` CLI installed and authenticated
- `docker` installed and running
- Sufficient GCP permissions (see below)
- The following APIs enabled on your project:

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### Required caller permissions

Your personal/CI account needs at minimum:

| Role | Purpose |
|---|---|
| `roles/run.admin` | Deploy and configure Cloud Run services |
| `roles/iam.serviceAccountAdmin` | Create service accounts |
| `roles/iam.serviceAccountUser` | Attach service accounts to Cloud Run |
| `roles/artifactregistry.admin` | Create repo and push images |
| `roles/resourcemanager.projectIamAdmin` | Grant IAM bindings on the project |
| `roles/secretmanager.admin` | Create and manage secrets (if using Jira mode) |

---

## 2. Project Variables

Set these in your shell once. All subsequent commands reference them.

```bash
export PROJECT_ID="dbg-corpit-security-dev-ae"
export REGION="europe-west3"
export REPO="command-gateway"
export TAG="latest"   # or: git rev-parse --short HEAD

# Derived image paths
export LINUX_MCP_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/linux-mcp:${TAG}"
export GATEWAY_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/command-gateway:${TAG}"

# Service account emails
export GATEWAY_SA="command-gateway-sa@${PROJECT_ID}.iam.gserviceaccount.com"
export LINUX_MCP_SA="linux-mcp-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

---

## 3. Artifact Registry Setup

Create the Artifact Registry Docker repository if it does not already exist:

```bash
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Command Gateway images" \
  --project="${PROJECT_ID}"
```

Configure Docker to authenticate against it:

```bash
gcloud auth configure-docker "${REGION}-docker.pkg.dev"
```

---

## 4. Service Accounts

Create dedicated service accounts for each Cloud Run service. Using dedicated SAs gives each service the minimum permissions it needs (principle of least privilege).

```bash
# creation of Gateway SA
gcloud iam service-accounts create command-gateway-sa \
  --display-name="Command Gateway Cloud Run SA" \
  --project="${PROJECT_ID}"

# Creation of Linux MCP SA
gcloud iam service-accounts create linux-mcp-sa \
  --display-name="Linux MCP Cloud Run SA" \
  --project="${PROJECT_ID}"

#Service Values
export GATEWAY_SA="command-gateway-sa@${PROJECT_ID}.iam.gserviceaccount.com"
export LINUX_MCP_SA="linux-mcp-sa@${PROJECT_ID}.iam.gserviceaccount.com"

```

> **Note:** If you deployed earlier without specifying a service account, Cloud Run uses the default compute SA (`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`). In that case skip this section and substitute the default compute SA email wherever `GATEWAY_SA` or `LINUX_MCP_SA` appear below.

---

## 5. IAM Bindings

These bindings are required for the services to function correctly.

### 5a. Allow the gateway to invoke linux-mcp

The gateway calls linux-mcp over HTTPS using its own identity token. linux-mcp must trust that identity.

```bash
gcloud run services add-iam-policy-binding linux-mcp \
  --region="${REGION}" \
  --member="serviceAccount:${GATEWAY_SA}" \
  --role="roles/run.invoker"
```

> If the gateway is still running as the default compute SA, use that email instead:
> ```bash
> gcloud run services add-iam-policy-binding linux-mcp \
>   --region="${REGION}" \
>   --member="serviceAccount:$(gcloud run services describe command-gateway --region=${REGION} --format='value(spec.template.spec.serviceAccountName)')" \
>   --role="roles/run.invoker"
> ```

### 5b. Allow external callers (agents/users) to invoke the gateway

```bash
# Option A — specific identity (recommended)
gcloud run services add-iam-policy-binding command-gateway \
  --region="${REGION}" \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker"

# Option B — all authenticated Google identities (broader, still requires a token)
gcloud run services add-iam-policy-binding command-gateway \
  --region="${REGION}" \
  --member="allAuthenticatedUsers" \
  --role="roles/run.invoker"

# Option C — fully public (only for dev/test, check org policies)
gcloud run services add-iam-policy-binding command-gateway \
  --region="${REGION}" \
  --member="allUsers" \
  --role="roles/run.invoker"
```

### 5c. Allow the gateway to access the Jira secret (Jira mode only)

Skip this if using `APPROVAL_MODE=mock`.

```bash
gcloud secrets add-iam-policy-binding JIRA_BEARER_TOKEN \
  --member="serviceAccount:${GATEWAY_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project="${PROJECT_ID}"
```

### Summary of bindings

| Principal | Resource | Role |
|---|---|---|
| `command-gateway-sa` | `linux-mcp` Cloud Run service | `roles/run.invoker` |
| Your user / agent SA | `command-gateway` Cloud Run service | `roles/run.invoker` |
| `command-gateway-sa` | `JIRA_BEARER_TOKEN` secret *(Jira mode only)* | `roles/secretmanager.secretAccessor` |

---

## 6. Build and Push Images

Run these from the **repository root** (`command-gateway/`).

### linux-mcp

```bash
docker build \
  -f linux_mcp/Dockerfile \
  -t "${LINUX_MCP_IMAGE}" \
  .

docker push "${LINUX_MCP_IMAGE}"
```

### command-gateway

```bash
docker build \
  -f gateway/Dockerfile \
  -t "${GATEWAY_IMAGE}" \
  .

docker push "${GATEWAY_IMAGE}"
```

#### Building behind a corporate proxy

Pass proxy settings as build args:

```bash
docker build \
  -f gateway/Dockerfile \
  --build-arg HTTP_PROXY="${HTTP_PROXY}" \
  --build-arg HTTPS_PROXY="${HTTPS_PROXY}" \
  --build-arg NO_PROXY="${NO_PROXY}" \
  -t "${GATEWAY_IMAGE}" \
  .
```

---

## 7. Deploy linux-mcp

Deploy linux-mcp **first** because the gateway needs its URL as an environment variable.

```bash
gcloud run deploy linux-mcp \
  --image="${LINUX_MCP_IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --port=9001 \
  --service-account="${LINUX_MCP_SA}" \
  --no-allow-unauthenticated \
  --ingress=internal \
  --set-env-vars="LOG_LEVEL=INFO" \
  --project="${PROJECT_ID}"
```

> **Ingress note:** `--ingress=internal` means only traffic from within the same GCP project (including other Cloud Run services) can reach linux-mcp. This is the recommended setting — the gateway is the only intended caller.

Capture the URL for the next step:

```bash
export LINUX_MCP_URL="$(gcloud run services describe linux-mcp \
  --region="${REGION}" \
  --format='value(status.url)')/mcp"

echo "Linux MCP URL: ${LINUX_MCP_URL}"
```

---

## 8. Deploy command-gateway

```bash
gcloud run deploy command-gateway \
  --image="${GATEWAY_IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --port=8000 \
  --service-account="${GATEWAY_SA}" \
  --no-allow-unauthenticated \
  --ingress=internal \
  --set-env-vars="LOG_LEVEL=INFO,APPROVAL_MODE=mock,LINUX_MCP_URL=${LINUX_MCP_URL},APPROVAL_STORE_PATH=/tmp/command_gateway_approvals.json" \
  --project="${PROJECT_ID}"
```

#### Jira mode (optional)

First create the secret:

```bash
echo -n "your-jira-bearer-token" | \
  gcloud secrets create JIRA_BEARER_TOKEN \
    --data-file=- \
    --project="${PROJECT_ID}"
```

Then deploy with Jira variables:

```bash
gcloud run deploy command-gateway \
  --image="${GATEWAY_IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --port=8000 \
  --service-account="${GATEWAY_SA}" \
  --no-allow-unauthenticated \
  --ingress=internal \
  --set-env-vars="LOG_LEVEL=INFO,APPROVAL_MODE=jira,LINUX_MCP_URL=${LINUX_MCP_URL},JIRA_BASE_URL=https://your-jira.example.com,JIRA_PROJECT_KEY=OPS,JIRA_APPROVAL_ISSUE_TYPE=Task" \
  --set-secrets="JIRA_BEARER_TOKEN=JIRA_BEARER_TOKEN:latest" \
  --project="${PROJECT_ID}"
```

---

## 9. Wire the Services Together

After both deployments, verify the gateway has the correct Linux MCP URL:

```bash
gcloud run services describe command-gateway \
  --region="${REGION}" \
  --format="value(spec.template.spec.containers[0].env)"
```

If `LINUX_MCP_URL` is wrong or missing, update it:

```bash
gcloud run services update command-gateway \
  --region="${REGION}" \
  --update-env-vars="LINUX_MCP_URL=${LINUX_MCP_URL}" \
  --project="${PROJECT_ID}"
```

---

## 10. Smoke Test

### Get the gateway URL

```bash
export GATEWAY_URL="$(gcloud run services describe command-gateway \
  --region="${REGION}" \
  --format='value(status.url)')"

echo "Gateway URL: ${GATEWAY_URL}"
```

### Obtain an identity token

```bash
export TOKEN=$(gcloud auth print-identity-token)
```

### Initialize MCP session and capture session ID

```bash
GATEWAY_SESSION_ID=$(curl -s -D - -X POST "${GATEWAY_URL}/mcp" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}' \
  | grep -i "mcp-session-id" | awk '{print $2}' | tr -d '\r')

echo "Session ID: ${GATEWAY_SESSION_ID}"
```

### Submit a READ_ONLY operation

```bash
curl -s -X POST "${GATEWAY_URL}/mcp" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${GATEWAY_SESSION_ID}" \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"submit_operation",
      "arguments":{
        "ticket_id":"INC-SMOKE-001",
        "technology":"linux",
        "hostname":"secgcpagent01",
        "command":"uptime",
        "reason":"smoke test"
      }
    }
  }' | grep '^data:' | sed 's/^data: //' | python3 -m json.tool
```

Expected: `"status": "success"` with `uptime` output in the result.

### Check gateway status

```bash
curl -s -X POST "${GATEWAY_URL}/mcp" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${GATEWAY_SESSION_ID}" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_gateway_status","arguments":{}}}' \
  | grep '^data:' | sed 's/^data: //' | python3 -m json.tool
```

---

## 11. Redeployment (Updates)

To push a code change:

```bash
# 1. Rebuild and push the image
docker build -f gateway/Dockerfile -t "${GATEWAY_IMAGE}" . && docker push "${GATEWAY_IMAGE}"

# 2. Trigger a new revision (Cloud Run picks up the new image)
gcloud run services update command-gateway \
  --image="${GATEWAY_IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}"
```

If you use a fixed tag like `latest`, Cloud Run may cache the old image. Either use a unique tag per build (`git rev-parse --short HEAD`) or force a new revision:

```bash
gcloud run deploy command-gateway \
  --image="${GATEWAY_IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}"
```

---

## 12. Teardown

```bash
gcloud run services delete linux-mcp --region="${REGION}" --project="${PROJECT_ID}" --quiet
gcloud run services delete command-gateway --region="${REGION}" --project="${PROJECT_ID}" --quiet

# Optional: delete service accounts
gcloud iam service-accounts delete "${GATEWAY_SA}" --project="${PROJECT_ID}" --quiet
gcloud iam service-accounts delete "${LINUX_MCP_SA}" --project="${PROJECT_ID}" --quiet

# Optional: delete the Artifact Registry repo (removes all images)
gcloud artifacts repositories delete "${REPO}" --location="${REGION}" --project="${PROJECT_ID}" --quiet
```

---

## Terraform (Next Step)

The `infra/terraform/` directory contains the equivalent of all the above as code. Once you are happy with the manual setup, run:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your values
terraform init
terraform plan
terraform apply
```

This will bring IAM, service accounts, and Cloud Run services under version-controlled infrastructure.
