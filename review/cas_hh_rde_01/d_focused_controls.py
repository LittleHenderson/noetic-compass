"""CAS-HH-RDE-01 / D — focused independent controls (second reviewer delivery).

OWNER: DeepSeek independent reviewer lane. Reviewer-only area:
    review/cas_hh_rde_01/*   (CAPTURE_CONTRACT.json scopes.DeepSeek)

REQUESTED BY
------------
Codex, codex-cas-hh-rde-01-source-handoff (2026-09-28T19:18:06Z):
"prepare focused independent neutrality/coverage/wrong-parent-site-shape-round-basis/
tamper controls. Source only; no paid calls, local tests or cloud launches."

WHAT THIS FILE IS
-----------------
Five control families, each executed here, model-free, CPU-only, no torch, no
network, no cloud, no paid call:

  F1 NEUTRALITY      -- OFF vs OBSERVE_ONLY must be bit-identical, and the
                        completeness flag must track hook coverage truthfully
                        (HH03, HH04).
  F2 COVERAGE        -- expected vs observed calls per declared site; a hook that
                        never fired is UNREACHED, never "0 calls"; any hook error
                        makes the whole receipt INCOMPLETE (HH04).
  F3 WRONG-KEY       -- a candidate must be refused, before any write, when its
                        parent module, site, shape, round index or basis is wrong,
                        and each refusal must name which key was wrong (HH02, HH05).
  F4 TAMPER          -- changed, truncated or internally-rehashed evidence must be
                        detected against an anchor the candidate cannot reach
                        (HH16).
  F5 CLEANUP         -- observer and intervention handles are released on normal
                        exit, on exception, and after a refused action (HH06, HH10).

WHY F3 AND F4 EXIST IN THIS STRENGTH
------------------------------------
F3 is driven by the current patch, not by preference. The declared capture sites in
CAPTURE_CONTRACT.json are dotted names ("head.reach", "graph.round_update"), while
the vendored harness runner was written against a Pythia attribute path
("gpt_neox.layers") plus a bare (layer, index) coordinate. Two coordinate spaces
that never meet produce a silent no-op, and a silent no-op is the failure mode the
shared directive forbids from being scored as success (HH10, HH11).

F4 is written this way on purpose. If a record carries its own digest, an attacker
edits the payload and recomputes the digest, and the check still passes. The
authoritative identity must live outside the candidate's reach. F4 demonstrates
that failure concretely rather than asserting it.

WHAT THIS FILE DOES NOT CLAIM
-----------------------------
Nothing here says HELM improved, or that any hidden computation was explained.
Everything below runs against reviewer-owned stubs and the byte-verified vendored
harness copy. Anything needing a real HELM checkpoint is in NOT_RUN with its exact
admitted-venue command.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Byte-verified external anchors. Each is a fact about bytes, checked below.
# ---------------------------------------------------------------------------
HARNESS_VENDOR_COPY = HERE / "_codex_pkg_62bb7f71" / "_verify" / "probe_runner_3468723e.py"
HARNESS_BLOB = "3468723e300fdf4fbb090c0d156b8014825d546d"
HARNESS_SHA256 = "543666e576a559b1bfd15d9c63b33d401de3dcb47a3af13325700060abca9209"
HARNESS_BYTES = 13105
HELM_MASTER_COMMIT = "e8537e6ce9e93242fb11dec36c03dbcafa86042c"

# Declared capture sites (CAPTURE_CONTRACT.json -> sites), machine-readable form.
DECLARED_SITES = (
    "input.mapping",
    "graph.initial_state",
    "graph.round_input",
    "graph.round_update",
    "graph.round_state",
    "graph.node_state",
    "graph.query_state",
    "graph.pointer_query",
    "head.node",
    "head.reach",
    "head.node_pointer",
    "answer.scores",
    "answer.decisions",
    "answer.assembly",
)


# ===========================================================================
# F1 -- passive neutrality (HH03) and truthful completeness (HH04)
# ===========================================================================
def _neutral_run(*, observe: bool):
    """One deterministic forward. Returns the recorded state, not a verdict."""
    model = RecorderModel(seed=20260928)
    with RecorderObserver(model, observe=observe) as receipt:
        prediction = model.forward()
        state = model.state_snapshot()
    return {"prediction": prediction, "state": state, "receipt": receipt}


def test_f1_off_and_observe_only_are_bit_identical():
    baseline = _neutral_run(observe=False)
    observed = _neutral_run(observe=True)
    assert baseline["prediction"] == observed["prediction"]
    assert baseline["state"] == observed["state"], "no tensor, parameter or RNG field may differ"


def test_f1_observation_records_values_without_altering_them():
    observed = _neutral_run(observe=True)
    assert observed["receipt"]["observed_sites"] == len(DECLARED_SITES)
    assert observed["receipt"]["before"] == observed["receipt"]["after"], (
        "the value seen by the hook must be the value the caller receives")


def test_f1_overhead_is_charged_not_hidden():
    observed = _neutral_run(observe=True)
    assert isinstance(observed["receipt"]["overhead_ns"], int)
    assert observed["receipt"]["overhead_ns"] >= 0
    assert observed["receipt"]["overhead_charged"] is True


def test_f1_an_unobserved_run_reports_zero_overhead_and_off_mode():
    baseline = _neutral_run(observe=False)
    assert baseline["receipt"]["capture_mode"] == "OFF"
    assert baseline["receipt"]["observed_sites"] == 0
    assert baseline["receipt"]["overhead_ns"] == 0


# ===========================================================================
# F2 -- actual capture coverage, never inferred (HH04)
# ===========================================================================
def test_f2_expected_is_declared_and_observed_is_counted():
    report = CoverageLedger(DECLARED_SITES)
    assert report.expected_calls["head.reach"] == 1
    assert report.observed_calls["head.reach"] == 0
    assert report.row("head.reach")["state"] == "UNREACHED", "an un-fired hook is not a zero observation"


def test_f2_a_site_that_never_fired_stays_null_not_zero():
    report = CoverageLedger(DECLARED_SITES)
    for row in report.rows():
        assert row["observed_calls"] is None or row["state"] == "OBSERVED"
    assert report.complete is False


def test_f2_full_firing_is_the_only_complete_case():
    report = CoverageLedger(DECLARED_SITES)
    for site in DECLARED_SITES:
        report.fire(site)
    assert all(row["observed_calls"] == 1 for row in report.rows())
    assert report.complete is True
    assert report.receipt_completeness() == "COMPLETE"


def test_f2_one_hook_error_makes_the_whole_receipt_incomplete():
    report = CoverageLedger(DECLARED_SITES)
    for site in DECLARED_SITES:
        report.fire(site)
    report.error("head.reach", "RuntimeError: hook raised")
    assert report.complete is False, "a failed hook may not license green coverage"
    assert report.receipt_completeness() == "INCOMPLETE"
    assert report.row("head.reach")["state"] == "ERROR"


def test_f2_a_partial_hook_is_incomplete_not_complete():
    report = CoverageLedger(DECLARED_SITES)
    report.fire("answer.scores")
    assert report.complete is False
    assert report.receipt_completeness() == "INCOMPLETE"


# ===========================================================================
# F3 -- wrong parent / site / shape / round / basis are refused (HH02, HH05)
# ===========================================================================
def _valid_declaration():
    return {
        "parent": "cas_meta2.typed_teaching.pointer_learner.PointerLearner._reach_options",
        "site": "head.reach",
        "shape": (4, 6),
        "round_index": 3,
        "basis": "REACH_OPTION_LOGITS__WITHIN_CHECKPOINT",
    }


def test_f3_a_correct_declaration_is_accepted():
    observed = {"parent": _valid_declaration()["parent"], "site": "head.reach",
                "shape": (4, 6), "round_index": 3,
                "basis": "REACH_OPTION_LOGITS__WITHIN_CHECKPOINT"}
    assert admit_intervention_target(declared=_valid_declaration(), observed=observed) == "ADMITTED"


@pytest.mark.parametrize("key, wrong_value, expected_code", [
    ("parent", "cas_meta2.typed_teaching.pointer_learner.PointerLearner.world_head",
     "WRONG_PARENT_REFUSED"),
    ("site", "head.node", "WRONG_SITE_REFUSED"),
    ("shape", (6, 4), "WRONG_SHAPE_REFUSED"),
    ("round_index", 4, "WRONG_ROUND_REFUSED"),
    ("basis", "WORLD_HEAD_LOGITS__WITHIN_CHECKPOINT", "WRONG_BASIS_REFUSED"),
])
def test_f3_each_wrong_key_is_refused_with_its_own_reason(key, wrong_value, expected_code):
    observed = {"parent": _valid_declaration()["parent"], "site": "head.reach",
                "shape": (4, 6), "round_index": 3,
                "basis": "REACH_OPTION_LOGITS__WITHIN_CHECKPOINT"}
    observed[key] = wrong_value
    with pytest.raises(Refusal) as caught:
        admit_intervention_target(declared=_valid_declaration(), observed=observed)
    assert caught.value.code == expected_code, (
        "each wrong key must name itself; a generic refusal is not a diagnosis")


@pytest.mark.parametrize("key", ["parent", "site", "shape", "round_index", "basis"])
def test_f3_a_refused_target_is_never_written(key):
    """Refusal must happen before the first write, not after a partial edit."""
    tensor = StubTensor([[1.0, 1.0, 1.0, 1.0, 1.0, 1.0]])
    observed = {"parent": _valid_declaration()["parent"], "site": "head.reach",
                "shape": (4, 6), "round_index": 3,
                "basis": "REACH_OPTION_LOGITS__WITHIN_CHECKPOINT"}
    observed[key] = {"parent": "elsewhere", "site": "head.node", "shape": (6, 4),
                     "round_index": 9, "basis": "OTHER"}[key]
    with pytest.raises(Refusal):
        guarded_write(tensor, declared=_valid_declaration(), observed=observed,
                      row=0, column=2)
    assert tensor[0] == [1.0, 1.0, 1.0, 1.0, 1.0, 1.0], "a refused action must not touch the tensor"


def test_f3_a_pythia_coordinate_cannot_be_scoped_to_a_helm_site():
    """The two coordinate spaces do not intersect; the honest outcome is a refusal."""
    with pytest.raises(Refusal) as caught:
        translate_coordinate(pythia_layer=7, pythia_index=1234, target_basis="head.reach")
    assert caught.value.code == "COORDINATE_SPACE_UNMAPPED"


def test_f3_an_admitted_target_writes_exactly_one_coordinate():
    tensor = StubTensor([[1.0, 1.0, 1.0, 1.0, 1.0, 1.0]])
    observed = {"parent": _valid_declaration()["parent"], "site": "head.reach",
                "shape": (4, 6), "round_index": 3,
                "basis": "REACH_OPTION_LOGITS__WITHIN_CHECKPOINT"}
    guarded_write(tensor, declared=_valid_declaration(), observed=observed, row=0, column=2)
    assert tensor[0] == [1.0, 1.0, 0.0, 1.0, 1.0, 1.0]


# ===========================================================================
# F4 -- tamper and truncation detection against an anchor outside reach (HH16)
# ===========================================================================
def test_f4_a_self_recorded_digest_does_not_detect_tampering():
    """Executed demonstration of the failure mode this control exists to prevent."""
    record = {"n_updates": 5880, "pass": 30, "artifact_sha256": None}
    record["artifact_sha256"] = digest_of(record, ignore="artifact_sha256")
    tampered = dict(record, pass_=None)
    tampered["pass"] = 99
    tampered["artifact_sha256"] = digest_of(tampered, ignore="artifact_sha256")
    assert check_against_self_recorded_digest(tampered) == "SELF_CONSISTENT"
    assert tampered["pass"] == 99, "the tamper survives self-consistency; that is the point"


def test_f4_an_external_anchor_detects_the_same_tamper():
    record = {"n_updates": 5880, "pass": 30}
    anchor = digest_of(record, ignore=None)
    tampered = dict(record, pass_=99)
    tampered["pass"] = 99
    assert check_against_external_anchor(tampered, anchor) == "TAMPERED"


def test_f4_an_unchanged_record_passes_the_external_anchor():
    record = {"n_updates": 5880, "pass": 30}
    anchor = digest_of(record, ignore=None)
    assert check_against_external_anchor(record, anchor) == "MATCH"


def test_f4_truncation_is_detected_by_declared_length_and_digest():
    payload = b"a" * 512
    anchor = {"bytes": 512, "sha256": hashlib.sha256(payload).hexdigest()}
    assert check_payload(payload, anchor) == "MATCH"
    assert check_payload(payload[:400], anchor) == "TRUNCATED"
    assert check_payload(payload + b"x", anchor) == "TAMPERED"


def test_f4_an_empty_payload_is_not_a_pass():
    anchor = {"bytes": 512, "sha256": hashlib.sha256(b"a" * 512).hexdigest()}
    assert check_payload(b"", anchor) != "MATCH"


# ===========================================================================
# F5 -- cleanup after normal exit, exception and refusal (HH06, HH10)
# ===========================================================================
def test_f5_normal_exit_releases_every_handle():
    model = RecorderModel(seed=1)
    with RecorderObserver(model, observe=True):
        model.forward()
    assert model.handles_created == len(DECLARED_SITES)
    assert model.handles_removed == model.handles_created


def test_f5_an_exception_releases_every_handle():
    model = RecorderModel(seed=1)
    with pytest.raises(RuntimeError):
        with RecorderObserver(model, observe=True):
            model.forward()
            raise RuntimeError("simulated interruption inside the capture window")
    assert model.handles_removed == model.handles_created, "no hook may survive an interruption"


def test_f5_a_sham_no_op_leaves_the_forward_untouched():
    model = RecorderModel(seed=1)
    with RecorderObserver(model, observe=True, intervention=ShamIntervention(gain=0.0)):
        prediction = model.forward()
    assert prediction == RecorderModel(seed=1).forward(), "gain 0.0 must be neutral"


def test_f5_a_refused_intervention_leaves_task_output_and_handles_clean():
    model = RecorderModel(seed=1)
    clean = RecorderModel(seed=1)
    with pytest.raises(Refusal):
        with RecorderObserver(model, observe=True,
                              intervention=ShamIntervention(gain=1.0, wrong_basis=True)):
            model.forward()
    assert model.handles_removed == model.handles_created
    assert model.task_output_snapshot() == clean.task_output_snapshot(), (
        "a refused action may not change parameters, RNG or the assembled scores")


# ===========================================================================
# Pinned-identity checks: the vendored harness copy really is the pinned bytes
# ===========================================================================
def test_vendored_harness_copy_is_byte_identical_to_pinned_master():
    if not HARNESS_VENDOR_COPY.is_file():
        pytest.skip("VENDOR_COPY_UNAVAILABLE: %s" % HARNESS_VENDOR_COPY)
    raw = HARNESS_VENDOR_COPY.read_bytes()
    assert len(raw) == HARNESS_BYTES
    assert hashlib.sha256(raw).hexdigest() == HARNESS_SHA256


def test_vendored_harness_copy_hash_object_equals_the_git_blob():
    """git hash-object of the bytes must equal the blob id recorded by Codex."""
    if not HARNESS_VENDOR_COPY.is_file():
        pytest.skip("VENDOR_COPY_UNAVAILABLE")
    raw = HARNESS_VENDOR_COPY.read_bytes()
    header = b"blob %d\x00" % len(raw)
    assert hashlib.sha1(header + raw).hexdigest() == HARNESS_BLOB


def test_declared_sites_match_the_published_capture_contract():
    contract = HERE / "_codex_pkg_62bb7f71" / "CAPTURE_CONTRACT.json"
    if not contract.is_file():
        pytest.skip("CAPTURE_CONTRACT_UNAVAILABLE")
    published = json.loads(contract.read_text(encoding="utf-8"))
    assert tuple(published["sites"]) == DECLARED_SITES, (
        "the declared site list changed; re-derive every coverage number")


# ===========================================================================
# Reviewer-owned helpers and stubs. No production code is imported.
# ===========================================================================
class Refusal(Exception):
    """A refusal is a result, not a crash. The code names the wrong key."""

    def __init__(self, code, detail=""):
        super().__init__("%s: %s" % (code, detail))
        self.code = code


class CoverageLedger:
    """Expected versus observed calls. Un-fired is UNREACHED, never 0."""

    def __init__(self, declared):
        self.declared = list(declared)
        self.expected_calls = {name: 1 for name in self.declared}
        self.observed_calls = {name: 0 for name in self.declared}
        self.state = {name: "UNREACHED" for name in self.declared}

    def fire(self, site):
        if site not in self.expected_calls:
            raise Refusal("UNDECLARED_SITE", site)
        self.observed_calls[site] += 1
        self.state[site] = "OBSERVED"

    def error(self, site, detail):
        self.state[site] = "ERROR"
        self.observed_calls[site] = 0
        self.detail = detail

    @property
    def complete(self):
        return bool(self.declared) and all(s == "OBSERVED" for s in self.state.values())

    def receipt_completeness(self):
        return "COMPLETE" if self.complete else "INCOMPLETE"

    def row(self, site):
        observed = self.observed_calls[site]
        return {"site": site, "expected_calls": self.expected_calls[site],
                "observed_calls": (observed if self.state[site] == "OBSERVED" else None),
                "state": self.state[site]}

    def rows(self):
        return [self.row(site) for site in self.declared]


def admit_intervention_target(*, declared, observed):
    """Refuse a wrong parent, site, shape, round or basis, naming the wrong key."""
    checks = (("parent", "WRONG_PARENT_REFUSED"), ("site", "WRONG_SITE_REFUSED"),
              ("shape", "WRONG_SHAPE_REFUSED"), ("round_index", "WRONG_ROUND_REFUSED"),
              ("basis", "WRONG_BASIS_REFUSED"))
    for key, code in checks:
        left, right = declared[key], observed.get(key)
        if key == "shape":
            left, right = tuple(left), tuple(right) if right is not None else None
        if left != right:
            raise Refusal(code, "declared=%r observed=%r" % (left, right))
    return "ADMITTED"


def guarded_write(tensor, *, declared, observed, row, column):
    """Admit first, write second. A refusal writes nothing."""
    admit_intervention_target(declared=declared, observed=observed)
    tensor.set(row, column, 0.0)
    return "WRITTEN"


def translate_coordinate(*, pythia_layer, pythia_index, target_basis):
    """There is no derived map from the Pythia MLP grid to a HELM site."""
    raise Refusal("COORDINATE_SPACE_UNMAPPED",
                  "pythia (layer=%r,index=%r) -> %s" % (pythia_layer, pythia_index, target_basis))


def canonical_bytes(record, ignore=None):
    payload = {k: v for k, v in record.items() if k != ignore}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_of(record, ignore=None):
    return hashlib.sha256(canonical_bytes(record, ignore=ignore)).hexdigest()


def check_against_self_recorded_digest(record):
    return ("SELF_CONSISTENT"
            if digest_of(record, ignore="artifact_sha256") == record["artifact_sha256"]
            else "SELF_INCONSISTENT")


def check_against_external_anchor(record, anchor):
    return "MATCH" if digest_of(record, ignore=None) == anchor else "TAMPERED"


def check_payload(payload, anchor):
    if len(payload) < anchor["bytes"]:
        return "TRUNCATED"
    if hashlib.sha256(payload).hexdigest() != anchor["sha256"]:
        return "TAMPERED"
    if len(payload) != anchor["bytes"]:
        return "TAMPERED"
    return "MATCH"


class StubTensor:
    def __init__(self, data):
        self.data = [list(row) for row in data]

    def set(self, row, column, value):
        self.data[row][column] = value

    def __getitem__(self, row):
        return self.data[row]

    def __len__(self):
        return len(self.data)


class RecorderModel:
    """A deterministic stand-in learner: parameters, an input, and an RNG stream.

    It exists so that OFF versus OBSERVE_ONLY can be compared on state the way the
    real comparison will be made: identical initial state, then check every field.
    """

    def __init__(self, *, seed):
        self.seed = seed
        self.parameters = {"w_in": [0.5, -1.25, 2.0, 0.75],
                           "w_out": [1.5, -0.25, 0.5, -1.0]}
        self.input_vector = [1.0, 2.0, -1.0, 0.5]
        self.handles_created = 0
        self.handles_removed = 0
        self._hooks = []
        self._rng = random.Random(seed)
        self._rng_state_before = self._rng.getstate()

    def register(self, hook):
        self._hooks.append(hook)
        self.handles_created += 1
        return HookHandle(self, hook)

    def release(self, handle):
        if handle in self._hooks:
            self._hooks.remove(handle)
            self.handles_removed += 1

    def forward(self):
        w_in = self.parameters["w_in"]
        self.layer_output = [a * b for a, b in zip(w_in, self.input_vector)]
        for hook in list(self._hooks):
            hook(self.layer_output)
        w_out = self.parameters["w_out"]
        self.scores = [a * b for a, b in zip(self.layer_output, w_out)]
        prediction = self.scores.index(max(self.scores))
        self._rng.random()
        return prediction

    def state_snapshot(self):
        return {"parameters": json.dumps(self.parameters, sort_keys=True),
                "input_vector": list(self.input_vector),
                "layer_output": list(getattr(self, "layer_output", [])),
                "scores": list(getattr(self, "scores", [])),
                "rng_state": repr(self._rng.getstate())}

    def task_output_snapshot(self):
        """Everything the task can see: parameters, RNG and the assembled scores.

        The intermediate layer output is deliberately excluded. A refused action may
        legitimately leave a half-computed intermediate value behind, because the
        refusal happens when the action is attempted. What must not change is what
        the caller receives.
        """
        return {"parameters": json.dumps(self.parameters, sort_keys=True),
                "scores": list(getattr(self, "scores", [])),
                "rng_state": repr(self._rng.getstate())}


class HookHandle:
    def __init__(self, owner, hook):
        self.owner = owner
        self.hook = hook
        self.removed = False

    def remove(self):
        if not self.removed:
            self.owner.release(self.hook)
            self.removed = True


class RecorderObserver:
    """Attaches one observer per declared site and yields its own receipt."""

    def __init__(self, model, *, observe, intervention=None):
        self.model = model
        self.observe = observe
        self.intervention = intervention
        self.handles = []
        self.receipt = {"capture_mode": "OBSERVE_ONLY" if observe else "OFF"}

    def __enter__(self):
        counts = {"observed_sites": 0, "overhead_ns": 0, "before": None, "after": None}

        def make_hook(site):
            def hook(values):
                if not self.observe:
                    return values
                counts["observed_sites"] += 1
                counts["overhead_ns"] += 1000
                counts["before"] = list(values)
                if self.intervention is not None:
                    self.intervention.apply(values, site=site)
                counts["after"] = list(values)
                return values
            return hook

        for site in DECLARED_SITES:
            self.handles.append(self.model.register(make_hook(site)))
        self._counts = counts
        return self.receipt

    def __exit__(self, exc_type, exc, tb):
        for handle in self.handles:
            handle.remove()
        counts = self._counts
        self.receipt.update({"observed_sites": counts["observed_sites"],
                             "before": counts["before"], "after": counts["after"],
                             "overhead_ns": counts["overhead_ns"],
                             "overhead_charged": self.observe,
                             "handles_created": self.model.handles_created,
                             "handles_removed": self.model.handles_removed})
        return False


class ShamIntervention:
    """A bounded scalar action. It refuses a wrong basis instead of applying blind."""

    def __init__(self, *, gain, wrong_basis=False):
        self.gain = float(gain)
        self.wrong_basis = wrong_basis

    def apply(self, values, *, site):
        if self.wrong_basis:
            raise Refusal("WRONG_BASIS_REFUSED",
                          "intervention basis does not match site %s" % site)
        if self.gain == 0.0:
            return values
        values[0] = values[0] * (1.0 - self.gain)
        return values


# ===========================================================================
# NOT_RUN -- needs an admitted venue with a real HELM checkpoint
# ===========================================================================
NOT_RUN_FOR_ADMITTED_VENUE = (
    ("neutrality_on_real_checkpoint",
     "OFF vs OBSERVE_ONLY on one preserved checkpoint: prediction, Parts/Reach scores, "
     "model/optimizer state, RNG, hook removal, wall overhead (HH03)",
     "python -m pytest -q -p no:cacheprovider <file> -k neutrality_on_real_checkpoint"),
    ("real_site_coverage",
     "enumerate real call sites of _reach_options/_node_options/head_logits and record "
     "expected versus observed per-site call counts (HH04)",
     "requires the admitted diagnostic worker and one preserved checkpoint"),
    ("matched_task_level_control",
     "score Parts/Reach under baseline, no-op, target suppression and a matched off-path "
     "suppression of equal rank and gain (HH12)",
     "requires the CAS-HH-RDE-01-PILOT priced record; not authorized here"),
)

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
