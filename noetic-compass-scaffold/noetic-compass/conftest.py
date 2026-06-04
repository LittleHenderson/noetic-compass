"""Root pytest conftest — establishes an honest local/dev posture for the suite.

This runs before any ``api.*`` import (pytest loads the rootdir conftest first),
so it can configure the ``Settings`` singleton via environment before
``api.config.Settings()`` is instantiated at import time.

Why this is needed (CAS Harness scoped-beta Phase 1 — mint lock / prod hardening):

* ``api.main`` now fails loud at startup when ``debug=False`` and ``jwt_secret`` is
  still the insecure default ``"change-me-in-production"``. The test suite drives
  the app through ``TestClient`` (which triggers the lifespan), so without a real
  secret every test that uses the ``client`` fixture would hit that guard.
* ``POST /auth/token`` now refuses the open (no-credential) mint unless ``debug``
  is True. The suite's auth tests exercise that frictionless local mint.

The tests model LOCAL/DEV behavior, so we declare the dev posture explicitly
rather than leaning on the insecure production default:

* ``NC_DEBUG=true``           — the dev posture the open-mint path is built for.
* ``NC_JWT_SECRET=<test>``    — a real (non-default) secret so signing is honest
                                and the production startup guard is satisfied.

Tests that specifically exercise the production-hardened paths (prod startup
guard, secret-required mint) override these per-test via ``monkeypatch``.
"""

from __future__ import annotations

import os

# Set before any `api` import so the Settings() singleton picks them up.
os.environ.setdefault("NC_DEBUG", "true")
os.environ.setdefault("NC_JWT_SECRET", "test-secret-not-the-default")
