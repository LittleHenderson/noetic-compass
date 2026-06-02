"""Application configuration via environment variables."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API
    app_name: str = "Noetic Compass API"
    debug: bool = False

    # Database (None = in-memory fallback)
    database_url: str | None = None

    # Durable state ledger (operational enable for the strangler-fig migration seam).
    # Dark by default: with both flags False, NO LedgerMirror is installed, the ledger
    # is never written or read, and the process-global dicts stay authoritative -- the
    # current production behaviour, byte-for-byte. See api/state_ledger_bootstrap.py.
    #   NC_STATE_LEDGER_ENABLED=true  -> install SqliteStateStore + LedgerMirror into both
    #     live services and rehydrate on startup (Phases 1-2: dual-write + shadow-compare),
    #     but the dicts REMAIN the read authority.
    #   NC_STATE_LEDGER_READ_AUTHORITY=true (only meaningful when enabled) -> also flip read
    #     authority onto the ledger (Phase 3). Kept a separate flag so an operator can run the
    #     mirror live in production, earning real-traffic zero-divergence evidence, BEFORE ever
    #     moving reads. Default off preserves dark-by-default.
    state_ledger_enabled: bool = False
    state_ledger_path: str = "state_ledger.db"
    state_ledger_read_authority: bool = False

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
    # Atlas cockpit (atlas.noeticcompass.com) -> api.noeticcompass.com
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

    # Atlas LIVE alpha proxy. The browser calls noetic-compass-api only; this
    # backend proxies to the private RunPod live-trace worker.
    atlas_live_worker_url: str = Field(
        default="",
        validation_alias=AliasChoices("ATLAS_LIVE_WORKER_URL", "NC_ATLAS_LIVE_WORKER_URL"),
    )
    atlas_live_invite_codes: str = Field(
        default="",
        validation_alias=AliasChoices("ATLAS_LIVE_INVITE_CODES", "NC_ATLAS_LIVE_INVITE_CODES"),
    )
    atlas_live_session_rate_limit_per_ip_hour: int = Field(
        default=120,
        ge=1,
        validation_alias=AliasChoices(
            "ATLAS_LIVE_SESSION_RATE_LIMIT_PER_IP_HOUR",
            "NC_ATLAS_LIVE_SESSION_RATE_LIMIT_PER_IP_HOUR",
        ),
    )
    atlas_live_invite_daily_limit: int = Field(
        default=1000,
        ge=1,
        validation_alias=AliasChoices(
            "ATLAS_LIVE_INVITE_DAILY_LIMIT",
            "NC_ATLAS_LIVE_INVITE_DAILY_LIMIT",
        ),
    )
    atlas_live_stream_token_minutes: int = Field(
        default=30,
        ge=1,
        validation_alias=AliasChoices(
            "ATLAS_LIVE_STREAM_TOKEN_MINUTES",
            "NC_ATLAS_LIVE_STREAM_TOKEN_MINUTES",
        ),
    )
    atlas_live_http_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "ATLAS_LIVE_HTTP_TIMEOUT_SECONDS",
            "NC_ATLAS_LIVE_HTTP_TIMEOUT_SECONDS",
        ),
    )

    # Optional secondary scorer LLM. Empty = no separate scorer for mock/base demo flows.
    scoring_provider: str = ""
    scoring_model: str = ""

    # Docker Compose DB credentials (used only by docker-compose.yml)
    db_user: str = "noetic"
    db_password: str = "noetic_dev"

    model_config = {"env_prefix": "NC_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
