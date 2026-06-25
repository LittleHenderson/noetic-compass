from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .data import dashboard_state
from .routes import proof, bundle, strategy, adaptive, settings, mt, pcba, account, movement, reconciliation, readiness, timeframes, live_telemetry, agent_decision, agent_decision_history, autonomous_loop, notifications, forex_fury_promote, strategy_dev_actions, operator_briefing, risk_monitoring

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
app.include_router(account.router, prefix="/api/forex/account", tags=["account"])
app.include_router(movement.router, prefix="/api/forex/movement", tags=["movement"])
app.include_router(reconciliation.router, prefix="/api/forex/reconciliation", tags=["reconciliation"])
app.include_router(readiness.router, prefix="/api/forex/readiness", tags=["readiness"])
app.include_router(timeframes.router, prefix="/api/forex/timeframes", tags=["timeframes"])
app.include_router(live_telemetry.router, prefix="/api/forex/live-telemetry", tags=["live-telemetry"])
app.include_router(agent_decision.router, prefix="/api/forex/agent-decision", tags=["agent-decision"])
app.include_router(agent_decision_history.router, prefix="/api/forex/agent-decision", tags=["agent-decision"])
app.include_router(autonomous_loop.router, prefix="/api/forex/autonomous-loop", tags=["autonomous-loop"])
app.include_router(notifications.router, prefix="/api/forex/notifications", tags=["notifications"])
app.include_router(forex_fury_promote.router, prefix="/api/forex/forex-fury-promote", tags=["forex-fury-promote"])
app.include_router(strategy_dev_actions.router, prefix="/api/forex/strategy-dev-actions", tags=["strategy-dev-actions"])
app.include_router(operator_briefing.router, prefix="/api/forex/operator-briefing", tags=["operator-briefing"])
app.include_router(risk_monitoring.router, prefix="/api/forex/risk-monitoring", tags=["risk-monitoring"])


@app.get("/api/forex/dashboard")
async def get_dashboard():
    """Aggregate full dashboard state."""
    return dashboard_state()


@app.get("/api/forex/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
