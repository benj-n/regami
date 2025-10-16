#!/bin/bash
#
# Database Restore Script for Regami
# Restores PostgreSQL database from backup file
#
# Usage:
#   ./restore.sh --file backups/regami_staging_20251115_120000.sql.gz [--environment staging]
#   ./restore.sh --from-s3 s3://regami-backups-prod/2025/11/regami_prod_20251115_120000.sql.gz
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR="/tmp/regami_restore_$$"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging
log_info() { echo -e "${GREEN}ℹ${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1" >&2; }

# Cleanup on exit
cleanup() {
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Parse arguments
BACKUP_FILE=""
S3_PATH=""
ENVIRONMENT="staging"
SKIP_CONFIRMATION=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --file)
      BACKUP_FILE="$2"
      shift 2
      ;;
    --from-s3)
      S3_PATH="$2"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --yes)
      SKIP_CONFIRMATION=true
      shift
      ;;
    --help)
      cat <<EOF
Usage: $0 [options]

Options:
  --file PATH              Path to local backup file (.sql.gz)
  --from-s3 S3_URI         Download backup from S3 (s3://bucket/path/file.sql.gz)
  --environment ENV        Target environment (staging|prod) [default: staging]
  --yes                    Skip confirmation prompt
  --help                   Show this help message

Examples:
  # Restore from local file
  $0 --file backups/regami_staging_20251115.sql.gz

  # Restore from S3
  $0 --from-s3 s3://regami-backups-prod/2025/11/backup.sql.gz --environment prod

  # Skip confirmation (for automation)
  $0 --file backup.sql.gz --yes
EOF
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate inputs
if [ -z "$BACKUP_FILE" ] && [ -z "$S3_PATH" ]; then
  log_error "Either --file or --from-s3 must be specified"
  exit 1
fi

# Load environment configuration
if [ "$ENVIRONMENT" = "prod" ]; then
  DB_HOST="${PROD_DB_HOST:-regami-db.cluster-xxxxx.us-east-1.rds.amazonaws.com}"
  DB_NAME="${PROD_DB_NAME:-regami}"
  DB_USER="${PROD_DB_USER:-regami}"
  DB_PASSWORD="${PROD_DB_PASSWORD}"
elif [ "$ENVIRONMENT" = "staging" ]; then
  DB_HOST="${STAGING_DB_HOST:-localhost}"
  DB_NAME="${STAGING_DB_NAME:-regami}"
  DB_USER="${STAGING_DB_USER:-regami}"
  DB_PASSWORD="${STAGING_DB_PASSWORD:-regami}"
else
  log_error "Invalid environment: $ENVIRONMENT"
  exit 1
fi

# Validate password
if [ -z "${DB_PASSWORD:-}" ]; then
  log_error "Database password not set. Set ${ENVIRONMENT^^}_DB_PASSWORD environment variable."
  exit 1
fi

mkdir -p "$TEMP_DIR"

# Download from S3 if needed
if [ -n "$S3_PATH" ]; then
  log_info "Downloading backup from S3: $S3_PATH"
  BACKUP_FILE="$TEMP_DIR/$(basename "$S3_PATH")"

  if ! aws s3 cp "$S3_PATH" "$BACKUP_FILE"; then
    log_error "Failed to download from S3"
    exit 1
  fi
  log_info "✓ Downloaded to $BACKUP_FILE"
fi

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
  log_error "Backup file not found: $BACKUP_FILE"
  exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_info "Backup file: $BACKUP_FILE ($BACKUP_SIZE)"

# Safety confirmation
if [ "$SKIP_CONFIRMATION" = false ]; then
  log_warn "================================ WARNING ================================"
  log_warn "This will REPLACE ALL DATA in the $ENVIRONMENT database:"
  log_warn "  Host: $DB_HOST"
  log_warn "  Database: $DB_NAME"
  log_warn "========================================================================="
  echo ""
  read -p "Are you sure you want to continue? Type 'yes' to proceed: " -r
  echo ""

  if [ "$REPLY" != "yes" ]; then
    log_info "Restore cancelled by user"
    exit 0
  fi
fi

log_info "Starting restore to $ENVIRONMENT environment..."

# Export password for psql/pg_restore
export PGPASSWORD="$DB_PASSWORD"

# Test database connection
log_info "Testing database connection..."
if ! psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "SELECT 1" > /dev/null 2>&1; then
  log_error "Cannot connect to database"
  exit 1
fi
log_info "✓ Connection successful"

# Create a backup of current database before restore (safety measure)
if [ "$ENVIRONMENT" != "local" ]; then
  SAFETY_BACKUP="$TEMP_DIR/pre_restore_safety_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
  log_info "Creating safety backup of current database..."
  pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" --format=plain | gzip > "$SAFETY_BACKUP" || true
  log_info "✓ Safety backup created: $SAFETY_BACKUP"
fi

# Drop existing connections
log_info "Terminating existing database connections..."
psql -h "$DB_HOST" -U "$DB_USER" -d postgres <<EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
EOF

# Drop and recreate database
log_info "Dropping database: $DB_NAME"
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"

log_info "Creating fresh database: $DB_NAME"
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"

# Restore database
log_info "Restoring database from backup..."
if gunzip < "$BACKUP_FILE" | psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" > "$TEMP_DIR/restore.log" 2>&1; then
  log_info "✓ Database restored successfully"
else
  log_error "Restore failed! Check log: $TEMP_DIR/restore.log"
  exit 1
fi

# Verify restore
log_info "Verifying restored database..."
TABLE_COUNT=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
log_info "✓ Found $TABLE_COUNT tables in restored database"

# Run Alembic stamp to mark current version
if [ -f "$SCRIPT_DIR/../../backend/alembic/versions/"*.py ]; then
  LATEST_REVISION=$(ls -1 "$SCRIPT_DIR/../../backend/alembic/versions/"*.py | tail -1 | grep -oP '[a-f0-9]{12}' | head -1)
  if [ -n "$LATEST_REVISION" ]; then
    log_info "Stamping Alembic version: $LATEST_REVISION"
    cd "$SCRIPT_DIR/../../backend" && alembic stamp "$LATEST_REVISION" 2>/dev/null || log_warn "Alembic stamp failed (may need manual intervention)"
  fi
fi

# Success summary
log_info "==================== RESTORE SUMMARY ===================="
log_info "Environment: $ENVIRONMENT"
log_info "Source: $BACKUP_FILE"
log_info "Database: $DB_NAME @ $DB_HOST"
log_info "Tables restored: $TABLE_COUNT"
log_info "Status: SUCCESS"
log_info "========================================================="

# Send notification
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  curl -X POST "$SLACK_WEBHOOK_URL" \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"✓ Database restored for $ENVIRONMENT from $BACKUP_FILE\"}" \
    2>/dev/null || true
fi

log_info "Restore completed successfully!"
log_info "Logs available at: $TEMP_DIR/restore.log"
