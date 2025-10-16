#!/bin/bash
# Regami Deployment Script
# Main orchestrator for deploying Regami to VMs
#
# Usage:
#   ./deploy.sh [staging|production] [image_tag]
#
# Examples:
#   ./deploy.sh staging latest
#   ./deploy.sh production v1.2.3

set -euo pipefail

ENVIRONMENT="${1:-}"
IMAGE_TAG="${2:-latest}"

if [[ -z "$ENVIRONMENT" ]]; then
    echo "Usage: $0 [staging|production] [image_tag]"
    echo ""
    echo "Environments:"
    echo "  staging     - Deploy to VM3-STAGING"
    echo "  production  - Deploy to VM1-PROD and VM2-PROD"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$ENVIRONMENT" in
    staging)
        exec "$SCRIPT_DIR/deploy-staging.sh" "$IMAGE_TAG"
        ;;
    production)
        exec "$SCRIPT_DIR/deploy-production.sh" "$IMAGE_TAG"
        ;;
    *)
        echo "Error: Unknown environment '$ENVIRONMENT'"
        echo "Valid options: staging, production"
        exit 1
        ;;
esac
