#!/bin/bash
# Regami Production Deployment Script
# Rolling deployment to VM1-PROD and VM2-PROD with zero downtime
#
# Prerequisites:
#   - SSH access to production VMs configured as 'regami-prod-1' and 'regami-prod-2'
#   - Docker and Docker Compose installed on both VMs
#   - .env file configured on both VMs
#   - External HAProxy configured for both backends
#
# Usage:
#   ./deploy-production.sh [image_tag]
#
# Deployment order:
#   1. Deploy to standby VM (VM2)
#   2. Verify health
#   3. Deploy to active VM (VM1)
#   4. Verify health

set -euo pipefail

IMAGE_TAG="${1:-latest}"
PROD_HOST_1="${PROD_HOST_1:-regami-prod-1}"
PROD_HOST_2="${PROD_HOST_2:-regami-prod-2}"
REMOTE_DIR="/opt/regami"

echo "=== Regami Production Deployment ==="
echo "Image tag: $IMAGE_TAG"
echo "Targets: $PROD_HOST_1 (active), $PROD_HOST_2 (standby)"
echo ""

# Confirm deployment
echo "⚠️  WARNING: This will deploy to PRODUCTION"
read -p "Are you sure? Type 'yes' to continue: " -r
if [[ "$REPLY" != "yes" ]]; then
    echo "Deployment cancelled."
    exit 0
fi

deploy_to_host() {
    local host="$1"
    local name="$2"

    echo ""
    echo "=== Deploying to $name ($host) ==="

    echo "Pulling images..."
    ssh "$host" "docker pull ghcr.io/benj-n/regami-api:$IMAGE_TAG"
    ssh "$host" "docker pull ghcr.io/benj-n/regami-web:$IMAGE_TAG"

    echo "Updating IMAGE_TAG..."
    ssh "$host" "cd $REMOTE_DIR && sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=$IMAGE_TAG/' .env"

    echo "Restarting services..."
    ssh "$host" "cd $REMOTE_DIR && docker compose down && docker compose up -d"

    echo "Waiting for services to start..."
    sleep 15

    echo "Health check..."
    if ! ssh "$host" "curl -sf http://localhost:8000/health"; then
        echo "❌ Health check failed on $name!"
        return 1
    fi

    echo "Checking Patroni status..."
    ssh "$host" "curl -sf http://localhost:8008/health || echo 'Patroni health pending'"

    echo "Cleaning up old images..."
    ssh "$host" "docker image prune -f"

    echo "✅ $name deployment complete"
}

echo ""
echo "Step 1: Deploy to standby (VM2) first..."
deploy_to_host "$PROD_HOST_2" "VM2-STANDBY"

echo ""
echo "Step 2: Verify standby is healthy before continuing..."
sleep 5
if ! ssh "$PROD_HOST_2" "curl -sf http://localhost:8000/health"; then
    echo "❌ Standby health check failed! Aborting deployment."
    echo "Active VM ($PROD_HOST_1) was NOT touched."
    exit 1
fi

echo ""
echo "Step 3: Deploy to active (VM1)..."
deploy_to_host "$PROD_HOST_1" "VM1-ACTIVE"

echo ""
echo "=== Production deployment complete! ==="
echo ""
echo "Verify:"
echo "  - https://regami.com"
echo "  - https://api.regami.com/health"
echo ""
echo "Check Patroni cluster status:"
echo "  ssh $PROD_HOST_1 'curl -s http://localhost:8008/cluster | jq'"
