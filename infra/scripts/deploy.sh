#!/usr/bin/env bash
# Deploy SANGAD via Coolify API
# Usage: ./infra/scripts/deploy.sh [environment] [tag]
set -euo pipefail

COOLIFY_URL="${COOLIFY_URL:-http://localhost:8000}"
COOLIFY_TOKEN="${COOLIFY_TOKEN:?Set COOLIFY_TOKEN environment variable}"
DEPLOY_ENV="${1:-production}"
TAG="${2:-main}"

echo "Triggering deploy of ${TAG} to ${DEPLOY_ENV}..."
APP_UUID=$(curl -sf -H "Authorization: Bearer ${COOLIFY_TOKEN}" "${COOLIFY_URL}/api/v1/applications" | jq -r ".[] | select(.name == \"sangad-${DEPLOY_ENV}\") | .uuid")
curl -sf -X POST -H "Authorization: Bearer ${COOLIFY_TOKEN}" -H "Content-Type: application/json" \
  -d "{\"git_hash\": \"${TAG}\"}" "${COOLIFY_URL}/api/v1/applications/${APP_UUID}/deploy"
echo "Deploy triggered."
