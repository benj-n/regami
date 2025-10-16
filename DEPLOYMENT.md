# Self-Hosted Deployment Guide

Complete guide for deploying Regami to self-hosted infrastructure with high availability.

## Architecture Overview

### Production Environment (2 VMs - Active/Passive)

```
                    ┌─────────────────┐
                    │  External       │
                    │  HAProxy        │
                    │  (Load Balancer)│
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       ┌──────▼──────┐              ┌──────▼──────┐
       │  VM1-PROD   │              │  VM2-PROD   │
       │  (Active)   │◄────────────►│  (Standby)  │
       │             │   Patroni    │             │
       │  - Caddy    │   Sync       │  - Caddy    │
       │  - API      │              │  - API      │
       │  - Web      │   MinIO      │  - Web      │
       │  - Patroni  │◄────────────►│  - Patroni  │
       │  - etcd     │   mc mirror  │  - etcd     │
       │  - MinIO    │              │  - MinIO    │
       │  - pgBouncer│              │  - pgBouncer│
       └─────────────┘              └─────────────┘
```

### Staging Environment (1 VM - Standalone)

```
       ┌─────────────┐
       │  VM3-STAGING│
       │             │
       │  - Caddy    │
       │  - API      │
       │  - Web      │
       │  - PostgreSQL│
       │  - MinIO    │
       └─────────────┘
```

### VM Specifications

| VM | Role | CPU | RAM | Disk |
|----|------|-----|-----|------|
| VM1-PROD | Primary (Active) | 4 vCPU | 4 GB | 50 GB SSD |
| VM2-PROD | Secondary (Standby) | 4 vCPU | 4 GB | 50 GB SSD |
| VM3-STAGING | Staging | 4 vCPU | 4 GB | 30 GB SSD |

---

## Prerequisites

### On Your Local Machine

```bash
# Required tools
ssh --version      # SSH client
docker --version   # Docker (for testing)
git --version      # Git

# GitHub CLI (for GHCR authentication)
gh --version
gh auth login
```

### On Each VM

The setup scripts will install these, but VMs need:
- Ubuntu 22.04 LTS or newer
- SSH access with sudo privileges
- Open ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)

---

## Initial Setup

### Step 1: Configure SSH Access

Create `~/.ssh/config` on your local machine:

```ssh-config
Host regami-prod1
    HostName <VM1_IP>
    User deploy
    IdentityFile ~/.ssh/regami_deploy

Host regami-prod2
    HostName <VM2_IP>
    User deploy
    IdentityFile ~/.ssh/regami_deploy

Host regami-staging
    HostName <VM3_IP>
    User deploy
    IdentityFile ~/.ssh/regami_deploy
```

### Step 2: Set Up VMs

```bash
# Clone the repository
git clone https://github.com/benj-n/regami.git
cd regami

# Set up each VM (run from your local machine)
./infra/scripts/setup-vm.sh regami-prod1
./infra/scripts/setup-vm.sh regami-prod2
./infra/scripts/setup-staging.sh regami-staging
```

### Step 3: Configure Environment Files

SSH to each production VM and create `/opt/regami/.env`:

```bash
ssh regami-prod1
sudo nano /opt/regami/.env
```

Use `infra/production/.env.example` as a template. Key settings:

```bash
# Database
POSTGRES_PASSWORD=<generate-secure-password>

# Patroni (etcd)
PATRONI_SUPERUSER_PASSWORD=<generate-secure-password>
PATRONI_REPLICATION_PASSWORD=<generate-secure-password>
ETCD_TOKEN=<generate-unique-token>

# API
SECRET_KEY=<generate-32-char-secret>
DATABASE_URL=postgresql://regami:${POSTGRES_PASSWORD}@pgbouncer:6432/regami

# MinIO
MINIO_ROOT_USER=regami
MINIO_ROOT_PASSWORD=<generate-secure-password>

# Node identification
NODE_NAME=regami-prod1  # or regami-prod2
PATRONI_NAME=pg1        # or pg2
ETCD_NAME=etcd1         # or etcd2
```

For staging, use `infra/staging/.env.example`.

### Step 4: Configure External HAProxy

Provide your network administrator with the HAProxy configuration from:
`infra/production/HAPROXY_CONFIG.md`

---

## Deployment

### Build and Push Images

Images are automatically built on push to `main` via GitHub Actions.

Manual build (if needed):

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build and push
docker build -t ghcr.io/benj-n/regami-api:latest ./backend
docker build -t ghcr.io/benj-n/regami-web:latest ./web
docker push ghcr.io/benj-n/regami-api:latest
docker push ghcr.io/benj-n/regami-web:latest
```

### Deploy to Staging

```bash
./infra/scripts/deploy.sh staging
```

This will:
1. Pull latest images from GHCR
2. Run database migrations
3. Restart containers with zero-downtime

### Deploy to Production

```bash
./infra/scripts/deploy.sh production
```

This performs a rolling deployment:
1. Drain VM1 from HAProxy
2. Update VM1
3. Health check VM1
4. Switch traffic to VM1
5. Update VM2
6. Restore full cluster

---

## High Availability

### PostgreSQL Clustering (Patroni)

Patroni manages PostgreSQL replication with automatic failover:

```bash
# Check cluster status
ssh regami-prod1 "docker exec patroni patronictl list"

# Force failover (if needed)
ssh regami-prod1 "docker exec patroni patronictl switchover"
```

### etcd Cluster (2-node)

**Important**: A 2-node etcd cluster cannot automatically recover from split-brain.
See `infra/production/RECOVERY.md` for manual recovery procedures.

```bash
# Check etcd health
ssh regami-prod1 "docker exec etcd etcdctl endpoint health"

# Check cluster members
ssh regami-prod1 "docker exec etcd etcdctl member list"
```

### MinIO Replication

Files are synced between VMs using `mc mirror`:

```bash
# Manual sync (runs automatically via cron)
./infra/scripts/sync-minio.sh

# Check sync status
ssh regami-prod1 "docker exec minio mc diff minio/regami remote/regami"
```

### SSL Certificate Sharing

Let's Encrypt certificates are synced between VMs:

```bash
# Sync certificates from active to standby
./infra/scripts/sync-certs.sh regami-prod1 regami-prod2
```

---

## Maintenance

### Database Backup

Backups run daily via cron. Manual backup:

```bash
./infra/scripts/backup-postgres.sh regami-prod1
```

Backups are stored in `/opt/regami/backups/` on both VMs.

### Database Restore

```bash
# Restore from backup
ssh regami-prod1 "cd /opt/regami && ./scripts/restore.sh backups/regami_20240115_120000.sql.gz"
```

### View Logs

```bash
# All services
ssh regami-prod1 "cd /opt/regami && docker compose logs -f"

# Specific service
ssh regami-prod1 "cd /opt/regami && docker compose logs -f api"
ssh regami-prod1 "cd /opt/regami && docker compose logs -f patroni"
```

### Restart Services

```bash
# Restart single service
ssh regami-prod1 "cd /opt/regami && docker compose restart api"

# Restart all services
ssh regami-prod1 "cd /opt/regami && docker compose restart"
```

---

## Troubleshooting

### Health Checks

```bash
# API health
curl -s https://api.regami.com/health

# Database health
ssh regami-prod1 "docker exec patroni patronictl list"

# All container status
ssh regami-prod1 "docker ps"
```

### Common Issues

#### API Returns 502 Bad Gateway

1. Check if API container is running:
   ```bash
   ssh regami-prod1 "docker ps | grep api"
   ```
2. Check API logs:
   ```bash
   ssh regami-prod1 "docker logs regami-api"
   ```

#### Database Connection Failed

1. Check Patroni cluster status:
   ```bash
   ssh regami-prod1 "docker exec patroni patronictl list"
   ```
2. Check pgBouncer:
   ```bash
   ssh regami-prod1 "docker logs pgbouncer"
   ```

#### Split-Brain Recovery

See `infra/production/RECOVERY.md` for step-by-step recovery procedures.

---

## Monitoring

### Basic Monitoring (Built-in)

- **Health endpoint**: `GET /health` returns API and database status
- **Docker stats**: `docker stats` for resource usage
- **Patroni dashboard**: `patronictl list` for database cluster status

### External Monitoring (Optional)

For production, consider:
- **Uptime monitoring**: UptimeRobot, Pingdom, or similar
- **Log aggregation**: Loki + Grafana or similar
- **Metrics**: Prometheus + Grafana (see `infra/monitoring/`)

---

## Security Checklist

- [ ] Change all default passwords in `.env` files
- [ ] Restrict SSH access (key-only, no root login)
- [ ] Configure firewall (UFW) to only allow 22, 80, 443
- [ ] Enable automatic security updates
- [ ] Set up log rotation
- [ ] Configure backup encryption
- [ ] Review HAProxy SSL settings with admin

---

## Infrastructure Files

```
infra/
├── production/
│   ├── docker-compose.yml    # Production HA stack
│   ├── patroni.yml           # PostgreSQL HA config
│   ├── Caddyfile            # Reverse proxy config
│   ├── .env.example         # Environment template
│   ├── RECOVERY.md          # Split-brain recovery
│   └── HAPROXY_CONFIG.md    # HAProxy config docs
├── staging/
│   ├── docker-compose.yml    # Staging stack
│   ├── Caddyfile            # Staging Caddy config
│   └── .env.example         # Staging env template
├── scripts/
│   ├── deploy.sh            # Main deployment script
│   ├── deploy-staging.sh    # Staging deployment
│   ├── deploy-production.sh # Production rolling deploy
│   ├── setup-vm.sh          # Base VM setup
│   ├── setup-production.sh  # Production setup
│   ├── setup-staging.sh     # Staging setup
│   ├── sync-certs.sh        # Certificate sync
│   ├── sync-minio.sh        # MinIO bucket sync
│   └── backup-postgres.sh   # Database backup
└── archive/
    └── terraform-aws-*/     # Archived AWS configs
```
