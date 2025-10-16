# Staging Environment Deployment Guide

Complete guide to deploy Regami to the staging environment (staging.regami.com) for testing before production.

## Overview

**Purpose:** Staging environment for testing features before production deployment.

**Domains:**
- Frontend: `https://staging.regami.com`
- API: `https://api.staging.regami.com`

**Architecture:** Simplified single-VM deployment with:
- Single PostgreSQL instance (no Patroni clustering)
- Single MinIO instance (no cross-site sync)
- Caddy for reverse proxy with automatic SSL
- Same Docker images as production

**VM Specifications:**
- 4 vCPU / 4 GB RAM / 30 GB SSD

### Basic Authentication

Staging environment can be protected with HTTP Basic Auth:
- Configure in Caddyfile using `basicauth` directive
- Credentials stored in `.env` file

---

## Prerequisites

- SSH access to staging VM
- GitHub Container Registry (GHCR) access
- Domain configured with DNS pointing to VM IP

---

## Infrastructure Setup

### Step 1: Configure SSH Access

Add to `~/.ssh/config` on your local machine:

```ssh-config
Host regami-staging
    HostName <STAGING_VM_IP>
    User deploy
    IdentityFile ~/.ssh/regami_deploy
```

### Step 2: Set Up the VM

```bash
# Clone the repository
git clone https://github.com/benj-n/regami.git
cd regami

# Run the staging setup script
./infra/scripts/setup-staging.sh regami-staging
```

This script will:
- Install Docker and Docker Compose
- Configure firewall (UFW)
- Set up automatic security updates
- Create the deployment directory at `/opt/regami`

### Step 3: Configure Environment

SSH to the staging VM and create the environment file:

```bash
ssh regami-staging
sudo nano /opt/regami/.env
```

Use `infra/staging/.env.example` as a template:

```bash
# API Configuration
SECRET_KEY=<generate-32-char-secret>
DATABASE_URL=postgresql://regami:${POSTGRES_PASSWORD}@postgres:5432/regami
CORS_ORIGINS=https://staging.regami.com

# Database
POSTGRES_USER=regami
POSTGRES_PASSWORD=<generate-secure-password>
POSTGRES_DB=regami

# MinIO (S3-compatible storage)
MINIO_ROOT_USER=regami
MINIO_ROOT_PASSWORD=<generate-secure-password>
S3_BUCKET_NAME=regami
S3_PUBLIC_BASE_URL=https://staging.regami.com/uploads

# Email (optional - use for testing)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Domain
DOMAIN=staging.regami.com
```

### Step 4: Copy Infrastructure Files

```bash
# Copy docker-compose and Caddyfile to the VM
scp infra/staging/docker-compose.yml regami-staging:/opt/regami/
scp infra/staging/Caddyfile regami-staging:/opt/regami/
```

### Step 5: Configure DNS

Point your domain to the staging VM IP:

```
staging.regami.com     A     <STAGING_VM_IP>
api.staging.regami.com A     <STAGING_VM_IP>
```

---

## Deployment

### Deploy to Staging

```bash
# From your local machine
./infra/scripts/deploy.sh staging
```

Or manually:

```bash
ssh regami-staging

cd /opt/regami

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull latest images
docker compose pull

# Run database migrations
docker compose run --rm api alembic upgrade head

# Start services
docker compose up -d
```

### Verify Deployment

```bash
# Check all containers are running
docker compose ps

# Check API health
curl -s https://api.staging.regami.com/health

# Check logs
docker compose logs -f
```

---

## Maintenance

### View Logs

```bash
ssh regami-staging "cd /opt/regami && docker compose logs -f"

# Specific service
ssh regami-staging "cd /opt/regami && docker compose logs -f api"
```

### Restart Services

```bash
ssh regami-staging "cd /opt/regami && docker compose restart"

# Specific service
ssh regami-staging "cd /opt/regami && docker compose restart api"
```

### Database Access

```bash
ssh regami-staging "cd /opt/regami && docker compose exec postgres psql -U regami -d regami"
```

### Backup Database

```bash
ssh regami-staging "cd /opt/regami && docker compose exec postgres pg_dump -U regami regami > backup.sql"
```

### Reset Database

```bash
ssh regami-staging
cd /opt/regami

# Stop services
docker compose down

# Remove database volume
docker volume rm regami_postgres_data

# Start fresh
docker compose up -d

# Run migrations
docker compose run --rm api alembic upgrade head
```

---

## Differences from Production

| Feature | Production | Staging |
|---------|------------|---------|
| VMs | 2 (Active/Passive) | 1 |
| PostgreSQL | Patroni HA cluster | Single instance |
| MinIO | Cross-site sync | Single instance |
| etcd | 2-node cluster | None |
| Load Balancer | External HAProxy | Direct Caddy |
| SSL | Shared between VMs | Local to VM |
| Backups | Daily to remote VM | Manual only |

---

## Troubleshooting

### SSL Certificate Issues

```bash
# Check Caddy logs
ssh regami-staging "cd /opt/regami && docker compose logs caddy"

# Force certificate renewal
ssh regami-staging "cd /opt/regami && docker compose restart caddy"
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
ssh regami-staging "cd /opt/regami && docker compose ps postgres"

# Check database logs
ssh regami-staging "cd /opt/regami && docker compose logs postgres"
```

### Container Won't Start

```bash
# Check container logs
ssh regami-staging "cd /opt/regami && docker compose logs api"

# Verify environment file
ssh regami-staging "cat /opt/regami/.env"
```

---

## Staging Files

```
infra/staging/
├── docker-compose.yml    # Simplified staging stack
├── Caddyfile            # Staging Caddy config
└── .env.example         # Environment template
```

---

## Related Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Full production deployment guide
- **[DEV.md](DEV.md)** - Local development setup
- **[infra/staging/](infra/staging/)** - Staging infrastructure files
