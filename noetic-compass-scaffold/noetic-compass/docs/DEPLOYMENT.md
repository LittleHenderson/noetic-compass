# Deployment Guide

## Prerequisites

- **Docker** 24+ and Docker Compose v2
- **Node.js** 20+ (for dashboard development)
- **Python** 3.12+ (for API development)
- **Rust** stable toolchain (for cas-engine development)
- **maturin** 1.0+ (for building Python bindings from Rust)

## Local Development Setup

### 1. Clone and configure

```bash
git clone <repo-url>
cd noetic-compass

# Copy env template and fill in your values
cp .env.example .env
```

### 2. Build and install cas-engine (Rust + PyO3)

```bash
cd cas-engine
maturin develop --features python
cd ..
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Run API locally

```bash
uvicorn api.main:app --reload --port 8000
```

### 5. Run dashboard locally

```bash
cd dashboard
npm ci
npm run dev
```

### 6. Run tests

```bash
# Python tests (API + validation)
python -m pytest tests/ validation/ -v

# Rust tests
cd cas-engine && cargo test && cd ..

# Frontend tests
cd dashboard && npx tsc --noEmit && npx vitest run && cd ..
```

## Docker Compose Deployment

### Step-by-step

```bash
# 1. Copy and edit environment config
cp .env.example .env
# Edit .env — at minimum set NC_JWT_SECRET to a secure value

# 2. Build and start all services
docker compose up --build -d

# 3. Verify services are healthy
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/health/ready

# 4. Access the application
#   API:       http://localhost:8000
#   Dashboard: http://localhost:3000
#   Health:    http://localhost:8000/health
#   Readiness: http://localhost:8000/health/ready
#   DB Health: http://localhost:8000/health/db
```

### Stopping services

```bash
docker compose down          # stop containers, keep volumes
docker compose down -v       # stop containers AND remove volumes
```

### Rebuilding after code changes

```bash
docker compose up --build -d
```

## Cloud Deployment (Render)

### Quick Start
1. Push repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. New > Blueprint > connect your repo
4. Render auto-detects `infra/render.yaml`
5. Set environment variables (API keys) in Render dashboard

### Services Created
| Service | Type | URL |
|---------|------|-----|
| noetic-compass-api | Web Service (Docker) | `*.onrender.com` |
| noetic-compass-dashboard | Static Site | `*.onrender.com` |

## Environment Variables Reference

All variables use the `NC_` prefix and are loaded via pydantic-settings.

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `NC_APP_NAME` | `Noetic Compass API` | Application display name |
| `NC_DEBUG` | `false` | Enable debug mode |
| `NC_CORS_ORIGINS` | `*` | Comma-separated allowed CORS origins. Use `*` for dev, specific origins for production (e.g., `https://app.example.com,https://staging.example.com`) |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `NC_JWT_SECRET` | `change-me-in-production` | JWT signing secret. **Must change in production.** |
| `NC_JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `NC_JWT_EXPIRY_MINUTES` | `60` | Token expiry time in minutes |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `NC_RATE_LIMIT_RPM` | `60` | Requests per minute (token bucket capacity) |
| `NC_RATE_LIMIT_TIER` | `community` | Tier: `community` (50/mo), `professional` (500/mo), `enterprise` (unlimited) |

### LLM Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `NC_DEFAULT_LLM_PROVIDER` | `mock` | Default provider: `mock`, `openai`, `anthropic`, `google`, `meta` |
| `NC_MOCK_LLM` | `true` | Enable mock LLM mode |
| `NC_OPENAI_API_KEY` | (empty) | OpenAI API key |
| `NC_ANTHROPIC_API_KEY` | (empty) | Anthropic API key |
| `NC_GOOGLE_API_KEY` | (empty) | Google AI API key |
| `NC_META_API_BASE_URL` | (empty) | Meta/Llama API base URL |
| `NC_META_API_KEY` | (empty) | Meta/Llama API key |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `NC_DATABASE_URL` | (empty) | PostgreSQL connection URL. If unset, DB health check returns `not_configured`. |

### Docker Compose specific

| Variable | Default | Description |
|----------|---------|-------------|
| `NC_DB_USER` | `noetic` | PostgreSQL username |
| `NC_DB_PASSWORD` | `noetic_dev` | PostgreSQL password |

## Health Check Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | No | Basic liveness probe. Returns `{"status": "ok", "version": "0.1.0"}` |
| `GET /health/db` | No | Database connectivity check. Returns 200 if connected, 503 if unreachable, 200 with `not_configured` if no DATABASE_URL |
| `GET /health/ready` | No | Full readiness probe. Returns 200 only if ALL subsystems healthy (API, cas-engine, DB if configured). Returns 503 with details of unhealthy checks. |

## Monitoring and Logging

### Structured Audit Logs

All API requests produce structured JSON audit log entries via the `noetic.audit` logger:

```json
{
  "timestamp": "2026-04-07T12:00:00+00:00",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user": "test-user",
  "api_key": "default",
  "method": "POST",
  "path": "/wrap",
  "status": 200,
  "latency_ms": 142.5,
  "content_length": 1024
}
```

### Request Tracing

Every request is assigned a unique `X-Request-ID` header:
- If the client sends `X-Request-ID`, it is passed through
- Otherwise, a UUID is generated
- The ID is included in the response headers and audit logs

### Docker Compose Health Checks

All services in docker-compose.yml include health checks:
- **cas-api**: HTTP GET to `/health` every 30s
- **cas-dashboard**: HTTP GET to `/` every 30s
- **redis**: `redis-cli ping` every 15s
- **postgres**: `pg_isready` every 15s

Monitor with:

```bash
docker compose ps          # check health status
docker compose logs -f     # tail all logs
docker compose logs cas-api -f  # tail API logs only
```

## Resource Limits

Docker Compose services include resource limits:

| Service | CPU Limit | Memory Limit | CPU Reserved | Memory Reserved |
|---------|-----------|-------------|-------------|----------------|
| cas-api | 2.0 | 2 GB | 0.5 | 512 MB |
| cas-dashboard | 0.5 | 256 MB | 0.1 | 64 MB |
| redis | 0.5 | 256 MB | 0.1 | 64 MB |
| postgres | 1.0 | 512 MB | 0.25 | 128 MB |
