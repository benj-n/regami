#!/bin/bash
# Regami Staging Deployment Script
# Deploys to VM3-STAGING
#
# Prerequisites:
#   - SSH access to staging VM configured in ~/.ssh/config as 'regami-staging'
#   - Docker and Docker Compose installed on the VM
#   - .env file configured on the VM
#
# Usage:
#   ./deploy-staging.sh [image_tag]

set -euo pipefail

IMAGE_TAG="${1:-latest}"
STAGING_HOST="${STAGING_HOST:-regami-staging}"
REMOTE_DIR="/opt/regami"

echo "=== Regami Staging Deployment ==="
echo "Image tag: $IMAGE_TAG"
echo "Target: $STAGING_HOST"
echo ""

# Confirm deployment
read -p "Deploy to staging? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Step 1: Pull latest images from GHCR..."
ssh "$STAGING_HOST" "docker pull ghcr.io/benj-n/regami-api:$IMAGE_TAG"
ssh "$STAGING_HOST" "docker pull ghcr.io/benj-n/regami-web:$IMAGE_TAG"

echo ""
echo "Step 2: Update IMAGE_TAG in environment..."
ssh "$STAGING_HOST" "cd $REMOTE_DIR && sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=$IMAGE_TAG/' .env"

echo ""
echo "Step 3: Restart services with new images..."
ssh "$STAGING_HOST" "cd $REMOTE_DIR && docker compose down && docker compose up -d"

echo ""
echo "Step 4: Wait for health check..."
sleep 10
ssh "$STAGING_HOST" "curl -sf http://localhost:8000/health || echo 'Health check pending...'"

echo ""
echo "Step 5: Cleanup old images..."
ssh "$STAGING_HOST" "docker image prune -f"

echo ""
echo "=== Staging deployment complete! ==="
echo "URL: https://staging.regami.com"
