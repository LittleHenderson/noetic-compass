# CAS Forex — single-container cloud image (the "brain" that runs 24/7).
# Serves BOTH the API (/api/forex/*) and the built cockpit UI from one port, so
# the phone and desktop are thin clients of the exact same instance.
#
# NOTE: MetaTrader5 is NOT installed (it is Windows-only and commented out of
# requirements.txt). The cloud engine runs the paper/operator brain on non-MT5
# market data (yfinance/OANDA). LIVE MT5 execution needs a Windows host or a
# PC-side MT5 relay — see docs/DEPLOY.md.
#
# Build the UI first:  (cd ui && npm ci && npm run build)
# Then:                docker build -t cas-forex .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CAS_FOREX_CLOUD_MODE=1 \
    CAS_FOREX_SERVE_UI=1

WORKDIR /app

# Python deps first (better layer caching). requirements.txt keeps MetaTrader5
# commented out, so this installs cleanly on Linux.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + the pre-built UI bundle.
COPY cas_forex ./cas_forex
COPY api ./api
COPY ui/dist ./ui/dist

# Durable state (ledgers, operator state, dials, owner token) — mount a volume
# here so it survives restarts/redeploys: the "same instance, continued exactly".
RUN mkdir -p /app/runtime
VOLUME ["/app/runtime"]

EXPOSE 8765

# A container healthcheck hits the unauthenticated liveness route.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/api/forex/health', timeout=4).status==200 else 1)"

CMD ["python", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8765", "--proxy-headers", "--forwarded-allow-ips", "*"]
