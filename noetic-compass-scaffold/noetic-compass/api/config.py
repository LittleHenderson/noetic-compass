"""Application configuration via environment variables."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

# Load …/noetic-compass/.env as an ABSOLUTE path so secrets (e.g. NC_GOOGLE_API_KEY) load no
# matter which directory the server is launched from. config.py lives at
# …/noetic-compass/api/config.py, so parent.parent is …/noetic-compass/ (where .env lives).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


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

    # Private Atlas live-trace worker. Public browsers call API routes, and the
    # API proxies the validated request to this worker URL. Canonical launch env:
    # ATLAS_LIVE_WORKER_URL / NC_ATLAS_LIVE_WORKER_URL. Older local env names are
    # retained so the existing dev tunnel setup keeps working.
    live_trace_worker_url: str = Field(
        default="http://127.0.0.1:8010",
        validation_alias=AliasChoices(
            "ATLAS_LIVE_WORKER_URL",
            "NC_ATLAS_LIVE_WORKER_URL",
            "ATLAS_LIVE_TRACE_WORKER_URL",
            "NC_LIVE_TRACE_WORKER_URL",
        ),
    )
    atlas_live_worker_token: str = Field(
        default="",
        validation_alias=AliasChoices("ATLAS_LIVE_WORKER_TOKEN", "NC_ATLAS_LIVE_WORKER_TOKEN"),
    )

    # Optional secondary scorer LLM. Empty = no separate scorer for mock/base demo flows.
    scoring_provider: str = ""
    scoring_model: str = ""

    # Gemini-powered CAS Harness explainer. The key stays server-side via
    # NC_GOOGLE_API_KEY / GOOGLE_API_KEY. The explainer route sends only curated
    # docs/explainer knowledge-base text to Gemini, never source code or internal prompts.
    gemini_explainer_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("NC_GEMINI_EXPLAINER_MODEL", "GEMINI_EXPLAINER_MODEL"),
    )

    # Docker Compose DB credentials (used only by docker-compose.yml)
    db_user: str = "noetic"
    db_password: str = "noetic_dev"

    model_config = {"env_prefix": "NC_", "env_file": str(_ENV_FILE), "extra": "ignore"}


settings = Settings()
