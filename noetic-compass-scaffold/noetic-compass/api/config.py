"""Application configuration via environment variables."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


# Default directory for the Stage 21A CAS Harness EvidencePacket v1 store.
# Anchored to this file's location so the default works regardless of the
# process's current working directory. Production deployments override via
# the ``NC_EVIDENCE_PACKETS_DIR`` environment variable.
_DEFAULT_HARNESS_EVIDENCE_PACKETS_DIR = str(
    (Path(__file__).resolve().parent.parent / "research" / "cas_probe" / "evidence_packets").resolve()
)


class Settings(BaseSettings):
    # API
    app_name: str = "Noetic Compass API"
    debug: bool = False

    # Database (None = in-memory fallback)
    database_url: str | None = None

    # JWT Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # Rate limiting
    rate_limit_rpm: int = 60
    rate_limit_tier: str = "community"  # community | professional | enterprise

    # LLM provider keys (optional — mock mode if unset)
    openai_api_key: str = Field(default="", validation_alias=AliasChoices("NC_OPENAI_API_KEY", "OPENAI_API_KEY"))
    anthropic_api_key: str = Field(default="", validation_alias=AliasChoices("NC_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"))
    google_api_key: str = Field(default="", validation_alias=AliasChoices("NC_GOOGLE_API_KEY", "GOOGLE_API_KEY"))
    meta_api_base_url: str = Field(default="", validation_alias=AliasChoices("NC_META_API_BASE_URL", "META_API_BASE_URL"))
    meta_api_key: str = Field(default="", validation_alias=AliasChoices("NC_META_API_KEY", "META_API_KEY"))
    xai_api_key: str = Field(default="", validation_alias=AliasChoices("NC_XAI_API_KEY", "XAI_API_KEY"))
    deepseek_api_key: str = Field(default="", validation_alias=AliasChoices("NC_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"))
    qwen_api_key: str = Field(default="", validation_alias=AliasChoices("NC_QWEN_API_KEY", "QWEN_API_KEY"))

    # CORS — comma-separated origins, "*" for dev (default).
    # Documented env name: ``ATLAS_ALLOWED_ORIGINS`` (canonical going forward).
    # Legacy alias ``NC_CORS_ORIGINS`` retained for backward compatibility.
    # Format: comma-separated list of fully-qualified origins, e.g.
    #   ATLAS_ALLOWED_ORIGINS=https://atlas.noeticcompass.com,http://localhost:5173
    # Atlas cockpit (atlas.noeticcompass.com) → atlas-api.noeticcompass.com
    # cross-subdomain preflight requires the cockpit origin be listed here.
    cors_origins: str = Field(
        default="*",
        validation_alias=AliasChoices("ATLAS_ALLOWED_ORIGINS", "NC_CORS_ORIGINS"),
    )
    # CORS regex — matches any Vercel deployment alias + localhost by default
    cors_origin_regex: str = r"https://([a-z0-9-]+\.)*vercel\.app|http://localhost(:\d+)?"

    # Mock mode
    mock_llm: bool = True

    # Default LLM provider
    default_llm_provider: str = "mock"

    # CAS Native structured-token predictor. When artifacts and torch are
    # available, Mode 7 can use this for real NL -> CAS head predictions and
    # live hook capture; otherwise it falls back to the deterministic demo path.
    cas_native_predictor_enabled: bool = True
    cas_native_predictor_run_dir: str = ""
    cas_native_predictor_device: str = "cpu"

    # Optional secondary scorer LLM. Empty = no separate scorer for mock/base demo flows.
    scoring_provider: str = ""
    scoring_model: str = ""

    # Stage 20 Generation Readiness Gate — opt-in Output Gate companion.
    # When False (default), the 8-stage Wrap Pipeline behaves exactly as
    # before. When True, the Wrap Pipeline runs the diagnostic readiness
    # gate after the Inversion Scan and emits an allow/caveat/constrain/
    # suppress policy decision into the response (and HTTP 422 on suppress).
    # Per-request `readiness_gate_enabled` overrides this default; the
    # request flag is the canonical opt-in surface and the env var is the
    # ops-side default for environments that want the gate on globally.
    wrap_readiness_gate_enabled: bool = False
    # Default verification mode for the Wrap Pipeline integration of the
    # Stage 20 gate. Valid: HIGH_PRECISION, BALANCED, MAX_COVERAGE_TRIAGE.
    wrap_readiness_gate_mode: str = "BALANCED"

    # Stage 21B CAS Harness EvidencePacket v1 — file-backed store directory.
    # Default points at the research samples (Stage 21A canonical exports);
    # production deployments override via ``NC_EVIDENCE_PACKETS_DIR``.
    # Schema, validator, and renderer live in
    # ``research/cas_probe/evidence_packet.py`` (Stage 21A).
    harness_evidence_packets_dir: str = Field(
        default=_DEFAULT_HARNESS_EVIDENCE_PACKETS_DIR,
        validation_alias=AliasChoices("NC_EVIDENCE_PACKETS_DIR"),
    )

    # Docker Compose DB credentials (used only by docker-compose.yml)
    db_user: str = "noetic"
    db_password: str = "noetic_dev"

    model_config = {"env_prefix": "NC_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
