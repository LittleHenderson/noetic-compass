"""Application configuration via environment variables."""

from pathlib import Path
import os

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

    # CRM lead capture (go-to-market workstream). Dark-by-default and honest about it:
    #   NC_CRM_PROVIDER (default "null") -> which external CRM leads sync to. "null" captures
    #     leads locally and syncs NOTHING (the honest default);
    #     "airtable" is a real provider when its token/base/table settings are present;
    #     "hubspot" is a declared seam that currently FAILS LOUD at startup because no real
    #     integration has been built — refusing to look like sync works when it does not.
    #   NC_CRM_LEAD_STORE_PATH (default unset) -> when set, leads persist to a durable append-only
    #     JSONL file (single-host durable, survives restart). Unset uses an in-memory store that
    #     forgets on restart and never pretends otherwise — a production deployment that means to
    #     keep its leads MUST set this. See api/services/crm/.
    crm_provider: str = "null"
    crm_lead_store_path: str | None = None
    crm_airtable_token: str = Field(default="", validation_alias=AliasChoices("NC_AIRTABLE_TOKEN", "AIRTABLE_TOKEN"))
    crm_airtable_base_id: str = Field(default="", validation_alias=AliasChoices("NC_AIRTABLE_BASE_ID", "AIRTABLE_BASE_ID"))
    crm_airtable_table_name: str = Field(
        default="Leads",
        validation_alias=AliasChoices("NC_AIRTABLE_TABLE_NAME", "AIRTABLE_TABLE_NAME"),
    )
    crm_airtable_api_base_url: str = Field(
        default="https://api.airtable.com/v0",
        validation_alias=AliasChoices("NC_AIRTABLE_API_BASE_URL", "AIRTABLE_API_BASE_URL"),
    )
    crm_public_lead_rate_limit_max: int = Field(
        default=5,
        ge=0,
        validation_alias=AliasChoices("NC_CRM_PUBLIC_LEAD_RATE_LIMIT_MAX", "CRM_PUBLIC_LEAD_RATE_LIMIT_MAX"),
    )
    crm_public_lead_rate_limit_window_seconds: int = Field(
        default=3600,
        ge=0,
        validation_alias=AliasChoices(
            "NC_CRM_PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS",
            "CRM_PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS",
        ),
    )

    # JWT Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # Auth-token mint lock (CAS Harness scoped-beta Phase 1 — close the open mint).
    # Phase 1 ONLY: this is a single SHARED mint credential, not per-account identity.
    # Full per-account issued-API-key auth (each account holds its own key, tokens scoped
    # to that account) is Phase 2 — see the seam in api/routes/auth.py. Until then:
    #   NC_AUTH_MINT_SECRET (default "") -> a shared secret a /auth/token request must present
    #     (X-Auth-Mint-Secret header or `mint_secret` body field) to mint a JWT for any identity.
    #     * If SET, the secret is REQUIRED in every environment (debug or prod). Mismatch/absence
    #       -> HTTP 401. This is the closed posture.
    #     * If UNSET (""), the open mint (any username, no credential) is allowed ONLY when
    #       `debug` is True (local dev/demo). In non-debug (production) an unset secret means
    #       the mint refuses entirely (HTTP 401) — prod is NEVER an open mint.
    auth_mint_secret: str = Field(
        default="",
        validation_alias=AliasChoices("NC_AUTH_MINT_SECRET", "AUTH_MINT_SECRET"),
    )

    # Per-account identity (PAID-user security spine — the account half). Dark by default.
    #   NC_ACCOUNTS_ENABLED=false (default) -> NO account store is installed; /auth/token keeps the
    #     shared-secret mint (above) exactly as today and the /accounts/* routes return 503. App
    #     behaviour is byte-for-byte the current behaviour.
    #   NC_ACCOUNTS_ENABLED=true -> a durable account/invite store is opened at startup (Postgres
    #     when NC_DATABASE_URL is set, else SQLite) and /auth/token gains an identity-login branch:
    #     when an account exists for the supplied identity, the minted token is bound to that
    #     account's SERVER-DERIVED account_id/tenant_id/role and opens a durable jti/session that
    #     can be revoked at the request chokepoint. If enabled but no durable account/session
    #     backend can be built, startup FAILS LOUD (identity state is durable or absent, never
    #     silently in-memory). Tenant isolation and quota enforcement are later PRs.
    accounts_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("NC_ACCOUNTS_ENABLED", "ACCOUNTS_ENABLED"),
    )
    # Server-only key for one-way HMAC hashes of client-held account API credentials.
    # Account records never persist the bearer value; this key must remain stable across replicas.
    account_credential_pepper: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_ACCOUNT_CREDENTIAL_PEPPER", "ACCOUNT_CREDENTIAL_PEPPER"
        ),
    )
    # One-time hosted first-owner bootstrap secret. It is never a normal login credential.
    account_bootstrap_secret: str = Field(
        default="",
        validation_alias=AliasChoices("NC_ACCOUNT_BOOTSTRAP_SECRET", "ACCOUNT_BOOTSTRAP_SECRET"),
    )
    # Separate platform authority for provisioning later customer tenants. Customer account roles
    # never inherit this authority, and the value is accepted only in a server-side request header.
    platform_tenant_provisioning_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_PLATFORM_TENANT_PROVISIONING_SECRET",
            "PLATFORM_TENANT_PROVISIONING_SECRET",
        ),
    )
    accounts_bootstrap_tenant_id: str = Field(
        default="primary",
        validation_alias=AliasChoices(
            "NC_ACCOUNTS_BOOTSTRAP_TENANT_ID", "ACCOUNTS_BOOTSTRAP_TENANT_ID"
        ),
    )
    # SQLite account storage is single-host and requires an explicit operator acknowledgement
    # plus an absolute path. Postgres does not require this acknowledgement.
    accounts_allow_single_host_sqlite: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE", "ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE"
        ),
    )

    # Tenant-keyed immutable Evidence Packet bytes.  Dark by default.  When
    # enabled, startup requires the shared StateStore plus the existing S3
    # Object-Lock bucket/mode/retention settings and refuses host-local packet
    # files for account traffic.
    evidence_packet_object_store_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED",
            "EVIDENCE_PACKET_OBJECT_STORE_ENABLED",
        ),
    )
    # Stable server-only HMAC key for serialized exact-version Object Lock
    # verifier receipts.  It is intentionally distinct from JWT signing.  A
    # rotation invalidates existing durable receipts, so production must retain
    # this key unchanged unless a keyring/migration is introduced first.
    object_lock_receipt_attestation_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY",
            "OBJECT_LOCK_RECEIPT_ATTESTATION_KEY",
        ),
    )

    # Tenant-bound service credentials for distributed/fleet callbacks. Dark by default.
    # These credentials are deliberately separate from customer JWTs and the legacy global
    # Atlas worker token. When enabled, a durable account-mode store issues short-lived,
    # capability-scoped credentials and records one-time request nonces to reject replays.
    fleet_service_auth_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "NC_FLEET_SERVICE_AUTH_ENABLED", "FLEET_SERVICE_AUTH_ENABLED"
        ),
    )
    fleet_service_credential_pepper: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_FLEET_SERVICE_CREDENTIAL_PEPPER",
            "FLEET_SERVICE_CREDENTIAL_PEPPER",
        ),
    )
    fleet_service_max_clock_skew_seconds: int = Field(
        default=300,
        ge=30,
        le=900,
        validation_alias=AliasChoices(
            "NC_FLEET_SERVICE_MAX_CLOCK_SKEW_SECONDS",
            "FLEET_SERVICE_MAX_CLOCK_SKEW_SECONDS",
        ),
    )

    # Per-tenant usage quotas (PAID-user metering spine). Dark by default — the engine is INERT.
    #   NC_QUOTAS_ENABLED=false (default) -> NO metering. The quota engine
    #     (api/services/quotas.py) is never consulted, no usage counter is ever written or read,
    #     and app behaviour is byte-for-byte the current behaviour. Engine inert.
    #   NC_QUOTAS_ENABLED=true -> the audit run route enforces a per-tenant monthly quota,
    #     idempotently keyed by audit id. Quotas are PER-ACCOUNT, so this REQUIRES
    #     accounts_enabled: enabling quotas without accounts is a config error and FAILS LOUD at
    #     startup (see api/main.py lifespan) — there is no tenant to meter without identity.
    quotas_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("NC_QUOTAS_ENABLED", "QUOTAS_ENABLED"),
    )
    # Optional deployment-level cap used only while billing entitlements are dark. The private
    # account canary sets this to a deliberately small value so exact 429 and restart durability
    # can be proven with local/no-provider audits. Paid plans continue to derive their limits from
    # server-owned entitlement records, and an unset value preserves the historical default.
    quota_monthly_audit_limit: int | None = Field(
        default=None,
        ge=1,
        le=10_000,
        validation_alias=AliasChoices(
            "NC_QUOTA_MONTHLY_AUDIT_LIMIT", "QUOTA_MONTHLY_AUDIT_LIMIT"
        ),
    )

    # Server-derived plans/subscriptions/feature entitlements. Dark by default and valid only
    # with durable account identity + quota enforcement. The browser may request Checkout for a
    # catalog plan, but effective access is read exclusively from the signature-verified durable
    # subscription record.
    billing_entitlements_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "NC_BILLING_ENTITLEMENTS_ENABLED", "BILLING_ENTITLEMENTS_ENABLED"
        ),
    )
    billing_provider: str = Field(
        default="null",
        validation_alias=AliasChoices("NC_BILLING_PROVIDER", "BILLING_PROVIDER"),
    )
    # Separate platform authority for expiring comped-beta grants. It is not a login credential
    # and cannot grant a paid plan.
    billing_admin_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_BILLING_ADMIN_SECRET", "BILLING_ADMIN_SECRET"
        ),
    )
    stripe_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("NC_STRIPE_SECRET_KEY", "STRIPE_SECRET_KEY"),
    )
    stripe_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_STRIPE_WEBHOOK_SECRET", "STRIPE_WEBHOOK_SECRET"
        ),
    )
    stripe_professional_price_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_STRIPE_PROFESSIONAL_PRICE_ID", "STRIPE_PROFESSIONAL_PRICE_ID"
        ),
    )
    stripe_enterprise_price_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_STRIPE_ENTERPRISE_PRICE_ID", "STRIPE_ENTERPRISE_PRICE_ID"
        ),
    )
    stripe_checkout_success_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_STRIPE_CHECKOUT_SUCCESS_URL", "STRIPE_CHECKOUT_SUCCESS_URL"
        ),
    )
    stripe_checkout_cancel_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_STRIPE_CHECKOUT_CANCEL_URL", "STRIPE_CHECKOUT_CANCEL_URL"
        ),
    )
    stripe_portal_return_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "NC_STRIPE_PORTAL_RETURN_URL", "STRIPE_PORTAL_RETURN_URL"
        ),
    )

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
    atlas_live_worker_token: str = Field(
        default="",
        validation_alias=AliasChoices("ATLAS_LIVE_WORKER_TOKEN", "NC_ATLAS_LIVE_WORKER_TOKEN"),
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

    def validate_object_lock_receipt_attestation(self) -> None:
        """Require a stable MAC key for every production-capable S3 lock path."""

        anchor_mode = os.environ.get(
            "CAS_HARNESS_EVIDENCE_ANCHOR_MODE", "disabled"
        ).strip().lower()
        lock_target_present = bool(
            os.environ.get(
                "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", ""
            ).strip()
            or os.environ.get(
                "CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", ""
            ).strip()
        )
        if (
            self.evidence_packet_object_store_enabled
            or (anchor_mode == "s3" and lock_target_present)
        ) and len(self.object_lock_receipt_attestation_key.encode("utf-8")) < 32:
            raise RuntimeError(
                "S3 Object Lock receipts require stable "
                "NC_OBJECT_LOCK_RECEIPT_ATTESTATION_KEY with at least 32 bytes."
            )

    def validate_account_storage(self) -> None:
        """Fail loud unless account mode has an explicitly persistent shared backend."""
        if self.billing_entitlements_enabled and not self.accounts_enabled:
            raise RuntimeError(
                "NC_BILLING_ENTITLEMENTS_ENABLED=true requires NC_ACCOUNTS_ENABLED=true."
            )
        if self.billing_entitlements_enabled and not self.quotas_enabled:
            raise RuntimeError(
                "NC_BILLING_ENTITLEMENTS_ENABLED=true requires NC_QUOTAS_ENABLED=true."
            )
        if self.billing_entitlements_enabled:
            provider = self.billing_provider.strip().lower()
            if provider not in {"null", "stripe"}:
                raise RuntimeError("NC_BILLING_PROVIDER must be 'null' or 'stripe'.")
            if self.billing_admin_secret and len(
                self.billing_admin_secret.encode("utf-8")
            ) < 32:
                raise RuntimeError(
                    "NC_BILLING_ADMIN_SECRET must contain at least 32 bytes when set."
                )
            professional = self.stripe_professional_price_id.strip()
            enterprise = self.stripe_enterprise_price_id.strip()
            if provider == "stripe" and professional == enterprise and professional:
                raise RuntimeError(
                    "Stripe professional and enterprise price ids must be distinct."
                )
        if self.fleet_service_auth_enabled and not self.accounts_enabled:
            raise RuntimeError(
                "NC_FLEET_SERVICE_AUTH_ENABLED=true requires NC_ACCOUNTS_ENABLED=true."
            )
        if self.fleet_service_auth_enabled and len(
            self.fleet_service_credential_pepper.encode("utf-8")
        ) < 32:
            raise RuntimeError(
                "Fleet service auth requires NC_FLEET_SERVICE_CREDENTIAL_PEPPER "
                "with at least 32 bytes."
            )
        if not self.accounts_enabled:
            return

        from api.services.accounts.credentials import validate_credential_pepper

        validate_credential_pepper(self.account_credential_pepper)
        if not self.debug and not self.evidence_packet_object_store_enabled:
            raise RuntimeError(
                "Hosted account mode requires "
                "NC_EVIDENCE_PACKET_OBJECT_STORE_ENABLED=true."
            )
        if self.jwt_algorithm != "HS256":
            raise RuntimeError("Account mode pins NC_JWT_ALGORITHM=HS256.")
        if len(self.jwt_secret.encode("utf-8")) < 32:
            raise RuntimeError("Account mode requires NC_JWT_SECRET with at least 32 bytes.")
        self.validate_object_lock_receipt_attestation()
        if self.account_bootstrap_secret and len(
            self.account_bootstrap_secret.encode("utf-8")
        ) < 32:
            raise RuntimeError(
                "NC_ACCOUNT_BOOTSTRAP_SECRET must contain at least 32 bytes when set."
            )
        if self.platform_tenant_provisioning_secret and len(
            self.platform_tenant_provisioning_secret.encode("utf-8")
        ) < 32:
            raise RuntimeError(
                "NC_PLATFORM_TENANT_PROVISIONING_SECRET must contain at least "
                "32 bytes when set."
            )
        database_url = (self.database_url or "").strip()
        if database_url:
            scheme = database_url.split(":", 1)[0].lower()
            if scheme not in {"postgres", "postgresql", "postgresql+asyncpg"}:
                raise RuntimeError(
                    "Account mode requires PostgreSQL or acknowledged single-host SQLite."
                )
            return

        if not self.debug:
            raise RuntimeError(
                "Hosted account mode requires NC_DATABASE_URL backed by PostgreSQL."
            )

        if not self.accounts_allow_single_host_sqlite:
            raise RuntimeError(
                "Account mode on SQLite requires "
                "NC_ACCOUNTS_ALLOW_SINGLE_HOST_SQLITE=true."
            )
        raw_path = self.state_ledger_path.strip()
        lowered = raw_path.lower()
        if not raw_path or lowered == ":memory:" or "mode=memory" in lowered:
            raise RuntimeError("Account mode refuses an in-memory SQLite ledger.")
        if not Path(raw_path).expanduser().is_absolute():
            raise RuntimeError(
                "Account mode requires an absolute NC_STATE_LEDGER_PATH."
            )


    model_config = {"env_prefix": "NC_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
