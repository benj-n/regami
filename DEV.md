# Local Development Guide

Complete guide to run Regami locally for development and testing.

## Overview

This guide covers three ways to run Regami locally:

1. **Quick Start** - Backend + Frontend (no Docker, SQLite)
2. **Docker Compose** - Full stack with PostgreSQL, MinIO, MailHog
3. **Hybrid** - Backend in Docker, Frontend on host (best for frontend development)

---

## Prerequisites

### Required Tools

```bash
# 1. Python 3.12
python3.12 --version
# If not installed:
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip

# 2. Node.js 20.x
node --version  # Should be v20.x
# If not installed:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 3. Docker (optional, for full stack)
docker --version
docker compose version
# If not installed: https://docs.docker.com/engine/install/

# 4. Git
git --version
```

### Clone Repository

```bash
git clone https://github.com/benj-n/regami.git
cd regami
```

---

## Method 1: Quick Start (No Docker)

Best for: Quick testing, backend development

### 1. Backend Setup

```bash
# Create Python virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Copy environment file
cp ../.env.example ../.env

# Edit .env (optional - defaults work for local dev)
# Defaults:
# - SQLite database
# - Local file storage
# - No email (MailHog not running)
```

### 2. Run Backend

```bash
# Start API server
uvicorn app.main:app --reload --port 8000

# You should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete.
```

**API will be available at:** `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs`

### 3. Frontend Setup

Open a new terminal:

```bash
cd web

# Install dependencies
npm ci

# Create environment file
cp .env.example .env.local

# Edit .env.local
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
```

### 4. Run Frontend

```bash
# Start dev server
npm run dev

# You should see:
# VITE v5.x ready in xxx ms
# ➜  Local:   http://localhost:5173/
```

**Web app will be available at:** `http://localhost:5173`

### 5. Test the Setup

```bash
# In a new terminal:

# Test backend health
curl http://localhost:8000/health

# Expected: {"status":"ok"}

# Test frontend
curl -I http://localhost:5173

# Expected: HTTP/1.1 200 OK
```

### 6. Create Test User

**Option A: Via API**
```bash
# Register user
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "dog_name": "REX21"
  }'

# Login
curl -X POST http://localhost:8000/v1/auth/login \
  -d "username=test@example.com&password=password123"

# Copy the access_token from response
```

**Option B: Via Web UI**
1. Open `http://localhost:5173`
2. Click "S'inscrire" (Register)
3. Fill form: email, password, dog name (e.g., REX21)
4. Login with credentials

### 7. Run Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd ../web
npm run test:run

# E2E tests (requires both backend and frontend running)
npm run test:e2e
```

---

## Method 2: Docker Compose (Full Stack)

Best for: Complete local environment, testing integrations

### Architecture

```
┌─────────────────────────────────────────────────┐
│  Docker Compose Services                        │
├─────────────────────────────────────────────────┤
│  • PostgreSQL (port 5432)                       │
│  • MinIO S3 (port 9000, console 9001)           │
│  • MailHog SMTP (port 1025, UI 8025)            │
│  • API Backend (port 8000)                      │
│  • Web Frontend (port 5173)                     │
└─────────────────────────────────────────────────┘
```

### 1. Setup Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env (optional - defaults work)
# Important settings for Docker:
# DATABASE_URL=postgresql+psycopg2://regami:regami@db:5432/regami
# S3_ENDPOINT_URL=http://minio:9000
# SMTP_HOST=mailhog
```

### 2. Start Services

```bash
cd infra

# Start all services
docker compose up -d --build

# Watch logs (optional)
docker compose logs -f

# Or watch specific service
docker compose logs -f api
```

**Wait for all services to be healthy (~30-60 seconds)**

### 3. Verify Services

```bash
# Check service status
docker compose ps

# All services should show "healthy"

# Test each service:

# 1. PostgreSQL
docker compose exec db psql -U regami -d regami -c "SELECT 1"

# 2. MinIO
curl http://localhost:9000/minio/health/live
# Expected: OK

# 4. MailHog
curl http://localhost:8025
# Expected: HTML response

# 5. API
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 6. Web
curl -I http://localhost:5173
# Expected: HTTP/1.1 200 OK
```

### 4. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Web App** | http://localhost:5173 | - |
| **API** | http://localhost:8000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **MailHog UI** | http://localhost:8025 | - |
| **PostgreSQL** | localhost:5432 | regami / regami |

### 5. Create Test Data

```bash
# Run seed script
docker compose exec api python scripts/seed.py

# This creates:
# - 4 test users (alice, bob, carol, david)
# - Dogs for each user
# - Sample availability offers/requests
# - Some matches
```

**Test Users:**
- `alice@example.com` / `password123`
- `bob@example.com` / `password123`
- `carol@example.com` / `password123`
- `david@example.com` / `password123`

### 6. Test Features

**Upload Dog Photos:**
1. Login as alice@example.com
2. Go to "Mes chiens" (My dogs)
3. Upload a photo for DOG01
4. View uploaded photo (served from MinIO)

**Test Email:**
1. Register new user
2. Open MailHog: http://localhost:8025
3. See welcome email

**Test Matching:**
1. Login as Alice
2. Create an availability offer
3. Login as Bob (new browser/incognito)
4. Create an availability request with overlapping time
5. See match notification

### 7. Development Workflow

```bash
# Code changes are automatically reflected:

# Backend: Uvicorn auto-reloads on file changes
# Frontend: Vite hot-reloads on file changes

# View logs
docker compose logs -f api    # Backend logs
docker compose logs -f web    # Frontend logs

# Restart services
docker compose restart api
docker compose restart web

# Stop services
docker compose down

# Stop and remove volumes (⚠️ deletes data)
docker compose down -v
```

### 8. Database Management

```bash
# Access database shell
docker compose exec db psql -U regami -d regami

# Run SQL queries
docker compose exec db psql -U regami -d regami -c "SELECT * FROM users;"

# Run migrations
docker compose exec api alembic upgrade head

# Create new migration
docker compose exec api alembic revision --autogenerate -m "description"

# Rollback migration
docker compose exec api alembic downgrade -1

# Reset database (⚠️ deletes all data)
docker compose down -v
docker compose up -d
```

### 9. Stop Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (deletes data)
docker compose down -v

# Stop and remove images
docker compose down --rmi all
```

---

## Method 3: Hybrid (Backend in Docker, Frontend on Host)

Best for: Frontend development with full backend features

### 1. Start Backend Services Only

```bash
cd infra

# Start only backend services
docker compose up -d db minio mailhog minio-setup api

# Wait for API to be healthy
docker compose ps api
```

### 2. Run Frontend on Host

```bash
cd web

# Install dependencies
npm ci

# Create .env.local
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local

# Start dev server
npm run dev
```

**Benefits:**
- Fast frontend hot-reload
- Full backend features (PostgreSQL, S3)
- Easy frontend debugging
- Faster npm installs (no Docker rebuild)

---

## Testing

### Backend Tests

```bash
# Quick Start method
cd backend
pytest tests/ -v

# Docker Compose method
docker compose exec api pytest tests/ -v

# With coverage
docker compose exec api pytest tests/ --cov=app --cov-report=html

# View coverage report
open backend/htmlcov/index.html
```

### Frontend Tests

```bash
# Unit tests
cd web
npm run test:run

# Watch mode
npm run test

# Coverage
npm run test:coverage

# E2E tests (requires backend running)
npm run test:e2e

# E2E with UI
npm run test:e2e:ui
```

### Load Tests

```bash
# Install k6
# macOS: brew install k6
# Linux: snap install k6

cd tests/load

# Basic load test
k6 run basic-load-test.js

# Stress test
k6 run stress-test.js

# Spike test
k6 run spike-test.js
```

---

## Debugging

### Backend Debugging (VS Code)

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

**Usage:**
1. Set breakpoints in Python code
2. Press F5 to start debugging
3. Make API requests
4. Debugger pauses at breakpoints

### Frontend Debugging

```bash
# Use browser DevTools
# Chrome: F12 → Sources tab
# Set breakpoints in React components

# Or use VS Code debugger
# Install "JavaScript Debugger" extension
# Set breakpoints in .tsx files
# Run: npm run dev
# Attach debugger to Chrome
```

### Docker Debugging

```bash
# View all logs
docker compose logs

# Follow specific service
docker compose logs -f api

# Execute commands in container
docker compose exec api bash

# Check environment variables
docker compose exec api env

# Test database connection
docker compose exec api python -c "from app.db import engine; print(engine)"
```

---

## Common Issues

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # or :5173, :5432, etc.

# Kill process
kill -9 <PID>

# Or use different ports
uvicorn app.main:app --port 8001
npm run dev -- --port 5174
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker compose ps db

# Check connection string
docker compose exec api env | grep DATABASE_URL

# Test connection
docker compose exec db psql -U regami -d regami -c "SELECT 1"

# Restart database
docker compose restart db
```

### MinIO Access Denied

```bash
# Check MinIO credentials
docker compose exec api env | grep S3_

# Recreate bucket
docker compose exec minio mc mb regami/regami --ignore-existing

# Set public policy
docker compose exec minio mc anonymous set download regami/regami
```

### Frontend Can't Reach API

```bash
# Check API is running
curl http://localhost:8000/health

# Check CORS configuration
docker compose exec api env | grep CORS_ORIGINS

# Should include: http://localhost:5173

# Check frontend .env.local
cat web/.env.local
# Should have: VITE_API_BASE_URL=http://localhost:8000
```



---

## Useful Commands

### Database

```bash
# Backup database
docker compose exec -T db pg_dump -U regami regami > backup.sql

# Restore database
docker compose exec -T db psql -U regami regami < backup.sql

# Reset database
docker compose down -v
docker compose up -d db
docker compose exec api alembic upgrade head
```

### MinIO

```bash
# List buckets
docker compose exec minio mc ls minio

# List objects in bucket
docker compose exec minio mc ls minio/regami

# Upload file
docker compose exec minio mc cp /tmp/test.jpg minio/regami/test/

# Download file
docker compose exec minio mc cp minio/regami/test/test.jpg /tmp/
```

### Logs

```bash
# All logs
docker compose logs

# Last 100 lines
docker compose logs --tail=100

# Follow logs
docker compose logs -f

# Specific service
docker compose logs -f api

# Since timestamp
docker compose logs --since 2024-01-01T00:00:00

# Filter logs
docker compose logs | grep ERROR
```

### Performance

```bash
# Check resource usage
docker stats

# Check disk usage
docker system df

# Clean up unused images
docker image prune -a

# Clean up everything (⚠️ deletes all data)
docker system prune -a --volumes
```

---

## Development Tips

### Hot Reload

Both backend and frontend support hot reload:

**Backend (Uvicorn):**
- Automatically reloads on `.py` file changes
- No need to restart server
- Changes reflect immediately

**Frontend (Vite):**
- Extremely fast hot module replacement (HMR)
- Changes reflect in <100ms
- Preserves component state

### Database Migrations

```bash
# Create new migration after model changes
alembic revision --autogenerate -m "add user profile"

# Review generated migration
cat alembic/versions/xxxx_add_user_profile.py

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing Workflow

```bash
# TDD workflow:
# 1. Write test
# 2. Run test (should fail)
# 3. Write code
# 4. Run test (should pass)
# 5. Refactor

# Run tests in watch mode
cd web
npm run test  # Vitest watch mode

cd backend
ptw  # pytest-watch (pip install pytest-watch)
```

### Code Quality

```bash
# Format code
cd backend
black app/

cd web
npm run format

# Lint code
cd backend
ruff check app/

cd web
npm run lint

# Type checking
cd web
npm run type-check
```

---

## API Documentation

When backend is running:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

### Example API Calls

```bash
# Register
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "securepass123",
    "dog_name": "MAX99"
  }'

# Login
TOKEN=$(curl -X POST http://localhost:8000/v1/auth/login \
  -d "username=newuser@example.com&password=securepass123" \
  | jq -r .access_token)

# Get profile
curl http://localhost:8000/v1/users/me \
  -H "Authorization: Bearer $TOKEN"

# List dogs
curl http://localhost:8000/v1/dogs/me \
  -H "Authorization: Bearer $TOKEN"

# Create availability offer
curl -X POST http://localhost:8000/v1/availability/offers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_at": "2024-12-01T09:00:00Z",
    "end_at": "2024-12-01T17:00:00Z"
  }'
```

---

## Getting Help

- **Documentation:** See project README and other guides
- **Issues:** Open GitHub issue
- **Logs:** Check Docker logs for errors
- **Community:** Ask in project discussions

---

## Quick Reference

### Start Development

```bash
# Quick Start (no Docker)
source .venv/bin/activate
cd backend && uvicorn app.main:app --reload &
cd web && npm run dev

# Docker Compose
cd infra && docker compose up -d

# Hybrid
cd infra && docker compose up -d db minio mailhog api
cd web && npm run dev
```

### Stop Development

```bash
# Quick Start
# Press Ctrl+C in both terminals

# Docker Compose
cd infra && docker compose down

# Hybrid
cd infra && docker compose down
# Press Ctrl+C in web terminal
```

### Run Tests

```bash
# Backend
pytest backend/tests/ -v

# Frontend
cd web && npm run test:run

# All tests
pytest backend/tests/ && cd web && npm run test:run
```

### Reset Everything

```bash
# Remove virtual environment
rm -rf .venv

# Remove Docker volumes
cd infra && docker compose down -v

# Remove node_modules
rm -rf web/node_modules

# Start fresh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd web && npm ci
```

---

**Happy coding!**
