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
    CRM_SCHEMA_VERSION,
    CRMStateError,
    CRMSyncResult,
    Lead,
    LeadPipelineStatus,
    LeadSubmission,
    LeadSyncStatus,
    LeadValidationError,
    VALID_PIPELINE_STATUSES,
    normalize_email,
    normalize_pipeline_status,
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
    CRMSyncProvider,
    NullCRMProvider,
    build_crm_provider,
)

__all__ = [
    "CRM_SCHEMA_VERSION",
    "AirtableCRMProvider",
    "CRMConfigError",
    "CRMService",
    "CRMStateError",
    "CRMSyncProvider",
    "CRMSyncResult",
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
    "normalize_email",
    "normalize_pipeline_status",
    "VALID_PIPELINE_STATUSES",
]
