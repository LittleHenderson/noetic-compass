from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "playground" / "scripts" / "cncm_browser_bridge.py"


def load_bridge():
    spec = importlib.util.spec_from_file_location("cncm_browser_bridge_test", BRIDGE_PATH)
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


class BrowserBridgeMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = load_bridge()

    def test_linear_result_is_reexecuted_through_bridge(self) -> None:
        solved = dispatch(
            self.bridge,
            "math_solve",
            {"notation": "2*(x+3)=14", "variable": "x"},
        )
        self.assertTrue(solved["ok"])
        self.assertTrue(solved["math_verification"]["valid"])

        verified = dispatch(self.bridge, "math_verify", solved["math_result"])
        self.assertTrue(verified["ok"])
        self.assertTrue(verified["report"]["valid"])

    def test_counterexample_result_is_reexecuted_and_tampering_fails(self) -> None:
        searched = dispatch(
            self.bridge,
            "math_counterexample",
            {
                "notation": "x*x<5",
                "bounds": [{"variable": "x", "lower": -3, "upper": 3}],
                "max_assignments": 4096,
            },
        )
        self.assertTrue(searched["ok"])
        self.assertEqual(searched["math_counterexample"]["status"], "FOUND")
        self.assertTrue(searched["math_verification"]["valid"])

        verified = dispatch(
            self.bridge,
            "math_verify_counterexample",
            searched["math_counterexample"],
        )
        self.assertTrue(verified["ok"])
        self.assertTrue(verified["report"]["valid"])

        tampered = copy.deepcopy(searched["math_counterexample"])
        tampered["assignment"] = [["x", 2]]
        rejected = dispatch(self.bridge, "math_verify_counterexample", tampered)
        self.assertTrue(rejected["ok"])
        self.assertFalse(rejected["report"]["valid"])

    def test_bridge_rejects_unknown_math_fields(self) -> None:
        reply = dispatch(
            self.bridge,
            "math_solve",
            {"notation": "x=1", "variable": "x", "verified": True},
        )
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["kind"], "request_shape")


if __name__ == "__main__":
    unittest.main()
