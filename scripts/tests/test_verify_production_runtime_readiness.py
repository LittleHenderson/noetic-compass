from __future__ import annotations

import unittest

from scripts.verify_production_runtime_readiness import (
    RuntimeMonitorError,
    validate_api_base_url,
    validate_readiness_payload,
    validate_realmode_payload,
)


def _ready_payload() -> dict:
    return {
        "status": "ok",
        "ready": True,
        "checks": {
            "api": {"status": "ok"},
            "live_worker": {
                "configured": True,
                "required": True,
                "status": "ok",
                "authority": "verified",
            },
            "s3_worm": {
                "configured": True,
                "required": True,
                "status": "ok",
                "authority": "verified",
            },
        },
    }


def _realmode_payload() -> dict:
    return {
        "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
        "is_real_model": True,
        "fake_runtime_env": False,
        "model_loaded": True,
        "load_error": None,
        "manifest_is_real_model": True,
        "model_id": "EleutherAI/pythia-160m",
    }


class ApiBasePolicyTests(unittest.TestCase):
    def test_plain_public_base_is_allowed(self) -> None:
        self.assertEqual(
            validate_api_base_url("https://api.example.test/"),
            "https://api.example.test",
        )

    def test_embedded_credentials_are_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeMonitorError, "must not embed credentials"):
            validate_api_base_url("https://user:secret@api.example.test")


class ReadinessContractTests(unittest.TestCase):
    def test_production_dependencies_ready_passes(self) -> None:
        validate_readiness_payload(200, _ready_payload())

    def test_http_200_with_unconfigured_worker_fails_closed(self) -> None:
        payload = _ready_payload()
        payload["checks"]["live_worker"] = {
            "configured": False,
            "required": False,
            "status": "not_configured",
        }
        with self.assertRaisesRegex(RuntimeMonitorError, "live_worker=not_configured"):
            validate_readiness_payload(200, payload)

    def test_http_503_surfaces_only_normalized_dependency_reasons(self) -> None:
        payload = _ready_payload()
        payload["status"] = "degraded"
        payload["ready"] = False
        payload["checks"]["s3_worm"] = {
            "configured": True,
            "required": True,
            "status": "error",
            "reason": "authentication_failed",
        }
        with self.assertRaisesRegex(RuntimeMonitorError, "s3_worm=authentication_failed"):
            validate_readiness_payload(503, payload)

    def test_short_worm_retention_uses_normalized_reason(self) -> None:
        payload = _ready_payload()
        payload["status"] = "degraded"
        payload["ready"] = False
        payload["checks"]["s3_worm"] = {
            "configured": True,
            "required": True,
            "status": "error",
            "reason": "object_lock_retention_below_minimum",
        }
        with self.assertRaisesRegex(
            RuntimeMonitorError,
            "s3_worm=object_lock_retention_below_minimum",
        ):
            validate_readiness_payload(503, payload)

    def test_unknown_dependency_detail_is_not_echoed(self) -> None:
        payload = _ready_payload()
        payload["checks"]["s3_worm"] = {
            "configured": True,
            "required": True,
            "status": "error",
            "reason": {"credential": "must-not-appear"},
        }
        with self.assertRaises(RuntimeMonitorError) as context:
            validate_readiness_payload(503, payload)
        self.assertIn("s3_worm=error", str(context.exception))
        self.assertNotIn("must-not-appear", str(context.exception))


class WorkerRealmodeContractTests(unittest.TestCase):
    def test_strict_realmode_payload_passes(self) -> None:
        validate_realmode_payload(200, _realmode_payload())

    def test_demo_mode_fails(self) -> None:
        payload = _realmode_payload()
        payload["fake_runtime_env"] = True
        payload["is_real_model"] = False
        with self.assertRaisesRegex(RuntimeMonitorError, "fake_runtime_env"):
            validate_realmode_payload(200, payload)

    def test_load_error_fails_without_echoing_provider_detail(self) -> None:
        payload = _realmode_payload()
        payload["load_error"] = "provider path and sensitive detail"
        with self.assertRaises(RuntimeMonitorError) as context:
            validate_realmode_payload(200, payload)
        self.assertIn("load_error", str(context.exception))
        self.assertNotIn("sensitive detail", str(context.exception))


if __name__ == "__main__":
    unittest.main()
