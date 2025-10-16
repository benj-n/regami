#!/bin/bash
#
# Database Backup Script for Regami
# Creates automated backups of PostgreSQL database with rotation
#
# Usage:
#   ./backup.sh [--environment prod|staging] [--retention-days 7]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/../backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-7}"
ENVIRONMENT="${1:-staging}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}ℹ${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1" >&2; }

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [--environment prod|staging] [--retention-days 7]"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

log_info "Starting backup for environment: $ENVIRONMENT"
log_info "Retention policy: $RETENTION_DAYS days"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Load environment-specific configuration
if [ "$ENVIRONMENT" = "prod" ]; then
  DB_HOST="${PROD_DB_HOST:-regami-db.cluster-xxxxx.us-east-1.rds.amazonaws.com}"
  DB_NAME="${PROD_DB_NAME:-regami}"
  DB_USER="${PROD_DB_USER:-regami}"
  DB_PASSWORD="${PROD_DB_PASSWORD}"
  S3_BUCKET="${BACKUP_S3_BUCKET:-regami-backups-prod}"
elif [ "$ENVIRONMENT" = "staging" ]; then
  DB_HOST="${STAGING_DB_HOST:-regami-staging-db.cluster-xxxxx.us-east-1.rds.amazonaws.com}"
  DB_NAME="${STAGING_DB_NAME:-regami}"
  DB_USER="${STAGING_DB_USER:-regami}"
  DB_PASSWORD="${STAGING_DB_PASSWORD}"
  S3_BUCKET="${BACKUP_S3_BUCKET:-regami-backups-staging}"
else
  log_error "Invalid environment: $ENVIRONMENT (must be 'prod' or 'staging')"
  exit 1
fi

# Validate required variables
if [ -z "${DB_PASSWORD:-}" ]; then
  log_error "Database password not set. Set ${ENVIRONMENT^^}_DB_PASSWORD environment variable."
  exit 1
fi

# Generate backup filename
BACKUP_FILE="$BACKUP_DIR/regami_${ENVIRONMENT}_${TIMESTAMP}.sql.gz"
BACKUP_METADATA="$BACKUP_DIR/regami_${ENVIRONMENT}_${TIMESTAMP}.json"

log_info "Creating backup: $(basename "$BACKUP_FILE")"

# Create database backup
export PGPASSWORD="$DB_PASSWORD"
if pg_dump \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --format=plain \
  --no-owner \
  --no-acl \
  --verbose \
  | gzip > "$BACKUP_FILE"; then

  BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  log_info "✓ Backup created successfully ($BACKUP_SIZE)"
else
  log_error "Backup failed!"
  rm -f "$BACKUP_FILE"
  exit 1
fi

# Create metadata file
cat > "$BACKUP_METADATA" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "environment": "$ENVIRONMENT",
  "database": "$DB_NAME",
  "host": "$DB_HOST",
  "size_bytes": $(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE"),
  "filename": "$(basename "$BACKUP_FILE")",
  "checksum": "$(shasum -a 256 "$BACKUP_FILE" | cut -d' ' -f1)"
}
EOF

log_info "Metadata saved: $(basename "$BACKUP_METADATA")"

# Upload to S3 (if AWS CLI is available and bucket is configured)
if command -v aws &> /dev/null && [ -n "${S3_BUCKET:-}" ]; then
  log_info "Uploading to S3: s3://$S3_BUCKET/"

  if aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/$(date +%Y)/$(date +%m)/" \
    --storage-class STANDARD_IA \
    --metadata "environment=$ENVIRONMENT,timestamp=$TIMESTAMP"; then
    log_info "✓ Uploaded to S3"

    # Upload metadata
    aws s3 cp "$BACKUP_METADATA" "s3://$S3_BUCKET/$(date +%Y)/$(date +%m)/"
  else
    log_warn "S3 upload failed, backup is only stored locally"
  fi
else
  log_warn "AWS CLI not available or S3 bucket not configured, skipping upload"
fi

# Cleanup old local backups
log_info "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "regami_${ENVIRONMENT}_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "regami_${ENVIRONMENT}_*.json" -mtime +$RETENTION_DAYS -delete
log_info "✓ Cleanup complete"

# Summary
log_info "==================== BACKUP SUMMARY ===================="
log_info "Environment: $ENVIRONMENT"
log_info "Backup file: $BACKUP_FILE"
log_info "Size: $BACKUP_SIZE"
log_info "Status: SUCCESS"
log_info "========================================================"

# Send notification (optional)
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  curl -X POST "$SLACK_WEBHOOK_URL" \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"✓ Database backup completed for $ENVIRONMENT: $BACKUP_SIZE\"}" \
    2>/dev/null || true
fi

log_info "Backup completed successfully!"
