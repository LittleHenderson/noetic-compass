"""CRM lead-capture workstream — capture leads honestly, sync them only when real.

The public seam for the go-to-market lead pipeline. Its founding distinction mirrors the rest of the
platform's declared-vs-verified discipline: a lead **captured** on our side is not the same as a lead
**synced** into the external CRM of record, and only a real provider may claim the latter (see
:mod:`.models` for the full honesty rule).

Wiring: :func:`~api.services.crm.service.build_crm_service` constructs the service from settings
(durable file store + sync provider, dark by default); ``api/main.py`` stashes it on
``app.state.crm`` and ``api/routes/crm.py`` exposes the public capture endpoint and the authed sales
views over it.
"""

from __future__ import annotations

from api.services.crm.models import (
    CRM_CONSENT_SCHEMA_VERSION,
    CRM_SCHEMA_VERSION,
    CRMStateError,
    CRMSyncResult,
    CRMVerificationReceipt,
    Lead,
    LeadPipelineStatus,
    LeadSubmission,
    LeadSyncStatus,
    LeadValidationError,
    VALID_PIPELINE_STATUSES,
    normalize_email,
    normalize_pipeline_status,
)
from api.services.crm.privacy import (
    CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256,
    CRM_CURRENT_OPEN_DRAFT_VERSION,
    CRM_PRIVACY_NOTICE_OPEN_STATUS,
    CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    CRM_PRIVACY_NOTICE_URL,
    CRMPrivacyNoticeConfigError,
    CRMPrivacyNoticeContract,
    build_privacy_notice_contract,
)
from api.services.crm.service import (
    CRMService,
    build_crm_service,
    build_dark_crm_service,
    build_lead_store,
)
from api.services.crm.store import (
    InMemoryLeadStore,
    JsonlFileLeadStore,
    LeadStore,
)
from api.services.crm.abuse import (
    LeadAbuseRejected,
    PublicLeadAbuseDecision,
    PublicLeadAbuseGuard,
    PublicLeadRateLimitExceeded,
    build_public_lead_abuse_guard,
)
from api.services.crm.sync import (
    AirtableCRMProvider,
    CRMConfigError,
    CRMProviderError,
    CRMSyncProvider,
    NullCRMProvider,
    airtable_email_dedup_key,
    build_crm_provider,
    normalize_crm_provider_error,
)

__all__ = [
    "CRM_CONSENT_SCHEMA_VERSION",
    "CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256",
    "CRM_CURRENT_OPEN_DRAFT_VERSION",
    "CRM_PRIVACY_NOTICE_OPEN_STATUS",
    "CRM_PRIVACY_NOTICE_PRESENT_STATUS",
    "CRM_PRIVACY_NOTICE_URL",
    "CRMPrivacyNoticeConfigError",
    "CRMPrivacyNoticeContract",
    "CRM_SCHEMA_VERSION",
    "AirtableCRMProvider",
    "CRMConfigError",
    "CRMProviderError",
    "CRMService",
    "CRMStateError",
    "CRMSyncProvider",
    "CRMSyncResult",
    "CRMVerificationReceipt",
    "InMemoryLeadStore",
    "JsonlFileLeadStore",
    "LeadAbuseRejected",
    "Lead",
    "LeadPipelineStatus",
    "LeadStore",
    "LeadSubmission",
    "LeadSyncStatus",
    "LeadValidationError",
    "NullCRMProvider",
    "PublicLeadAbuseDecision",
    "PublicLeadAbuseGuard",
    "PublicLeadRateLimitExceeded",
    "build_crm_provider",
    "build_crm_service",
    "build_dark_crm_service",
    "build_lead_store",
    "build_public_lead_abuse_guard",
    "build_privacy_notice_contract",
    "airtable_email_dedup_key",
    "normalize_email",
    "normalize_pipeline_status",
    "normalize_crm_provider_error",
    "VALID_PIPELINE_STATUSES",
]
