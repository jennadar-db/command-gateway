#!/usr/bin/env bash
set -euo pipefail

# One-command deploy for linux-mcp:
# 1) build local image (proxy-aware)
# 2) push image to Artifact Registry
# 3) deploy/update Cloud Run service

PROJECT_ID="${PROJECT_ID:-dbg-corpit-security-dev-ae}"
REGION="${REGION:-europe-west3}"
REPO="${REPO:-command-gateway}"
SERVICE="${SERVICE:-linux-mcp}"
PORT="${PORT:-9001}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Org-policy-sensitive network settings; adjust to your platform rules.
INGRESS="${INGRESS:-internal}"
VPC_CONNECTOR="${VPC_CONNECTOR:-}"
VPC_EGRESS="${VPC_EGRESS:-all-traffic}"
AUTH_MODE="${AUTH_MODE:-no-allow-unauthenticated}"

TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:${TAG}}"

echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE}"
echo "Image: ${IMAGE}"

gcloud config set project "${PROJECT_ID}" >/dev/null
gcloud config set run/region "${REGION}" >/dev/null

echo "Configuring docker auth for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null

BUILD_ARGS=()
if [[ -n "${HTTP_PROXY:-}" ]]; then
  BUILD_ARGS+=(--build-arg "HTTP_PROXY=${HTTP_PROXY}")
  BUILD_ARGS+=(--build-arg "http_proxy=${HTTP_PROXY}")
fi
if [[ -n "${HTTPS_PROXY:-}" ]]; then
  BUILD_ARGS+=(--build-arg "HTTPS_PROXY=${HTTPS_PROXY}")
  BUILD_ARGS+=(--build-arg "https_proxy=${HTTPS_PROXY}")
fi
if [[ -n "${NO_PROXY:-}" ]]; then
  BUILD_ARGS+=(--build-arg "NO_PROXY=${NO_PROXY}")
  BUILD_ARGS+=(--build-arg "no_proxy=${NO_PROXY}")
fi

echo "Building image..."
docker build -f linux_mcp/Dockerfile -t "${IMAGE}" . "${BUILD_ARGS[@]}"

echo "Pushing image..."
docker push "${IMAGE}"

DEPLOY_ARGS=(
  run deploy "${SERVICE}"
  --image="${IMAGE}"
  --region="${REGION}"
  --platform=managed
  --port="${PORT}"
  --set-env-vars="LOG_LEVEL=${LOG_LEVEL}"
)

if [[ "${AUTH_MODE}" == "allow-unauthenticated" ]]; then
  DEPLOY_ARGS+=(--allow-unauthenticated)
else
  DEPLOY_ARGS+=(--no-allow-unauthenticated)
fi

if [[ -n "${INGRESS}" ]]; then
  DEPLOY_ARGS+=(--ingress="${INGRESS}")
fi

if [[ -n "${VPC_CONNECTOR}" ]]; then
  DEPLOY_ARGS+=(--vpc-connector="${VPC_CONNECTOR}")
  DEPLOY_ARGS+=(--vpc-egress="${VPC_EGRESS}")
fi

echo "Deploying to Cloud Run..."
gcloud "${DEPLOY_ARGS[@]}"

URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
echo "Deploy complete. Service URL: ${URL}"
