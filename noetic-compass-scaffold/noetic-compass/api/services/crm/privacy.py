"""Server-owned privacy-notice contract for public CRM consent.

The browser may acknowledge the notice, but it may not choose which notice the
server records.  Production therefore owns one exact publication status,
version, URL, and byte-level content digest.  The currently served page is a
draft and is deliberately ``OPEN``; public lead persistence remains disabled
until a separately approved notice is configured as ``present`` with a
different exact content digest.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


CRM_PRIVACY_NOTICE_URL = "https://cascompass.ai/privacy"
CRM_PRIVACY_NOTICE_OPEN_STATUS = "OPEN"
CRM_PRIVACY_NOTICE_PRESENT_STATUS = "present"

# Exact bytes served from https://cascompass.ai/privacy on 2026-07-15 UTC.
# The page itself says ``Privacy publication status: OPEN`` and
# ``FLAG_FOR_HUMAN_REVIEW``.  This digest is a deny-listed draft, not a legal
# approval or a value an operator may relabel as ``present``.
CRM_CURRENT_OPEN_DRAFT_VERSION = "draft-2026-07-14"
CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256 = (
    "e94df1615dde4122836b47a74e32d45c79b63c1603db3bd1aee01f62d7ddae28"
)

_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CRMPrivacyNoticeConfigError(ValueError):
    """The server-owned notice contract is absent, malformed, or unsafe."""


@dataclass(frozen=True)
class CRMPrivacyNoticeContract:
    """One exact privacy notice the server is allowed to record on a lead."""

    publication_status: str
    version: str
    content_sha256: str
    url: str = CRM_PRIVACY_NOTICE_URL

    def validated(self) -> "CRMPrivacyNoticeContract":
        status = self.publication_status.strip()
        version = self.version.strip()
        digest = self.content_sha256.strip().lower()
        if status not in {
            CRM_PRIVACY_NOTICE_OPEN_STATUS,
            CRM_PRIVACY_NOTICE_PRESENT_STATUS,
        }:
            raise CRMPrivacyNoticeConfigError(
                "CRM privacy notice publication status must be exact OPEN or present"
            )
        if self.url != CRM_PRIVACY_NOTICE_URL:
            raise CRMPrivacyNoticeConfigError(
                f"CRM privacy notice URL must be exact {CRM_PRIVACY_NOTICE_URL}"
            )
        if _VERSION_RE.fullmatch(version) is None:
            raise CRMPrivacyNoticeConfigError(
                "CRM privacy notice version must be a log-safe 1-128 character identifier"
            )
        if _SHA256_RE.fullmatch(digest) is None:
            raise CRMPrivacyNoticeConfigError(
                "CRM privacy notice content digest must be 64 lowercase hexadecimal characters"
            )
        if status == CRM_PRIVACY_NOTICE_PRESENT_STATUS and (
            version.casefold().startswith("draft-")
            or digest == CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256
        ):
            raise CRMPrivacyNoticeConfigError(
                "the exact currently served OPEN draft cannot be relabelled as present"
            )
        return CRMPrivacyNoticeContract(
            publication_status=status,
            version=version,
            content_sha256=digest,
            url=self.url,
        )

    @property
    def permits_contact_capture(self) -> bool:
        return self.publication_status == CRM_PRIVACY_NOTICE_PRESENT_STATUS


def build_privacy_notice_contract(settings: Any) -> CRMPrivacyNoticeContract:
    """Build the server-owned contract from settings, failing closed by default."""

    return CRMPrivacyNoticeContract(
        publication_status=str(
            getattr(
                settings,
                "crm_privacy_notice_publication_status",
                CRM_PRIVACY_NOTICE_OPEN_STATUS,
            )
        ),
        version=str(
            getattr(
                settings,
                "crm_privacy_notice_version",
                CRM_CURRENT_OPEN_DRAFT_VERSION,
            )
        ),
        content_sha256=str(
            getattr(
                settings,
                "crm_privacy_notice_content_sha256",
                CRM_CURRENT_OPEN_DRAFT_CONTENT_SHA256,
            )
        ),
    ).validated()
