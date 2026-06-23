from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .data import dashboard_state
from .routes import proof, bundle, strategy, adaptive, settings, mt, pcba

app = FastAPI(title="CAS Forex API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_origin_regex=(
        r"^(https?://("
        r"localhost|127\.0\.0\.1|0\.0\.0\.0|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?|capacitor://localhost)$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proof.router, prefix="/api/forex/proof", tags=["proof"])
app.include_router(bundle.router, prefix="/api/forex/bundle", tags=["bundle"])
app.include_router(strategy.router, prefix="/api/forex/strategy", tags=["strategy"])
app.include_router(adaptive.router, prefix="/api/forex/adaptive", tags=["adaptive"])
app.include_router(settings.router, prefix="/api/forex/settings", tags=["settings"])
app.include_router(pcba.router, prefix="/api/forex/pcba", tags=["pcba"])
app.include_router(mt.router, prefix="/api/forex/mt", tags=["mt"])


@app.get("/api/forex/dashboard")
async def get_dashboard():
    """Aggregate full dashboard state."""
    return dashboard_state()


@app.get("/api/forex/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
