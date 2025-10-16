#!/bin/bash
# Regami Staging VM Setup Script
# Additional setup for staging VM (VM3)
#
# Prerequisites:
#   - Base setup completed (setup-vm.sh)

set -euo pipefail

echo "=== Regami Staging VM Setup ==="
echo ""

# Check if base setup was done
if [[ ! -d /opt/regami ]]; then
    echo "Error: Base setup not completed. Run setup-vm.sh first."
    exit 1
fi

echo "Step 1: Copy staging configuration..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/../staging/docker-compose.yml" ]]; then
    cp "$SCRIPT_DIR/../staging/docker-compose.yml" /opt/regami/
    cp "$SCRIPT_DIR/../staging/Caddyfile" /opt/regami/
    cp "$SCRIPT_DIR/../staging/.env.example" /opt/regami/.env
    echo "Configuration files copied to /opt/regami/"
else
    echo "Warning: Staging config files not found. Copy manually."
fi

echo ""
echo "Step 2: Setup daily backup cron..."
cat > /etc/cron.d/regami-backup << 'EOF'
# Backup PostgreSQL daily at 3 AM
0 3 * * * root docker exec regami-postgres pg_dump -U regami regami | gzip > /opt/regami/backups/postgres-$(date +\%Y\%m\%d).sql.gz 2>&1
# Keep only last 7 days of backups
0 4 * * * root find /opt/regami/backups -name "postgres-*.sql.gz" -mtime +7 -delete
EOF

mkdir -p /opt/regami/backups

echo ""
echo "=== Staging VM setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit /opt/regami/.env with actual values"
echo "  2. Set BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD"
echo "  3. Run: cd /opt/regami && docker compose up -d"
