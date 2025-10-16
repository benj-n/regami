#!/bin/bash
# Sync Let's Encrypt certificates between production VMs
# Run on VM1 (active) to push certs to VM2 (standby)
#
# Prerequisites:
#   - SSH key access from VM1 to VM2
#   - Caddy running on both VMs
#
# Usage:
#   ./sync-certs.sh
#   or via cron (see setup-production.sh)

set -euo pipefail

# Configuration
REMOTE_HOST="${REMOTE_HOST:-regami-prod-2}"
CERT_DIR="/var/lib/docker/volumes/regami_caddy_data/_data"
REMOTE_CERT_DIR="$CERT_DIR"

# Check if we're the active node (has certs)
if [[ ! -d "$CERT_DIR" ]]; then
    echo "Certificate directory not found: $CERT_DIR"
    echo "This script should run on the active node."
    exit 1
fi

echo "$(date): Syncing certificates to $REMOTE_HOST..."

# Sync certificates using rsync
rsync -avz --delete \
    "$CERT_DIR/" \
    "$REMOTE_HOST:$REMOTE_CERT_DIR/"

if [[ $? -eq 0 ]]; then
    echo "$(date): Certificate sync completed successfully"

    # Reload Caddy on remote to pick up new certs
    ssh "$REMOTE_HOST" "docker exec regami-caddy caddy reload --config /etc/caddy/Caddyfile" 2>/dev/null || true
else
    echo "$(date): Certificate sync failed!"
    exit 1
fi
