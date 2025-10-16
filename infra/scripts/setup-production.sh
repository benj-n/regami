#!/bin/bash
# Regami Production VM Setup Script
# Additional setup for production VMs (VM1, VM2)
#
# Prerequisites:
#   - Base setup completed (setup-vm.sh)
#   - SSH access between VM1 and VM2 for syncing

set -euo pipefail

echo "=== Regami Production VM Setup ==="
echo ""

# Check if base setup was done
if [[ ! -d /opt/regami ]]; then
    echo "Error: Base setup not completed. Run setup-vm.sh first."
    exit 1
fi

echo "Step 1: Open additional ports for clustering..."
ufw allow 2379/tcp  # etcd client
ufw allow 2380/tcp  # etcd peer
ufw allow 5432/tcp  # PostgreSQL
ufw allow 8008/tcp  # Patroni REST API
ufw allow 9000/tcp  # MinIO API
ufw reload

echo ""
echo "Step 2: Copy production configuration..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/../production/docker-compose.yml" ]]; then
    cp "$SCRIPT_DIR/../production/docker-compose.yml" /opt/regami/
    cp "$SCRIPT_DIR/../production/Caddyfile" /opt/regami/
    cp "$SCRIPT_DIR/../production/patroni.yml" /opt/regami/
    cp "$SCRIPT_DIR/../production/.env.example" /opt/regami/.env
    echo "Configuration files copied to /opt/regami/"
else
    echo "Warning: Production config files not found. Copy manually."
fi

echo ""
echo "Step 3: Setup cron jobs for syncing..."
# Certificate sync (every hour)
cat > /etc/cron.d/regami-sync << 'EOF'
# Sync certificates between production VMs
0 * * * * root /opt/regami/scripts/sync-certs.sh >> /var/log/regami-sync.log 2>&1

# Backup PostgreSQL daily at 2 AM
0 2 * * * root /opt/regami/scripts/backup-postgres.sh >> /var/log/regami-backup.log 2>&1

# Sync MinIO buckets every 4 hours
0 */4 * * * root /opt/regami/scripts/sync-minio.sh >> /var/log/regami-minio-sync.log 2>&1
EOF

echo ""
echo "Step 4: Create scripts directory..."
mkdir -p /opt/regami/scripts

echo ""
echo "=== Production VM setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit /opt/regami/.env with actual values"
echo "  2. Set HOSTNAME and HOST_IP for this VM"
echo "  3. Configure ETCD_INITIAL_CLUSTER for both VMs"
echo "  4. Setup SSH keys between VM1 and VM2 for cert/backup sync"
echo "  5. Run: cd /opt/regami && docker compose up -d"
