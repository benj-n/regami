# Regami Deployment Quick Reference

Quick commands and checklists for deploying Regami to different environments.

## Quick Links

- **[DEV.md](DEV.md)** - Full local development guide
- **[STAGING.md](STAGING.md)** - Full staging deployment guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Full production deployment guide
- **[DOMAIN_CONFIG.md](DOMAIN_CONFIG.md)** - Domain configuration reference

---

## Local Development (5 minutes)

### Quick Start (No Docker)

```bash
# Backend
python3.12 -m venv .venv && source .venv/bin/activate
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd web && npm ci
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev

# Access at:
# Web: http://localhost:5173
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Docker Compose (Full Stack)

```bash
cd infra
docker compose up -d --build

# Access at:
# Web: http://localhost:5173
# API: http://localhost:8000
# MinIO: http://localhost:9001 (minioadmin/minioadmin)
# MailHog: http://localhost:8025
```

---

## Staging Deployment

### Prerequisites
- SSH access to staging VM (VM3-STAGING)
- GitHub token for GHCR access
- DNS configured for staging.regami.com

### Deploy to Staging
```bash
# One-command deployment
./infra/scripts/deploy.sh staging

# Or manually:
ssh regami-staging
cd /opt/regami
docker compose pull
docker compose run --rm api alembic upgrade head
docker compose up -d

# Verify
curl https://api.staging.regami.com/health
```

### Staging Management
```bash
# View logs
ssh regami-staging "cd /opt/regami && docker compose logs -f"

# Restart services
ssh regami-staging "cd /opt/regami && docker compose restart"

# Database access
ssh regami-staging "cd /opt/regami && docker compose exec postgres psql -U regami -d regami"
```

---

## Production Deployment

### Prerequisites Checklist
- [ ] SSH access to both production VMs
- [ ] HAProxy configured by network admin
- [ ] DNS configured for regami.com
- [ ] GitHub token for GHCR access
- [ ] Environment files configured on VMs

### Deploy to Production (Rolling)
```bash
# One-command rolling deployment
./infra/scripts/deploy.sh production

# This will:
# 1. Drain VM1 from HAProxy
# 2. Update VM1
# 3. Health check VM1
# 4. Switch traffic to VM1
# 5. Update VM2
# 6. Restore full cluster
```

### Manual Deployment
```bash
# Deploy to specific VM
ssh regami-prod1
cd /opt/regami
docker compose pull
docker compose run --rm api alembic upgrade head
docker compose up -d
```

### Production Health Checks
```bash
# API health
curl https://api.regami.com/health

# Patroni cluster status
ssh regami-prod1 "docker exec patroni patronictl list"

# etcd cluster status
ssh regami-prod1 "docker exec etcd etcdctl endpoint health"

# All containers
ssh regami-prod1 "docker ps"
```

---

## CI/CD

### Container Images

Images are automatically built and pushed to GHCR on push to `main`:
- `ghcr.io/benj-n/regami-api:latest`
- `ghcr.io/benj-n/regami-web:latest`

### CI Tests

```bash
# Run tests locally before push
pytest backend/tests -v
cd web && npm run test:run
```

### Setup GitHub Secrets
```bash
gh secret set GHCR_TOKEN --body "YOUR_GITHUB_TOKEN"
```

---

## Common Operations

### Database Backup
```bash
# Production backup
./infra/scripts/backup-postgres.sh regami-prod1

# Check backups
ssh regami-prod1 "ls -la /opt/regami/backups/"
```

### Certificate Sync
```bash
# Sync certs from active to standby
./infra/scripts/sync-certs.sh regami-prod1 regami-prod2
```

### MinIO Sync
```bash
# Sync files between VMs
./infra/scripts/sync-minio.sh
```

### Database Migrations
```bash
# Run migrations on staging
ssh regami-staging "cd /opt/regami && docker compose run --rm api alembic upgrade head"

# Run migrations on production (both VMs)
ssh regami-prod1 "cd /opt/regami && docker compose run --rm api alembic upgrade head"
```

---

## Emergency Procedures

### API Down
```bash
# Check containers
ssh regami-prod1 "docker ps"
ssh regami-prod1 "docker logs regami-api"

# Restart API
ssh regami-prod1 "cd /opt/regami && docker compose restart api"
```

### Database Issues
```bash
# Check Patroni status
ssh regami-prod1 "docker exec patroni patronictl list"

# Force failover (if needed)
ssh regami-prod1 "docker exec patroni patronictl switchover"

# Split-brain recovery
# See infra/production/RECOVERY.md
```

### Full Service Restart
```bash
ssh regami-prod1 "cd /opt/regami && docker compose restart"
ssh regami-prod2 "cd /opt/regami && docker compose restart"
```

---

## Environment Checklist

### Staging VM
- [ ] Docker installed
- [ ] `/opt/regami/.env` configured
- [ ] Docker Compose files in place
- [ ] GHCR login configured
- [ ] DNS pointing to VM

### Production VMs
- [ ] Docker installed on both VMs
- [ ] `/opt/regami/.env` configured on both VMs
- [ ] etcd cluster healthy
- [ ] Patroni cluster synchronized
- [ ] HAProxy health checks passing
- [ ] SSL certificates valid
- [ ] Backup cron job configured

---

## Quick References

### SSH Hosts
```bash
ssh regami-prod1    # Production VM1 (Active)
ssh regami-prod2    # Production VM2 (Standby)
ssh regami-staging  # Staging VM
```

### Key Directories
```
/opt/regami/           # Main application directory
/opt/regami/backups/   # Database backups
/opt/regami/caddy/     # SSL certificates
/opt/regami/minio/     # MinIO data
/opt/regami/postgres/  # PostgreSQL data
```

### Container Names
```
regami-api       # FastAPI backend
regami-web       # React frontend
caddy            # Reverse proxy
patroni          # PostgreSQL HA
etcd             # Distributed config
minio            # Object storage
pgbouncer        # Connection pooler
```

### Health Endpoints
```
https://api.regami.com/health                    # Production API
https://api.staging.regami.com/health            # Staging API
https://api.regami.com/health?check=db           # With DB check
```
