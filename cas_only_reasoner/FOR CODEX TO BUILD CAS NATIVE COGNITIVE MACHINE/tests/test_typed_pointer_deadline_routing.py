"""Prospective deadline regressions using exact helper ASTs and public protocol doubles.

No worker, learner, checker, Torch, or provider is imported. These tests exercise
deadline routing and one synthetic update, not numerical training equivalence.
Run on the authorized AWS test runner; this file is not a new launch request.
"""
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PRACTICE = ROOT / "cncm/typed_practice_worker.py"
POINTER = ROOT / "cncm/typed_pointer_worker.py"
CONTRACTS = ROOT / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def functions(path, names, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in selected} == set(names), "MISSING_TESTED_FUNCTION")
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def deadline_constant(name):
    tree = ast.parse((CONTRACTS / name).read_text(encoding="utf-8"))
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "WORKER_DEADLINE_SECONDS"
                        for target in node.targets))


class DeadlineRouting(unittest.TestCase):
    def setUp(self):
        self.elapsed = 0.0
        self.started = 700.0  # A nonzero origin catches accidental fresh-clock substitution.
        self.events = []
        self.clock = SimpleNamespace(monotonic=lambda: self.started + self.elapsed)
        self.practice = functions(PRACTICE, ("_deadline", "_stage_and_train", "_train_logged", "_append"), {
            "require": require, "Path": Path, "os": os, "canonical": canonical,
            "time": self.clock,
            "contract": SimpleNamespace(WORKER_DEADLINE_SECONDS=deadline_constant("practice_contract.py")),
            "base": SimpleNamespace(_write_bytes=self.write_seal),
        })
        self.pointer = functions(POINTER, ("_deadline", "_train_logged", "_stage_and_train"), {
            "require": require, "time": self.clock,
            "contract": SimpleNamespace(WORKER_DEADLINE_SECONDS=deadline_constant("pointer_contract.py")),
            "practice_worker": SimpleNamespace(**{name: self.practice[name]
                for name in ("_train_logged", "_stage_and_train")}),
        })
        # This synthetic module handles public sentinel packets only. The real
        # private checker and all project modules remain unimported.
        package = ModuleType("cas_meta2")
        package.__path__ = []
        teaching = ModuleType("cas_meta2.typed_teaching")
        teaching.__path__ = []
        checker = ModuleType("cas_meta2.typed_teaching.checker")
        checker.derive_target = self.derive_target
        teaching.checker = checker
        package.typed_teaching = teaching
        self.checker_patch = patch.dict(sys.modules, {
            "cas_meta2": package, "cas_meta2.typed_teaching": teaching,
            "cas_meta2.typed_teaching.checker": checker,
        })
        self.checker_patch.start()
        self.addCleanup(self.checker_patch.stop)

    def write_seal(self, path, raw):
        self.events.append("seal")
        path.write_bytes(raw)
        self.seal = path
        return {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}

    def derive_target(self, source, query):
        self.assertEqual((source, query), ("public-fixture", "public-query"))
        self.assertEqual(self.seal.read_bytes(), b'{"record_id":"public-case"}\n')
        self.events.append("target")
        return {"target_digest": "public-target-digest"}

    def learner(self):
        owner = self

        class PublicLearner:
            cursor = 4

            def stage_batch(self, packets, depth, *, cursor, occurrence_ids):
                owner.events.append("stage")
                owner.assertEqual(depth, 8)
                owner.assertEqual(cursor, 4)
                owner.assertEqual(occurrence_ids, ["public-occurrence"])
                owner.assertEqual(packets, [{"source": "public-fixture", "record": {"query": "public-query"}}])
                raw = b'{"record_id":"public-case"}\n'
                return {"bytes": raw, "sha256": sha256(raw).hexdigest()}

            def train_sealed_batch(self, path, *, expected_sha256, target_receipts):
                owner.events.append("train")
                owner.assertEqual(expected_sha256, sha256(path.read_bytes()).hexdigest())
                owner.assertEqual(target_receipts, [{"target_digest": "public-target-digest"}])
                self.cursor += 1
                return {"gradient_squared_norm": 0.5, "cursor": self.cursor}

        return PublicLearner()

    def run_update(self, namespace, *, logged, deadline=None, explicit_deadline=False):
        self.events = []
        learner = self.learner()
        batch = {"cursor": 4, "record_ids": ["public-case"], "depth": 8,
                 "occurrence_ids": ["public-occurrence"]}
        packets = {"public-case": {"source": "public-fixture", "record": {"query": "public-query"}}}
        kwargs = {"started": self.started}
        if explicit_deadline:
            kwargs["deadline"] = deadline
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            if logged:
                batches, updates = staging / "batches.jsonl", staging / "updates.jsonl"
                returned = namespace["_train_logged"](learner, batch, packets, staging, batches, updates, **kwargs)
                self.assertFalse((staging / "seal.json").exists())
                logs = (batches.read_bytes(), updates.read_bytes())
            else:
                returned = namespace["_stage_and_train"](learner, batch, packets, staging / "seal.json", **kwargs)
                logs = None
            return returned, learner.cursor, list(self.events), logs

    def test_pointer_logged_update_passes_after_old_practice_deadline(self):
        self.elapsed = 20000
        self.assertEqual(self.run_update(self.pointer, logged=True)[1], 5)

    def test_pointer_replay_update_passes_after_old_practice_deadline(self):
        self.elapsed = 20000
        self.assertEqual(self.run_update(self.pointer, logged=False)[1], 5)

    def test_pointer_strict_deadline_applies_before_any_update_work(self):
        self.assertEqual(self.pointer["contract"].WORKER_DEADLINE_SECONDS, 23100)
        for logged in (True, False):
            with self.subTest(logged=logged):
                self.elapsed = 23099.999
                self.assertEqual(self.run_update(self.pointer, logged=logged)[1], 5)
                for elapsed in (23100, 23100.001):
                    self.elapsed = elapsed
                    with self.assertRaisesRegex(ValueError, "POINTER_DEADLINE_EXCEEDED"):
                        self.run_update(self.pointer, logged=logged)
                    self.assertEqual(self.events, [])

    def test_practice_default_deadline_remains_unchanged(self):
        self.assertEqual(self.practice["contract"].WORKER_DEADLINE_SECONDS, 12300)
        for logged in (True, False):
            with self.subTest(logged=logged):
                self.elapsed = 12299.999
                self.assertEqual(self.run_update(self.practice, logged=logged)[1], 5)
                self.elapsed = 12300
                with self.assertRaisesRegex(ValueError, "PRACTICE_DEADLINE_EXCEEDED"):
                    self.run_update(self.practice, logged=logged)
                self.assertEqual(self.events, [])

    def test_logged_helper_forwards_callback_and_original_start(self):
        starts = []

        def refuse(started):
            starts.append(started)
            raise ValueError("SENTINEL_DEADLINE")

        with self.assertRaisesRegex(ValueError, "SENTINEL_DEADLINE"):
            self.run_update(self.practice, logged=True, deadline=refuse, explicit_deadline=True)
        self.assertEqual(starts, [self.started])
        self.assertEqual(self.events, [])

    def test_pointer_wrappers_forward_all_inputs_and_own_callback(self):
        calls = []
        sentinel = object()

        def capture(*args, **kwargs):
            calls.append((args, kwargs))
            return sentinel

        self.pointer["practice_worker"] = SimpleNamespace(_train_logged=capture, _stage_and_train=capture)
        for name, length in (("_train_logged", 6), ("_stage_and_train", 4)):
            args = tuple(object() for _ in range(length))
            self.assertIs(self.pointer[name](*args, started=self.started), sentinel)
            self.assertEqual(calls[-1], (args, {"started": self.started, "deadline": self.pointer["_deadline"]}))

    def test_update_outputs_and_seal_before_target_order_are_preserved(self):
        self.elapsed = 100
        expected_update = {"gradient_squared_norm": 0.5, "cursor": 5,
            "correction_identities": [{"record_id": "public-case", "target_digest": "public-target-digest"}]}
        for logged in (True, False):
            with self.subTest(logged=logged):
                practice = self.run_update(self.practice, logged=logged)
                pointer = self.run_update(self.pointer, logged=logged)
                self.assertEqual(pointer, practice)
                self.assertEqual(pointer[:3], ((b'{"record_id":"public-case"}\n', expected_update), 5,
                                               ["stage", "seal", "target", "train"]))
                if logged:
                    self.assertEqual(pointer[3], (pointer[0][0], canonical(expected_update)))

    def test_main_interference_and_replay_routes_call_pointer_wrappers(self):
        tree = ast.parse(POINTER.read_text(encoding="utf-8"))
        routes = {"_main_training": "_train_logged", "_retention_and_interference": "_train_logged",
                  "_reloads_and_replays": "_stage_and_train"}
        for name, helper in routes.items():
            node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
            calls = [call for call in ast.walk(node) if isinstance(call, ast.Call)]
            self.assertTrue(any(isinstance(call.func, ast.Name) and call.func.id == helper for call in calls))
            self.assertFalse(any(isinstance(call.func, ast.Attribute)
                and call.func.attr in ("_train_logged", "_stage_and_train") for call in calls))


if __name__ == "__main__":
    unittest.main()
