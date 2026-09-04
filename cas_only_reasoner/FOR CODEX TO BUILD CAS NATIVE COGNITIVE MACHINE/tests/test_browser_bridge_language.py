from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "playground" / "scripts" / "cncm_browser_bridge.py"


def load_bridge():
    spec = importlib.util.spec_from_file_location(
        "cncm_browser_bridge_language_test", BRIDGE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load the browser bridge")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dispatch(bridge, operation: str, payload=None):
    request = {"operation": operation}
    if payload is not None:
        request["json"] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return json.loads(bridge.bridge_dispatch(json.dumps(request)))


class BrowserBridgeLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = load_bridge()

    def test_bridge_lists_the_bounded_language_cases(self) -> None:
        reply = dispatch(self.bridge, "language_demo_cases")
        self.assertTrue(reply["ok"])
        self.assertEqual(
            reply["language_demo_cases"],
            ["passive_voice", "negation", "teacher_cannot_commit"],
        )

    def test_teacher_proposal_cannot_activate_grammar(self) -> None:
        reply = dispatch(
            self.bridge,
            "language_qualify",
            {"case_id": "teacher_cannot_commit"},
        )
        self.assertTrue(reply["ok"])
        result = reply["language_qualification"]
        self.assertEqual(result["candidate_status"], "CCB_L1_GRAM_PROPOSED")
        self.assertEqual(result["active_count"], 0)
        self.assertEqual(
            result["active_digest_before"],
            result["active_digest_after_submission"],
        )
        self.assertEqual(result["parse_without_receipts"]["status"], "UNKNOWN_CONSTRUCTION")
        self.assertEqual(
            result["authority_boundary"],
            {
                "kernel_integrated": False,
                "cncm_state_writes": 0,
                "cas_rrk_promotion_receipt": False,
            },
        )

    def test_passive_voice_qualification_preserves_and_discriminates_roles(self) -> None:
        reply = dispatch(
            self.bridge,
            "language_qualify",
            {"case_id": "passive_voice"},
        )
        self.assertTrue(reply["ok"])
        result = reply["language_qualification"]
        self.assertTrue(result["qualification_receipt"]["passed"])
        self.assertTrue(result["retention_receipt"]["passed"])
        self.assertEqual(
            result["provisional_version"]["status"],
            "CCB_L1_GRAM_PROMOTED_PROVISIONALLY",
        )
        self.assertEqual(result["durable_version"]["status"], "CCB_L1_GRAM_ACTIVE")
        self.assertTrue(result["semantic_law"]["active_equals_passive"])
        self.assertTrue(result["semantic_law"]["role_reversal_remains_different"])
        self.assertEqual(result["authority_boundary"]["cncm_state_writes"], 0)

    def test_bridge_rejects_extra_language_request_fields(self) -> None:
        reply = dispatch(
            self.bridge,
            "language_qualify",
            {"case_id": "passive_voice", "commit": True},
        )
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["kind"], "request_shape")


if __name__ == "__main__":
    unittest.main()
