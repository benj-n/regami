#!/bin/bash
# PostgreSQL Backup Script for Regami Production
# Creates compressed backup and optionally syncs to remote VM
#
# Usage:
#   ./backup-postgres.sh
#   or via cron (see setup-production.sh)

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/regami/backups}"
REMOTE_HOST="${REMOTE_HOST:-regami-prod-2}"
REMOTE_BACKUP_DIR="$BACKUP_DIR"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="regami-postgres-${TIMESTAMP}.sql.gz"

echo "$(date): Starting PostgreSQL backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Get database credentials from environment or docker
if [[ -f /opt/regami/.env ]]; then
    source /opt/regami/.env
fi

# Create backup using pg_dump through docker
echo "Creating backup: $BACKUP_FILE"
docker exec regami-patroni pg_dump \
    -U "${POSTGRES_USER:-regami}" \
    -d "${POSTGRES_DB:-regami}" \
    --no-owner \
    --no-acl \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

if [[ $? -ne 0 ]]; then
    echo "$(date): Backup failed!"
    exit 1
fi

BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
echo "$(date): Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Sync to remote VM
if [[ -n "${REMOTE_HOST:-}" ]]; then
    echo "Syncing backup to $REMOTE_HOST..."
    ssh "$REMOTE_HOST" "mkdir -p $REMOTE_BACKUP_DIR"
    rsync -avz "${BACKUP_DIR}/${BACKUP_FILE}" "${REMOTE_HOST}:${REMOTE_BACKUP_DIR}/"

    if [[ $? -eq 0 ]]; then
        echo "$(date): Backup synced to remote"
    else
        echo "$(date): Remote sync failed (backup still saved locally)"
    fi
fi

# Cleanup old backups
echo "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "regami-postgres-*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

# Also cleanup on remote
if [[ -n "${REMOTE_HOST:-}" ]]; then
    ssh "$REMOTE_HOST" "find $REMOTE_BACKUP_DIR -name 'regami-postgres-*.sql.gz' -mtime '+${RETENTION_DAYS}' -delete" 2>/dev/null || true
fi

echo "$(date): Backup complete"

# List current backups
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/regami-postgres-*.sql.gz 2>/dev/null || echo "No backups found"
