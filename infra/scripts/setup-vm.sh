#!/bin/bash
# Regami VM Setup Script
# Base setup for all VMs (production and staging)
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/benj-n/regami/main/infra/scripts/setup-vm.sh | bash
#   or
#   ./setup-vm.sh
#
# Prerequisites:
#   - Ubuntu 22.04 or 24.04 LTS
#   - Root or sudo access

set -euo pipefail

echo "=== Regami VM Setup ==="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (or with sudo)"
    exit 1
fi

echo "Step 1: Update system packages..."
apt-get update
apt-get upgrade -y

echo ""
echo "Step 2: Install Docker..."
if ! command -v docker &> /dev/null; then
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    echo "Docker installed successfully"
else
    echo "Docker already installed"
fi

echo ""
echo "Step 3: Configure Docker..."
# Enable Docker to start on boot
systemctl enable docker
systemctl start docker

# Add current user to docker group (if not root)
if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG docker "$SUDO_USER"
    echo "Added $SUDO_USER to docker group"
fi

echo ""
echo "Step 4: Install useful tools..."
apt-get install -y \
    htop \
    vim \
    curl \
    wget \
    jq \
    unzip \
    rsync \
    fail2ban \
    ufw

echo ""
echo "Step 5: Configure firewall (UFW)..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw --force enable

echo ""
echo "Step 6: Configure fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

echo ""
echo "Step 7: Create application directory..."
mkdir -p /opt/regami
chown -R "${SUDO_USER:-root}:${SUDO_USER:-root}" /opt/regami

echo ""
echo "Step 8: Configure system limits for Docker..."
cat > /etc/security/limits.d/docker.conf << EOF
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
EOF

echo ""
echo "=== Base VM setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Configure SSH keys for GitHub Actions or manual deployment"
echo "  2. Copy docker-compose.yml and .env to /opt/regami/"
echo "  3. Run environment-specific setup (setup-production.sh or setup-staging.sh)"
echo ""
echo "Reboot recommended to apply all changes:"
echo "  sudo reboot"
