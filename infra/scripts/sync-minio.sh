#!/bin/bash
# Sync MinIO buckets between production VMs
# Run on VM1 (active) to mirror data to VM2 (standby)
#
# Prerequisites:
#   - MinIO Client (mc) installed and configured
#   - SSH access to remote VM
#
# Usage:
#   ./sync-minio.sh

set -euo pipefail

# Configuration
LOCAL_ALIAS="${LOCAL_ALIAS:-local}"
REMOTE_HOST="${REMOTE_HOST:-regami-prod-2}"
BUCKET="regami"

echo "$(date): Starting MinIO bucket sync to $REMOTE_HOST..."

# Check if mc is available in the minio container
if ! docker exec regami-minio mc --version &>/dev/null; then
    echo "Installing MinIO Client in container..."
    docker exec regami-minio wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/bin/mc
    docker exec regami-minio chmod +x /usr/bin/mc
fi

# Configure local MinIO alias
docker exec regami-minio mc alias set local http://localhost:9000 "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"

# Configure remote MinIO alias (via SSH tunnel or direct)
# Note: For cross-site sync, the remote MinIO must be accessible
# This example assumes direct network access; adjust for your network
REMOTE_MINIO_URL="http://${REMOTE_HOST}:9000"
docker exec regami-minio mc alias set remote "${REMOTE_MINIO_URL}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"

# Mirror the bucket
echo "Mirroring bucket ${BUCKET}..."
docker exec regami-minio mc mirror --overwrite "local/${BUCKET}" "remote/${BUCKET}"

if [[ $? -eq 0 ]]; then
    echo "$(date): MinIO sync completed successfully"
else
    echo "$(date): MinIO sync failed!"
    exit 1
fi
