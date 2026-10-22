#!/usr/bin/env bash
# Deploy SANGAD via Coolify API
# Usage: ./infra/scripts/deploy.sh [environment] [tag]
set -euo pipefail

COOLIFY_URL="${COOLIFY_URL:-http://localhost:8000}"
COOLIFY_TOKEN="${COOLIFY_TOKEN:?Set COOLIFY_TOKEN or pass it as the first argument}"
DEPLOY_ENV="${1:-production}"
TAG="${2:-main}"

echo "Triggering deploy of ${TAG} to ${DEPLOY_ENV}..."

# Get application UUID from Coolify
APP_UUID=$(curl -s -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
  "${COOLIFY_URL}/api/v1/applications" \
  | jq -r ".[] | select(.name == \"sangad-${DEPLOY_ENV}\") | .uuid")

if [ -z "${APP_UUID}" ]; then
  echo "Error: Could not find sangad-${DEPLOY_ENV} application"
  exit 1
fi

# Trigger deploy
curl -s -X POST \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"git_hash\": \"${TAG}\"}" \
  "${COOLIFY_URL}/api/v1/applications/${APP_UUID}/deploy"

echo "Deploy triggered. Check Coolify dashboard for progress."