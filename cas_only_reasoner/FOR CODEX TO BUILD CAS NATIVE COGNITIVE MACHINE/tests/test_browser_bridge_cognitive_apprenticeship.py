from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "playground" / "scripts" / "cncm_browser_bridge.py"


def load_bridge():
    spec = importlib.util.spec_from_file_location(
        "cncm_browser_bridge_cognitive_apprenticeship_test", BRIDGE_PATH
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


class BrowserBridgeCognitiveApprenticeshipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = load_bridge()

    def test_bridge_lists_the_bounded_ccb_t1_cases(self) -> None:
        reply = dispatch(self.bridge, "cognitive_apprenticeship_demo_cases")
        self.assertTrue(reply["ok"])
        self.assertEqual(
            reply["cognitive_apprenticeship_demo_cases"],
            [
                "exact_reasoning_math",
                "tool_use_procedure",
                "source_grounded_changing_fact",
                "protected_authority_rejection",
            ],
        )

    def test_exact_lesson_returns_local_evidence_without_kernel_authority(self) -> None:
        reply = dispatch(
            self.bridge,
            "cognitive_apprenticeship_qualify",
            {"case_id": "exact_reasoning_math"},
        )
        self.assertTrue(reply["ok"])
        result = reply["cognitive_apprenticeship"]
        self.assertTrue(result["qualification_receipt"]["passed"])
        self.assertTrue(result["retention_receipt"]["passed"])
        self.assertEqual(result["state_scope"], "LOCAL CCB-T1 STORE ONLY")
        self.assertEqual(result["authority_boundary"]["cncm_state_writes"], 0)
        self.assertEqual(result["authority_boundary"]["cas_rrk_commits"], 0)
        self.assertFalse(
            result["authority_boundary"]["cas_rrk_promotion_receipt"]
        )

    def test_protected_authority_lesson_fails_closed(self) -> None:
        reply = dispatch(
            self.bridge,
            "cognitive_apprenticeship_qualify",
            {"case_id": "protected_authority_rejection"},
        )
        self.assertTrue(reply["ok"])
        result = reply["cognitive_apprenticeship"]
        self.assertFalse(result["qualification_receipt"]["passed"])
        self.assertIsNone(result["local_version"])
        self.assertEqual(result["authority_boundary"]["cncm_state_writes"], 0)
        self.assertEqual(result["authority_boundary"]["cas_rrk_commits"], 0)

    def test_bridge_rejects_extra_ccb_t1_request_fields(self) -> None:
        reply = dispatch(
            self.bridge,
            "cognitive_apprenticeship_qualify",
            {"case_id": "exact_reasoning_math", "commit": True},
        )
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["kind"], "request_shape")


if __name__ == "__main__":
    unittest.main()
