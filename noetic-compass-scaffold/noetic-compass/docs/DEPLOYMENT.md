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

## Railway Deployment (API Backend - Legacy)

Deploy the FastAPI backend to Railway with Docker (includes Rust cas-engine build).

### Prerequisites

```bash
npm i -g @railway/cli
railway login
```

### Deploy

```bash
cd noetic-compass   # project root (where railway.toml lives)
railway init        # create new project, follow prompts
railway up          # deploy using Dockerfile.api
```

Railway auto-detects `railway.toml` which points to `Dockerfile.api` and sets the start command to respect Railway's dynamic `PORT`.

### Environment Variables

Set these in the Railway dashboard (Project → Variables) or via CLI:

```bash
# Required — change from default
railway variables set NC_JWT_SECRET=your-secure-random-string

# Required — allow your Vercel dashboard origin
railway variables set NC_CORS_ORIGINS=https://noetic-compass.vercel.app

# Optional — LLM provider keys (mock mode works without these)
railway variables set NC_OPENAI_API_KEY=sk-...
railway variables set NC_ANTHROPIC_API_KEY=sk-ant-...
railway variables set NC_GOOGLE_API_KEY=AI...

# Optional — switch default provider from mock
railway variables set NC_DEFAULT_LLM_PROVIDER=openai
railway variables set NC_MOCK_LLM=false
```

Full list of `NC_` variables is in the Environment Variables Reference section below.

### Connect to Vercel Dashboard

After Railway deploys, grab your public API URL from the Railway dashboard (Settings → Networking → Public URL). Then update Vercel:

```bash
cd dashboard
vercel env rm VITE_API_URL production    # remove old value
vercel env add VITE_API_URL production   # enter Railway URL, e.g. https://noetic-compass-production.up.railway.app
vercel --prod                            # redeploy with new API URL
```

### Database (Optional)

Railway offers one-click PostgreSQL:

1. Railway dashboard → New → Database → PostgreSQL
2. Copy the connection string
3. Set: `railway variables set NC_DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db`

The API works without a database (in-memory fallback).

### Health Check

Railway uses the `/health` endpoint (configured in `railway.toml`). You can also verify manually:

```bash
curl https://your-app.up.railway.app/health
# → {"status": "ok", "version": "0.1.0"}

curl https://your-app.up.railway.app/health/ready
# → {"status": "ok", "checks": {...}}
```

### Custom Domain

```bash
railway domain add api.noetic-compass.com
```

---

## Cloud Deployment (Render API Backend)

### Managed production deployment

The existing production Blueprint uses repo-root `render.yaml` from `master`.
Keep **Blueprint Auto Sync set to No** in Render. A push must not apply
infrastructure changes by itself. After `cas-ci-gate` and
`cas-postgres-live-gate` pass for the exact Blueprint source SHA, follow
[`docs/runbooks/render_blueprint_manual_sync.md`](runbooks/render_blueprint_manual_sync.md)
and perform a manual Blueprint sync.

The API service itself tracks `master` with `autoDeployTrigger: checksPass`.
The live production service is a paid `starter` Web Service in Render's Oregon
region with a 1 GB persistent disk; it is not a free service. Provider keys and
other credentials remain dashboard-managed and must never be committed.

For a suspected credential exposure, hook leak, unauthorized provider action,
or Evidence Packet integrity concern, declare an incident and follow
[`docs/runbooks/incident_response.md`](runbooks/incident_response.md). The
runbook keeps raw credentials out of Git/WORM evidence and provides separate
recovery playbooks for RunPod, Render, AWS, GitHub, and Vercel.

### Services Created
| Service | Type / plan | Region | URL |
|---------|-------------|--------|-----|
| noetic-compass-api | Web Service (Docker, starter) | Oregon | `https://noetic-compass-api.onrender.com` |
| cas-harness-api-accounts-canary | Private Service (Docker, starter) | Oregon | Private Render network only |
| cas-harness-postgres-accounts-canary | Render Postgres (basic-1gb) | Oregon | Private Render network only |

The Vercel dashboard routes `https://noeticcompass.com/api/*` to this Render API with `dashboard/vercel.json`.

### CAS Harness Evidence Packet S3 Anchoring

Evidence Packets can be written with a local hash-chain receipt or an external S3 anchor receipt. For the alpha production API, use S3 once the bucket and AWS credentials are ready.

Set these on the Render `noetic-compass-api` service:

```bash
CAS_HARNESS_EVIDENCE_ANCHOR_MODE=s3
CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET=<bucket-name-only>
CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX=cas-harness/evidence-anchors
CAS_HARNESS_EVIDENCE_ANCHOR_S3_REGION=us-west-2
AWS_ACCESS_KEY_ID=<access-key-id>
AWS_SECRET_ACCESS_KEY=<secret-access-key>
```

Important AWS naming rule: `CAS_HARNESS_EVIDENCE_ANCHOR_S3_BUCKET` is only the bucket name. Do not include `s3://`, and do not put a slash path in the bucket field. Put folder-like paths in `CAS_HARNESS_EVIDENCE_ANCHOR_S3_PREFIX`.

The IAM user for these credentials needs S3 access on the selected prefix:

```text
s3:PutObject
s3:GetObject
```

Scope both actions to:

```text
arn:aws:s3:::<bucket-name>/<prefix>/*
```

The non-writing production readiness probe also needs these read-only actions
on the bucket ARN `arn:aws:s3:::<bucket-name>`:

```text
s3:GetBucketObjectLockConfiguration
s3:GetBucketVersioning
```

They let `/health/ready` prove Object Lock and versioning authority without
creating a canary object. See
[`docs/runbooks/production_runtime_monitor.md`](runbooks/production_runtime_monitor.md)
for normalized failure meanings and incident response.

Optional object-lock retention:

```bash
CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE=GOVERNANCE
CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS=30
```

Only set these Object Lock variables when the bucket was created with Object Lock enabled. The API fails the anchor loudly if only one variable is set or if the retention value is invalid, so production cannot silently downgrade a requested WORM anchor into a plain S3 write.

If Object Lock retention is enabled, the IAM user also needs permission to write object-retention metadata on the selected prefix:

```text
s3:PutObjectRetention
s3:GetObjectRetention
```

Only set `CAS_HARNESS_EVIDENCE_ANCHOR_MODE=s3` after the bucket, region, and credentials are valid. If mode is `s3` but the write fails, every new packet will honestly report `Anchor failed`.

After setting the Render env vars and redeploying, run the deployed smoke verifier:

```bash
cd noetic-compass-scaffold/noetic-compass
python scripts/verify_evidence_anchor_deployed.py \
  --base-url https://noetic-compass-api.onrender.com \
  --require-anchor-mode s3
```

The smoke creates one tiny distributed audit, merges an Evidence Packet, runs the verifier, fetches `/evidence/{trace_id}`, and checks `/evidence/{trace_id}/verify`. It does not run real model weights; it verifies the packet anchoring control plane.

The `/verify` route re-reads the S3 anchor object, hashes it, and confirms that the anchor manifest commits to the packet hash and hash-log entry.

If Object Lock was requested in the anchor receipt, the anchor upload includes the S3-required `Content-MD5`, and `/verify` also performs `HeadObject` and requires the expected lock mode plus a future `ObjectLockRetainUntilDate`. Without that check, the packet is S3 re-read verified but not WORM verified.

To require WORM verification in the deployed smoke, use:

```bash
cd noetic-compass-scaffold/noetic-compass
python scripts/verify_evidence_anchor_deployed.py \
  --base-url https://noetic-compass-api.onrender.com \
  --require-anchor-mode s3 \
  --require-object-lock
```

Success means:

- packet `hashes.external_anchor.mode` is `s3`
- packet `hashes.external_anchor.status` is `anchored`
- `/evidence/{trace_id}/verify` returns `overall: all_match`
- the `merged_packet_external_anchor` check matches
- Atlas Evidence Drawer shows `Anchored to S3`

Additional Object Lock success means:

- packet `hashes.external_anchor.object_lock_mode` is `GOVERNANCE` or `COMPLIANCE`
- packet `hashes.external_anchor.object_lock_retain_until` is present
- `/evidence/{trace_id}/verify` confirms active Object Lock retention by re-reading S3 object metadata

Current claim boundary: S3 anchoring plus `/verify` proves that the anchor object was written, re-read, hashed, and matched to the Evidence Packet. WORM language is only allowed after the `--require-object-lock` smoke passes against an Object-Lock-enabled bucket.

Failure labels:

- `Anchor disabled`: Render is unset or mode is `disabled`.
- `Anchor failed`: mode is `s3`, but the bucket, region, credentials, or object-lock settings are wrong.
- `S3 anchor object re-read failed`: the write receipt exists, but the IAM key cannot `GetObject`, the object was deleted, or the bucket/key is unreachable.
- `Object Lock mode did not match`: the anchor receipt requested WORM retention, but the S3 object metadata does not prove the expected lock.
- `No external anchor proof`: old packet or packet generated before external anchor metadata was written.

## Vercel Deployment (Dashboard)

Deploy the dashboard as a static site on Vercel with zero-config HTTPS and global CDN.

### Prerequisites

```bash
npm i -g vercel
```

### Deploy

```bash
cd dashboard
vercel
```

On first run, Vercel CLI walks you through project linking. It auto-detects `vercel.json` and uses these settings:

| Setting | Value |
|---------|-------|
| Framework | Vite |
| Build command | `npm run build` |
| Output directory | `dist` |
| SPA rewrites | All non-asset routes → `index.html` |

### Set the API URL

Production builds use same-origin `/api` and `dashboard/vercel.json` rewrites those requests to Render:

```json
{
  "source": "/api/:path*",
  "destination": "https://noetic-compass-api.onrender.com/:path*"
}

```

If Render assigns a different service hostname, update that rewrite and redeploy:

```bash
vercel --prod
```

### Local `.env` override

For local development with a remote API (no Vite proxy):

```bash
cp .env.example .env.local
# Edit .env.local:
# VITE_API_URL=https://your-api-host.com
```

`.env.local` is gitignored by default (`*.local` in `.gitignore`).

### CORS

When the dashboard is on a different origin than the API, make sure the API allows the dashboard's origin:

```bash
# On the API server, set:
NC_CORS_ORIGINS=https://your-dashboard.vercel.app
```

### Custom Domain

```bash
vercel domains add app.noetic-compass.com
```

Vercel provisions a TLS certificate automatically. The PWA install flow, service worker, and offline mode all require HTTPS — Vercel handles this out of the box.

---

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
| `GET /health/ready` | No | Deployment readiness probe. Returns 200 only if API, cas-engine, configured DB, configured live worker, and configured S3 WORM authority are healthy. Returns a non-secret 503 contract when a load-bearing dependency fails. |

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
