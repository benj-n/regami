# Regami

[![CI](https://github.com/benj-n/regami/workflows/CI/badge.svg)](https://github.com/benj-n/regami/actions)
[![codecov](https://codecov.io/gh/benj-n/regami/branch/main/graph/badge.svg)](https://codecov.io/gh/benj-n/regami)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Full-stack app with FastAPI (backend) and Vite + React (web). Features include:
- Auth, user profile, offers/requests with matching and notifications
- Dogs: shared ownership CRUD and photo uploads (local or S3/MinIO)
- Real-time messaging with WebSocket support
- Postgres + Alembic migrations (SQLite used by default locally)
- MailHog for local email testing; MinIO for S3-compatible storage

## Documentation Guides

### Deployment and Operations
- **[DEV.md](DEV.md)** - Local development setup (Docker, Quick Start, Hybrid)
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Self-hosted production deployment guide
- **[STAGING.md](STAGING.md)** - Deploy to staging environment

### Domains
- **Production:** regami.com (API: api.regami.com)
- **Staging:** staging.regami.com (API: api.staging.regami.com)
- **Local:** localhost:5173 (API: localhost:8000)

## Self-Hosted Architecture

Production deployment on self-hosted infrastructure with high availability:

- **Infrastructure:** 3 VMs (2 production HA, 1 staging)
- **Database HA:** PostgreSQL with Patroni + etcd clustering
- **Storage:** MinIO with cross-site replication
- **Load Balancing:** External HAProxy with health checks
- **SSL:** Let's Encrypt via Caddy (automatic renewal)
- **Container Registry:** GitHub Container Registry (GHCR)

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment instructions.

This README focuses on quick local testing. For full setup, see the guides above.

## Prerequisites

- Node.js 20.x and npm
- Python 3.12 with pip
- Docker (optional, for full stack with Postgres/MailHog/MinIO)

## Quick start: run tests locally (no Docker)

### Backend tests (pytest)

From repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Run all backend tests
pytest backend/tests -q
```

Notes:
- Default DB is SQLite file at `backend/regami.db` (configured via `DATABASE_URL` in settings).
- App setting `RESET_DB_ON_STARTUP=true` resets schema on each app start in dev; tests use TestClient and their own app instance.

Run the API locally for manual checks:

```bash
# in one shell
source .venv/bin/activate
uvicorn app.main:app --app-dir backend --reload --port 8000

# in another shell: smoke test
curl -s http://localhost:8000/health
```

### Web tests (Vitest)

From `web/`:

```bash
cd web
npm ci || npm i

# Run unit tests
npm run test:run
```

Run the web app locally:

```bash
# ensure API is on http://localhost:8000 (see backend run above)
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
# open http://localhost:5173
```

## Full stack via Docker Compose

The `infra/docker-compose.yml` provides:
- Postgres (5432)
- MailHog (SMTP 1025, UI 8025)
- API (8000)
- Web (5173) and a web-dev service
- MinIO (S3 API 9000, Console 9001)

Start services:

```bash
cd infra
docker compose up -d --build
# API: http://localhost:8000
# Web: http://localhost:5173
# MailHog UI: http://localhost:8025
# MinIO Console: http://localhost:9001 (user/pass from env or defaults)
```

Environment:
- Copy `.env.example` to `.env` at the repo root and adjust if needed.
- Storage:
	- S3/MinIO (default in docker-compose): API uses MinIO; photos return URLs like `http://localhost:9000/<bucket>/dogs/...`. Configure with `S3_PUBLIC_BASE_URL` for browser-friendly URLs.
	- Local: set `STORAGE_BACKEND=local` to serve under `/static/uploads/...`.

## Database migrations (Alembic)

Alembic is set up under `backend/alembic`. Typical flow:

```bash
cd backend
# point DATABASE_URL to your target (e.g., sqlite or postgres)
export DATABASE_URL=sqlite:///./regami.db

# Generate migration from models
alembic -c alembic.ini revision --autogenerate -m "your message"

# Apply migrations
alembic -c alembic.ini upgrade head
```

## API usage examples

Health check:

```bash
curl -s http://localhost:8000/health
```

### Rate Limits

The API implements rate limiting to prevent abuse:
- **Authentication endpoints** (`/auth/*`): 5 requests per minute
- **General endpoints**: 60 requests per minute

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

When rate limit is exceeded, API returns `429 Too Many Requests`.

### Authentication

Register and login to get a token:

```bash
curl -sX POST http://localhost:8000/auth/register \
	-H 'Content-Type: application/json' \
	-d '{"email":"alice@example.com","password":"password123","dog_name":"REX21"}'

TOKEN=$(curl -sX POST http://localhost:8000/auth/login \
	-d 'username=alice@example.com&password=password123' | jq -r .access_token)
echo "Token: $TOKEN"
```

Create a dog (names must be uppercase and end with two digits, e.g., REX21):

```bash
curl -sX POST http://localhost:8000/dogs/ \
	-H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
	-d '{"name":"REX21"}'
```

Upload dog photo (S3/MinIO will return http://localhost:9000/… if S3_PUBLIC_BASE_URL is set):

```bash
curl -sX POST http://localhost:8000/dogs/1/photo \
	-H "Authorization: Bearer $TOKEN" \
	-F 'file=@/path/to/photo.png'
```

## Storage notes

- Local storage: files saved to `STORAGE_LOCAL_DIR` and exposed at `/static/uploads/...` while the API is running.
- S3/MinIO storage: uploads go to the configured bucket; URLs will use `S3_PUBLIC_BASE_URL` when set (e.g., `http://localhost:9000/<bucket>/dogs/...`), else the internal endpoint.
- The web UI enforces client-side checks: `image/*` MIME and max ~5MB. The API also checks `image/*` MIME.

## CI/CD

### Continuous Integration

GitHub Actions workflow `.github/workflows/ci.yml` runs on push/PR to `main`:
- **Backend (pytest)**: Full test suite including messaging, WebSocket, and auth tests
- **Web (Vitest)**: Frontend unit and component tests
- **Security**: Trivy vulnerability scanning and secrets detection

### Container Build

GitHub Actions workflow `.github/workflows/build.yml` builds and pushes Docker images:
- **Registry**: GitHub Container Registry (GHCR)
- **Images**: `ghcr.io/benj-n/regami-api`, `ghcr.io/benj-n/regami-web`
- **Trigger**: Push to `main` branch

### Deployment

Manual deployment via SSH scripts (GHCR → Production/Staging VMs):
- **Production**: Rolling deployment with health checks
- **Staging**: Single VM deployment
- **Scripts**: See `infra/scripts/` directory

**Workflows**: See `.github/workflows/` directory for CI/CD configuration
**Infrastructure**: See `infra/` directory for deployment configs and scripts

## Troubleshooting

- If vite dev can't reach the API, verify `web/.env.local` has `VITE_API_BASE_URL=http://localhost:8000` and the backend is running.
- For MinIO access, use the console at http://localhost:9001 and check credentials from your env.
- For emails, use MailHog UI at http://localhost:8025.
- For more help, see **[DEV.md](DEV.md)** troubleshooting section.

---

## Complete Documentation

### Quick Start
- **[README.md](README.md)** (this file) - Overview and local quick start
- **[DEPLOYMENT_QUICK_REF.md](DEPLOYMENT_QUICK_REF.md)** - Quick commands and checklists

### Development & Deployment
- **[DEV.md](DEV.md)** - Complete local development guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Self-hosted production deployment
- **[STAGING.md](STAGING.md)** - Staging environment deployment

### Configuration
- **[DOMAIN_CONFIG.md](DOMAIN_CONFIG.md)** - Domain and CORS configuration reference

### Infrastructure
- **[infra/production/RECOVERY.md](infra/production/RECOVERY.md)** - Database HA recovery procedures
- **[infra/production/HAPROXY_CONFIG.md](infra/production/HAPROXY_CONFIG.md)** - HAProxy load balancer configuration
- **Web Testing:** [web/TESTING.md](web/TESTING.md)
- **Web Coverage:** [web/COVERAGE.md](web/COVERAGE.md)

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md)

## License

MIT
