"""CAS-HH-RDE-01 / A -- configuration and readout bridge from the CAS Harness to HELM capture records.

WHAT THIS MODULE IS. The configuration/readout half of Claude's leased adapter (CAPTURE_CONTRACT.json
`scopes.Claude`). It consumes raw capture records shaped exactly like the contract (identity + tensor +
coverage fields), reuses the CAS Harness's existing detection code on them, and produces a versioned
configuration record with an explicit claim level. It never captures anything itself: capture is Codex's
`observation.py` (not written at `62bb7f71`); the learner's own passive callback is
`_rounds(..., observe=)` at `pointer_learner.py:1197-1198` (`c45f775f`), which delivers
`observe(round_index, hidden_input)` and ignores the callback's return.

WHAT IS REUSED FROM THE HARNESS, AND HOW (HH01/HH07). The vendored source is
`harness_capture_vendor/probe_runner.py` (Harness commit `e8537e6c`, sha256 `543666e5...`, stdlib only).
`HARNESS_REUSE` classifies every reused name as EXACT_SHARED_IMPLEMENTATION, VERSIONED_ADAPTATION,
SEMANTIC_CORRESPONDENCE or NOT_REUSED. The top-K detector `_top_k_neurons` is called unchanged on a
`CaptureState` whose `mlp_post` key is the HELM round index and whose value is ONE node row's signed
values; its `layer`/`index` output is relabeled `round_index`/`coordinate`. Its Pythia meaning ("neuron")
is NOT carried over: every contract site is a projected or output coordinate (HH05), so the configuration
kind is `PROJECTED_COORDINATE_SET`, never `ACTUAL_UNIT`.

WHAT THIS MODULE REFUSES. Captures whose `coordinate_meaning` disagrees with the site table; nonfinite
values; coverage that over-counts; configurations fitted on the confirmation split; use of an unfrozen
configuration for confirmation; an `EXACT` CAS mapping (no HELM mapping is exact by construction); claim
levels above the pilot's reach; a Pythia probe "valid on HELM" without a HELM calibration record.

Canonical CAS names are pinned verbatim (`CANONICAL_NOETICS`) and never edited to fit clusters (HH09).
Authority: `OBSERVATION_ONLY_NO_PROMOTION`. Basis: `WITHIN_CHECKPOINT_ONLY`. Capture default: `OFF`.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .harness_capture_vendor import probe_runner as harness

CONTRACT_SCHEMA = "helm.harness.capture.contract/1"
CAPTURE_RECORD_SCHEMA = "helm.harness.raw-capture/0.1"
CONFIGURATION_SCHEMA = "helm.harness.configuration-record/0.1"
READOUT_SCHEMA = "helm.harness.readout/0.1"
TASK_ID = "CAS-HH-RDE-01"
EXTENDS = "ORIGINAL-HELM-DIAG-01"

SCIENTIFIC_SOURCE = "c45f775f225dd06cc20cdf313f0a0398486e0d61"
LEARNER_SHA256 = "0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8"
HARNESS_SOURCE_COMMIT = "e8537e6ce9e93242fb11dec36c03dbcafa86042c"
HARNESS_VENDOR_SHA256 = "543666e576a559b1bfd15d9c63b33d401de3dcb47a3af13325700060abca9209"
HARNESS_VENDOR_PATH = "research/helm_self_improvement/harness_capture_vendor/probe_runner.py"
CONTRACT_PATH = Path(__file__).resolve().parent / "cas_hh_rde_01" / "CAPTURE_CONTRACT.json"

AUTHORITY = "OBSERVATION_ONLY_NO_PROMOTION"
BASIS = "WITHIN_CHECKPOINT_ONLY"
CAPTURE_DEFAULT = "OFF"
PASSIVE_MODES = ("OFF", "OBSERVE_ONLY", "NO_OP_CONTROL")

# Learner anchors at `c45f775f`, recorded for documentation and expected-call arithmetic. Tensor widths are
# NEVER checked against these numbers: the captured shape and the module's own `in_features` are the authority
# (the learner's own lesson, `pointer_learner.py:1339-1347`).
LEARNER_ANCHORS = {"WIDTH": ("pointer_learner.py:197", 64), "CORE_ROUNDS": ("pointer_learner.py:198", 8),
                   "REACH_OPTION_COUNT": ("pointer_learner.py:252", 2),
                   "BLOCK_INPUT_WIDTH": ("pointer_learner.py:409", 192)}
CORE_ROUNDS = LEARNER_ANCHORS["CORE_ROUNDS"][1]

IDENTITY_FIELDS = ("checkpoint_sha256", "input_sha256", "source_sha256", "site", "call_index", "round_index")
TENSOR_FIELDS = ("shape", "dtype", "device", "coordinate_meaning", "signed_values")
COVERAGE_FIELDS = ("expected_calls", "observed_calls", "stored_calls", "errors", "complete")
DTYPES = ("float32", "float16", "bfloat16", "float64")

# The 14 contract sites, each bound to the exact learner statement it names. `answer_path` is what the
# statement feeds in `head_logits` (`pointer_learner.py:1578-1620`): Parts slots (`node`/`participant`) read
# `node_rows`; Reach reads `_reach_options` + `_node_options`. `world_head` (line 1566) feeds neither, so it
# is not a site and no Parts/Reach dependence on it is inferred. `hidden_unit` is False everywhere: no site is
# an individual hidden unit of the `^6` block (`model.preactivations`, line 902, is not in contract v1).
SITE_SEMANTICS = {
    "input.mapping": dict(tensor="reading (dict, not a tensor)", basis="READING", per_round=False,
                          anchor="pointer_learner.py:1927", answer_path="BOTH", hidden_unit=False,
                          coordinate_meaning="typed reading fields of one packet; no tensor coordinates"),
    "graph.initial_state": dict(tensor="hidden = _rms_unit(node_encode(raw))", basis="NODE_ROW_STATE",
                                per_round=False, anchor="pointer_learner.py:1160", answer_path="BOTH",
                                hidden_unit=False,
                                coordinate_meaning="row = node in block order; column = RMS-normalised encoded state coordinate"),
    "graph.round_input": dict(tensor="hidden_input = _block_input(block_input)", basis="NODE_ROW_BLOCK_INPUT",
                              per_round=True, anchor="pointer_learner.py:1191-1198", answer_path="BOTH",
                              hidden_unit=False,
                              coordinate_meaning="row = node in block order; column = blended encoded input coordinate of core_block (projected, not a hidden unit)"),
    "graph.round_update": dict(tensor="update = model.core_block(hidden_input)", basis="NODE_ROW_UPDATE",
                               per_round=True, anchor="pointer_learner.py:1199", answer_path="BOTH",
                               hidden_unit=False,
                               coordinate_meaning="row = node in block order; column = core_block output coordinate before cap/tanh/rate scaling"),
    "graph.round_state": dict(tensor="hidden after the round update", basis="NODE_ROW_STATE", per_round=True,
                              anchor="pointer_learner.py:1200", answer_path="BOTH", hidden_unit=False,
                              coordinate_meaning="row = node in block order; column = RMS-normalised state coordinate after the round"),
    "graph.node_state": dict(tensor="forward.hidden (final)", basis="NODE_ROW_STATE", per_round=False,
                             anchor="pointer_learner.py:1303", answer_path="BOTH", hidden_unit=False,
                             coordinate_meaning="row = node in block order; column = final RMS-normalised state coordinate"),
    "graph.query_state": dict(tensor="query_value = _encode_query()", basis="QUERY_VECTOR", per_round=False,
                              anchor="pointer_learner.py:1309,1361-1376", answer_path="BOTH", hidden_unit=False,
                              coordinate_meaning="single row; column = encoded query coordinate with focal argument states spliced in"),
    "graph.pointer_query": dict(tensor="pointer_query = model.pointer_key(query_value)", basis="POINTER_KEY_SPACE",
                                per_round=False, anchor="pointer_learner.py:1313", answer_path="REACH",
                                hidden_unit=False,
                                coordinate_meaning="single row; column = pointer-key coordinate matched against node states"),
    "head.node": dict(tensor="node_rows = model.node_head(node_input)", basis="NODE_HEAD_OUTPUT", per_round=False,
                      anchor="pointer_learner.py:1347", answer_path="PARTS", hidden_unit=False,
                      coordinate_meaning="row = node in block order; column = node-head output logit coordinate"),
    "head.reach": dict(tensor="model.reach_option_head(value).reshape(-1)", basis="REACH_OPTION_LOGITS",
                       per_round=False, anchor="pointer_learner.py:1492-1512", answer_path="REACH",
                       hidden_unit=False,
                       coordinate_meaning="single row; column 0 = ABSENT logit, column 1 = DIRECT logit"),
    "head.node_pointer": dict(tensor="states.matmul(pointer_query)", basis="NODE_POINTER_LOGITS", per_round=False,
                              anchor="pointer_learner.py:1406-1417", answer_path="REACH", hidden_unit=False,
                              coordinate_meaning="single row; column k = pointer logit of the k-th requested node rank (VIA_N options)"),
    "answer.scores": dict(tensor="scores = _logit_rows(...)", basis="SLOT_SCORES", per_round=False,
                          anchor="pointer_learner.py:1938", answer_path="BOTH", hidden_unit=False,
                          coordinate_meaning="per slot: one score per declared symbol in slot order"),
    "answer.decisions": dict(tensor="slots.score_decisions(packet, scores)", basis="DECISIONS", per_round=False,
                             anchor="pointer_learner.py:1940", answer_path="BOTH", hidden_unit=False,
                             coordinate_meaning="typed decisions; not a tensor"),
    "answer.assembly": dict(tensor="slots.assemble_answer(packet, decisions)", basis="ANSWER", per_round=False,
                            anchor="pointer_learner.py:1941", answer_path="BOTH", hidden_unit=False,
                            coordinate_meaning="assembled public answer; not a tensor"),
}
SITES = tuple(SITE_SEMANTICS)
TENSOR_SITES = tuple(site for site in SITES if SITE_SEMANTICS[site]["basis"]
                     not in ("READING", "DECISIONS", "ANSWER", "SLOT_SCORES"))
LOGIT_SITES = ("head.node", "head.reach", "head.node_pointer")

CONFIGURATION_KINDS = ("ACTUAL_UNIT_SET", "PROJECTED_COORDINATE_SET", "DIRECTION", "SUBSPACE",
                       "CROSS_ROUND_PATTERN", "UNKNOWN")
SPLITS = ("DISCOVERY", "CONFIRMATION", "SYNTHETIC_FIXTURE")
CLAIM_LEVELS = ("OBSERVED_CONFIGURATION", "STIMULUS_SELECTIVE", "CAS_READOUT_SUPPORTED",
                "TASK_CAUSAL_CONTRIBUTION_SUPPORTED", "TARGETED_REPAIR_GAIN_SUPPORTED",
                "NATIVE_IMPROVEMENT_POLICY_GAIN_SUPPORTED")
PILOT_CLAIM_CEILING = "TASK_CAUSAL_CONTRIBUTION_SUPPORTED"
MAPPING_CLASSES = ("EXACT", "ADAPTED", "PROPOSED", "UNKNOWN")
REUSE_RELATIONSHIPS = ("EXACT_SHARED_IMPLEMENTATION", "VERSIONED_ADAPTATION", "SEMANTIC_CORRESPONDENCE",
                       "NOT_REUSED", "UNKNOWN")

# Verbatim canonical names (docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md, Clarification 1). Never edited here.
CANONICAL_NOETICS = {"^0": "Idea", "^1": "Mind", "^2": "Positive", "^3": "Negative", "^4": "Vibration",
                     "^5": "Female", "^6": "Male", "^7": "Rhythm", "^8": "Above/Cause", "^9": "Below/Effect"}
DOMAINS = ("P", "C", "E", "O")
REGISTERS = ("T", "A", "f", "E")

HARNESS_REUSE = {
    "CaptureState": dict(relationship="EXACT_SHARED_IMPLEMENTATION", used_by="detect_top_k",
                         note="mlp_post key = HELM round index (Harness: layer); value = one node row's signed values"),
    "_top_k_neurons": dict(relationship="EXACT_SHARED_IMPLEMENTATION", used_by="detect_top_k",
                           note="algorithm unchanged (abs-value top-K, signed value carried); output relabeled round_index/coordinate; 'neuron' meaning not transferred"),
    "_softmax_margin": dict(relationship="VERSIONED_ADAPTATION", used_by="readout_margin",
                            note="formula reused; MARGIN_SAT=6.0 is Pythia-160M empirical, not HELM-calibrated; readout labeled accordingly"),
    "EraserIntervention": dict(relationship="SEMANTIC_CORRESPONDENCE", used_by="diagnostic_intervention.suppression_factor",
                               note="(coords, gain) record and factor=max(0,1-max(0,gain)) reused; _apply_eraser indexes [0,-1,idx] on a 3-D last-token tensor and is not applicable to HELM 2-D node rows"),
    "capture_probes": dict(relationship="SEMANTIC_CORRESPONDENCE", used_by="diagnostic_intervention.apply",
                           note="register-yield-always-remove context-manager pattern reused; gpt_neox.layers lookup not applicable"),
    "resolve_probes": dict(relationship="NOT_REUSED", used_by=None, note="Pythia probe pipeline names"),
    "summarise": dict(relationship="NOT_REUSED", used_by=None, note="token/attention semantics absent in HELM"),
    "_mode7_edges_from_attentions": dict(relationship="NOT_REUSED", used_by=None, note="no attention tensors in HELM sites"),
}


class ConfigurationRefused(ValueError):
    def __init__(self, code, detail=""):
        super().__init__(code if not detail else "%s: %s" % (code, detail))
        self.code = code


def _refuse(code, detail=""):
    raise ConfigurationRefused(code, detail)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _hex64(value, code):
    if not (type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)):
        _refuse(code, repr(value))
    return value


def _finite_float(value, code):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        _refuse(code, repr(value))
    return float(value)


# ---------------------------------------------------------------------------------------------------------
# Contract pin (HH01)
# ---------------------------------------------------------------------------------------------------------

def load_contract(path=CONTRACT_PATH):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def check_contract(contract):
    """The module's constants must restate the contract exactly; any drift is a refusal, not a warning."""
    if contract.get("schema") != CONTRACT_SCHEMA:
        _refuse("CONTRACT_SCHEMA", repr(contract.get("schema")))
    if contract.get("scientific_source") != SCIENTIFIC_SOURCE or contract.get("learner_sha256") != LEARNER_SHA256:
        _refuse("CONTRACT_SOURCE_PIN")
    if tuple(contract.get("sites", ())) != SITES:
        _refuse("CONTRACT_SITES", "contract %r != module %r" % (contract.get("sites"), SITES))
    raw = contract.get("raw_capture", {})
    if (tuple(raw.get("identity", ())) != IDENTITY_FIELDS or tuple(raw.get("tensor", ())) != TENSOR_FIELDS
            or tuple(raw.get("coverage", ())) != COVERAGE_FIELDS):
        _refuse("CONTRACT_FIELDS")
    if raw.get("authority") != AUTHORITY or raw.get("basis") != BASIS or raw.get("capture_default") != CAPTURE_DEFAULT:
        _refuse("CONTRACT_AUTHORITY")
    if tuple(contract.get("passive_modes", ())) != PASSIVE_MODES:
        _refuse("CONTRACT_MODES")
    claude = contract.get("scopes", {}).get("Claude", [])
    if "research/helm_self_improvement/diagnostic_configuration.py" not in claude:
        _refuse("CONTRACT_SCOPE", "this file is not in the Claude scope")
    return {"schema": CONTRACT_SCHEMA, "sites": len(SITES), "contract_digest": digest(contract)}


# ---------------------------------------------------------------------------------------------------------
# Coverage and raw capture records (HH04, HH05, HH06)
# ---------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Coverage:
    expected_calls: int
    observed_calls: int
    stored_calls: int
    errors: tuple
    complete: bool


def coverage(expected_calls, observed_calls, stored_calls, errors=()):
    """A missing hook is INCOMPLETE coverage, never a zero-valued observation. Over-counting is refused."""
    for name, value in (("expected_calls", expected_calls), ("observed_calls", observed_calls),
                        ("stored_calls", stored_calls)):
        if type(value) is not int or value < 0:
            _refuse("COVERAGE_COUNT", "%s=%r" % (name, value))
    errors = tuple(str(row) for row in errors)
    if observed_calls > expected_calls:
        _refuse("COVERAGE_OVERCOUNT", "observed %d > expected %d" % (observed_calls, expected_calls))
    if stored_calls > observed_calls:
        _refuse("COVERAGE_OVERCOUNT", "stored %d > observed %d" % (stored_calls, observed_calls))
    complete = not errors and observed_calls == expected_calls and stored_calls == observed_calls
    return Coverage(expected_calls, observed_calls, stored_calls, errors, complete)


def require_complete(cov, purpose):
    if not isinstance(cov, Coverage) or not cov.complete:
        _refuse("COVERAGE_INCOMPLETE", "%s needs complete coverage, got %r" % (purpose, cov))
    return cov


@dataclass(frozen=True)
class RawCapture:
    schema: str
    checkpoint_sha256: str
    input_sha256: str
    source_sha256: str
    site: str
    call_index: int
    round_index: object
    shape: tuple
    dtype: str
    device: str
    coordinate_meaning: str
    signed_values: tuple
    basis: str

    @property
    def rows(self):
        return self.shape[0] if len(self.shape) == 2 else 1

    @property
    def width(self):
        return self.shape[-1]


def raw_capture(*, checkpoint_sha256, input_sha256, source_sha256, site, call_index, round_index, shape, dtype,
                device, coordinate_meaning, signed_values):
    """Validate one emitter record against the contract and the site table. Values are detached floats."""
    if site not in SITE_SEMANTICS:
        _refuse("SITE_UNKNOWN", repr(site))
    if site not in TENSOR_SITES:
        _refuse("SITE_NOT_TENSOR", "%s carries no tensor coordinates" % site)
    semantics = SITE_SEMANTICS[site]
    for name, value in (("checkpoint_sha256", checkpoint_sha256), ("input_sha256", input_sha256),
                        ("source_sha256", source_sha256)):
        _hex64(value, "CAPTURE_IDENTITY:" + name)
    if type(call_index) is not int or call_index < 0:
        _refuse("CAPTURE_CALL_INDEX", repr(call_index))
    if semantics["per_round"]:
        if type(round_index) is not int or not 0 <= round_index < CORE_ROUNDS:
            _refuse("CAPTURE_ROUND_INDEX", "%s needs 0..%d, got %r" % (site, CORE_ROUNDS - 1, round_index))
    elif round_index is not None:
        _refuse("CAPTURE_ROUND_INDEX", "%s is not a per-round site" % site)
    shape = tuple(shape)
    if not shape or len(shape) > 2 or any(type(v) is not int or v <= 0 for v in shape):
        _refuse("CAPTURE_SHAPE", repr(shape))
    if dtype not in DTYPES:
        _refuse("CAPTURE_DTYPE", repr(dtype))
    if type(device) is not str or not device:
        _refuse("CAPTURE_DEVICE", repr(device))
    if coordinate_meaning != semantics["coordinate_meaning"]:
        _refuse("COORDINATE_MEANING_MISMATCH", "%s: %r" % (site, coordinate_meaning))
    values = tuple(_finite_float(v, "CAPTURE_NONFINITE") for v in signed_values)
    if len(values) != math.prod(shape):
        _refuse("CAPTURE_VALUE_COUNT", "%d values for shape %r" % (len(values), shape))
    return RawCapture(CAPTURE_RECORD_SCHEMA, checkpoint_sha256, input_sha256, source_sha256, site, call_index,
                      round_index, shape, dtype, device, coordinate_meaning, values, semantics["basis"])


def capture_digest(capture):
    return digest(asdict(capture))


def row_values(capture, row):
    if type(row) is not int or not 0 <= row < capture.rows:
        _refuse("CAPTURE_ROW", "row %r of %d" % (row, capture.rows))
    width = capture.width
    return capture.signed_values[row * width:(row + 1) * width]


# ---------------------------------------------------------------------------------------------------------
# Probe compatibility versus validity (HH02, HH07, HH08)
# ---------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ProbeIdentity:
    name: str
    version: str
    substrate: str
    width: int
    fitted_split: str
    coefficients_sha256: str


def probe_compatibility(probe, site, width):
    """Mechanical compatibility only: loading and matching dimensions establish nothing about HELM meaning."""
    if site not in TENSOR_SITES:
        _refuse("SITE_NOT_TENSOR", repr(site))
    if type(width) is not int or width <= 0 or probe.width != width:
        _refuse("PROBE_WIDTH_MISMATCH", "%r vs site width %r" % (probe.width, width))
    return {"probe": probe.name, "version": probe.version, "site": site, "mechanical": True,
            "valid_on_helm": False, "reason": "MECHANICAL_ONLY_VALIDITY_REQUIRES_HELM_CALIBRATION"}


def probe_validity(probe, calibration):
    """Validity on HELM needs a HELM calibration record on the discovery split of the same source."""
    if calibration is None or type(calibration) is not dict:
        _refuse("PROBE_VALIDITY_UNESTABLISHED", "no HELM calibration record for %s" % probe.name)
    if calibration.get("substrate") != "HELM" or calibration.get("source_sha256") != LEARNER_SHA256:
        _refuse("PROBE_SUBSTRATE_TRANSFER_UNVALIDATED", "probe substrate %r" % probe.substrate)
    if calibration.get("split") != "DISCOVERY":
        _refuse("PROBE_FIT_SPLIT", repr(calibration.get("split")))
    _hex64(calibration.get("checkpoint_sha256"), "PROBE_CALIBRATION_CHECKPOINT")
    if type(calibration.get("cases")) is not int or calibration["cases"] < 1:
        _refuse("PROBE_CALIBRATION_CASES", repr(calibration.get("cases")))
    if calibration.get("coefficients_sha256") != probe.coefficients_sha256:
        _refuse("PROBE_COEFFICIENTS_MISMATCH")
    return {"probe": probe.name, "valid_on_helm": True, "checkpoint_sha256": calibration["checkpoint_sha256"],
            "cases": calibration["cases"], "controls": tuple(calibration.get("controls", ()))}


# ---------------------------------------------------------------------------------------------------------
# Configuration records (HH05, HH08, HH09)
# ---------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ConfigurationRecord:
    schema: str
    checkpoint_sha256: str
    source_sha256: str
    site: str
    basis: str
    kind: str
    hidden_unit: bool
    split: str
    family: str
    input_sha256s: tuple
    coordinates: tuple          # ((round_index or None, coordinate), ...)
    signed_values: tuple        # aligned with `coordinates`, from the discovery capture(s)
    row: int
    detector: dict
    cas_definition: dict
    response: dict
    claim_level: str
    evidence: tuple
    frozen: bool
    frozen_digest: object

    @property
    def configuration_id(self):
        return "helm-configuration-" + digest(_identity_body(self))


def _identity_body(record):
    body = asdict(record)
    body.pop("frozen"), body.pop("frozen_digest"), body.pop("claim_level"), body.pop("evidence")
    return body


def cas_mapping(noetic=None, domain=None, register=None, mapping_class="UNKNOWN"):
    """A CAS label is optional; when present it must be a canonical name and can never be EXACT."""
    if mapping_class not in MAPPING_CLASSES:
        _refuse("CAS_MAPPING_CLASS", repr(mapping_class))
    if mapping_class == "EXACT":
        _refuse("CAS_MAPPING_EXACT_UNSUPPORTED", "no HELM configuration-to-CAS mapping is exact by construction")
    if noetic is None:
        if mapping_class != "UNKNOWN" or domain is not None or register is not None:
            _refuse("CAS_MAPPING_UNLABELED", "no noetic means UNKNOWN with no domain or register")
        return {"noetic": None, "name": None, "domain": None, "register": None, "mapping_class": "UNKNOWN"}
    if noetic not in CANONICAL_NOETICS:
        _refuse("CAS_NOETIC_NONCANONICAL", repr(noetic))
    if domain is not None and domain not in DOMAINS:
        _refuse("CAS_DOMAIN", repr(domain))
    if register is not None and register not in REGISTERS:
        _refuse("CAS_REGISTER", repr(register))
    if mapping_class == "UNKNOWN":
        _refuse("CAS_MAPPING_CLASS", "a labeled mapping is PROPOSED or ADAPTED, not UNKNOWN")
    return {"noetic": noetic, "name": CANONICAL_NOETICS[noetic], "domain": domain, "register": register,
            "mapping_class": mapping_class}


def build_configuration(*, captures, row, coordinates, signed_values, detector, split, family, kind,
                        cas_definition=None, response=None):
    """One configuration over one site of one checkpoint, named from discovery captures only."""
    captures = tuple(captures)
    if not captures:
        _refuse("CONFIGURATION_NO_CAPTURES")
    first = captures[0]
    for capture in captures:
        if not isinstance(capture, RawCapture):
            _refuse("CONFIGURATION_CAPTURE_TYPE", repr(type(capture)))
        if (capture.site, capture.checkpoint_sha256, capture.source_sha256, capture.shape[-1]) != (
                first.site, first.checkpoint_sha256, first.source_sha256, first.shape[-1]):
            _refuse("CONFIGURATION_CAPTURE_MIXED", "captures differ in site, checkpoint, source or width")
    if split not in SPLITS:
        _refuse("CONFIGURATION_SPLIT", repr(split))
    if split == "CONFIRMATION":
        _refuse("CONFIGURATION_FIT_ON_CONFIRMATION", "configurations are named on DISCOVERY or SYNTHETIC_FIXTURE only")
    if kind not in CONFIGURATION_KINDS:
        _refuse("CONFIGURATION_KIND", repr(kind))
    semantics = SITE_SEMANTICS[first.site]
    if kind == "ACTUAL_UNIT_SET" and not semantics["hidden_unit"]:
        _refuse("CONFIGURATION_NOT_HIDDEN_UNIT", "%s coordinates are projected/output coordinates" % first.site)
    if type(row) is not int or not 0 <= row < first.rows:
        _refuse("CONFIGURATION_ROW", repr(row))
    coordinates = tuple((r, c) for r, c in coordinates)
    if not coordinates or len(set(coordinates)) != len(coordinates):
        _refuse("CONFIGURATION_COORDINATES", "empty or duplicated")
    for round_index, coordinate in coordinates:
        if semantics["per_round"]:
            if type(round_index) is not int or not 0 <= round_index < CORE_ROUNDS:
                _refuse("CONFIGURATION_ROUND", repr(round_index))
        elif round_index is not None:
            _refuse("CONFIGURATION_ROUND", "%s is not per-round" % first.site)
        if type(coordinate) is not int or not 0 <= coordinate < first.width:
            _refuse("CONFIGURATION_COORDINATE_RANGE", "%r of width %d" % (coordinate, first.width))
    signed_values = tuple(_finite_float(v, "CONFIGURATION_VALUE") for v in signed_values)
    if len(signed_values) != len(coordinates):
        _refuse("CONFIGURATION_VALUE_COUNT")
    if type(detector) is not dict or not {"name", "version", "harness_function", "relationship"} <= set(detector):
        _refuse("CONFIGURATION_DETECTOR", "name, version, harness_function, relationship required")
    if detector["relationship"] not in REUSE_RELATIONSHIPS:
        _refuse("CONFIGURATION_DETECTOR", repr(detector["relationship"]))
    if type(family) is not str or not family:
        _refuse("CONFIGURATION_FAMILY", repr(family))
    cas = cas_definition if cas_definition is not None else cas_mapping()
    if cas["mapping_class"] not in ("UNKNOWN", "PROPOSED"):
        _refuse("CAS_MAPPING_PREMATURE", "ADAPTED needs CAS_READOUT_SUPPORTED evidence via assign_claim")
    response = dict(response or {"support": len(captures), "uncertainty": None})
    return ConfigurationRecord(CONFIGURATION_SCHEMA, first.checkpoint_sha256, first.source_sha256, first.site,
                               first.basis, kind, bool(semantics["hidden_unit"]), split, family,
                               tuple(sorted({c.input_sha256 for c in captures})), coordinates, signed_values,
                               row, dict(detector), dict(cas), response, "OBSERVED_CONFIGURATION", (),
                               False, None)


def detect_top_k(captures, *, row, k, split, family):
    """Reuse the Harness top-K detector unchanged on one node row across the captured rounds.

    `harness._top_k_neurons` ranks by absolute value and carries the SIGNED value, so inhibition survives.
    Its `layer` becomes the HELM round index (None for non-round sites) and its `index` the coordinate. The
    result is a PROJECTED_COORDINATE_SET at the site's basis -- never a hidden-unit claim.
    """
    captures = tuple(captures)
    if not captures:
        _refuse("CONFIGURATION_NO_CAPTURES")
    if type(k) is not int or k <= 0:
        _refuse("DETECTOR_K", repr(k))
    state = harness.CaptureState()
    per_round = SITE_SEMANTICS[captures[0].site]["per_round"]
    for capture in captures:
        key = capture.round_index if per_round else 0
        if key in state.mlp_post:
            _refuse("CONFIGURATION_CAPTURE_MIXED", "two captures for round %r" % key)
        state.mlp_post[key] = list(row_values(capture, row))
    found = harness._top_k_neurons(state, k)
    coordinates = tuple((int(entry["layer"]) if per_round else None, int(entry["index"])) for entry in found)
    values = tuple(float(entry["activation"]) for entry in found)
    detector = {"name": "harness.top_k_abs", "version": HARNESS_SOURCE_COMMIT[:8],
                "harness_function": "_top_k_neurons", "relationship": HARNESS_REUSE["_top_k_neurons"]["relationship"],
                "parameters": {"k": k, "row": row, "ranking": "abs_value_desc"}}
    return build_configuration(captures=captures, row=row, coordinates=coordinates, signed_values=values,
                               detector=detector, split=split, family=family, kind="PROJECTED_COORDINATE_SET")


def support(record, captures):
    """Signed response of a fixed configuration over further stimuli; coactivation AND inhibition retained."""
    captures = tuple(captures)
    if not captures:
        _refuse("SUPPORT_NO_CAPTURES")
    per_round = SITE_SEMANTICS[record.site]["per_round"]
    by_input = {}
    for capture in captures:
        if (capture.site, capture.checkpoint_sha256, capture.source_sha256) != (
                record.site, record.checkpoint_sha256, record.source_sha256):
            _refuse("SUPPORT_CAPTURE_MISMATCH")
        by_input.setdefault(capture.input_sha256, {})[capture.round_index if per_round else None] = capture
    rows = []
    for input_sha256, rounds in sorted(by_input.items()):
        values = []
        for round_index, coordinate in record.coordinates:
            capture = rounds.get(round_index)
            if capture is None:
                _refuse("SUPPORT_ROUND_MISSING", "input %s round %r" % (input_sha256[:8], round_index))
            values.append(row_values(capture, record.row)[coordinate])
        rows.append(values)
    n = len(rows)
    per_coordinate = []
    for index in range(len(record.coordinates)):
        column = [row[index] for row in rows]
        mean = sum(column) / n
        spread = math.sqrt(sum((v - mean) ** 2 for v in column) / (n - 1)) if n > 1 else None
        per_coordinate.append({"coordinate": list(record.coordinates[index]), "mean_signed": mean,
                               "positive": sum(1 for v in column if v > 0), "negative": sum(1 for v in column if v < 0),
                               "zero": sum(1 for v in column if v == 0), "stdev": spread})
    return {"support": n, "inputs": tuple(sorted(by_input)), "per_coordinate": per_coordinate,
            "uncertainty": "SAMPLE_STDEV_PER_COORDINATE" if n > 1 else "SINGLE_STIMULUS_NO_SPREAD"}


def freeze_configuration(record):
    if record.frozen:
        _refuse("CONFIGURATION_ALREADY_FROZEN")
    return replace(record, frozen=True, frozen_digest=digest(_identity_body(record)))


def require_frozen(record, split):
    """Confirmation-split use needs a frozen record whose identity still matches its freeze digest."""
    if split not in SPLITS:
        _refuse("CONFIGURATION_SPLIT", repr(split))
    if split != "CONFIRMATION":
        return record
    if not record.frozen or record.frozen_digest != digest(_identity_body(record)):
        _refuse("CONFIGURATION_NOT_FROZEN", "confirmation use needs a frozen, unmodified configuration")
    return record


def assign_claim(record, level, evidence):
    """Monotone claim assignment. Every step above OBSERVED needs controls and an artifact; pilot-capped."""
    if level not in CLAIM_LEVELS:
        _refuse("CLAIM_LEVEL", repr(level))
    if CLAIM_LEVELS.index(level) > CLAIM_LEVELS.index(PILOT_CLAIM_CEILING):
        _refuse("CLAIM_LEVEL_OUTSIDE_PILOT", "%s is a later experiment (HH21)" % level)
    if CLAIM_LEVELS.index(level) < CLAIM_LEVELS.index(record.claim_level):
        _refuse("CLAIM_LEVEL_DOWNGRADE", "%s below %s; retire the record instead" % (level, record.claim_level))
    if level == "OBSERVED_CONFIGURATION":
        return record
    if type(evidence) is not dict or not evidence.get("controls") or not evidence.get("artifact"):
        _refuse("CLAIM_EVIDENCE", "controls and artifact required")
    _hex64(evidence.get("artifact_sha256"), "CLAIM_EVIDENCE_ARTIFACT_SHA256")
    if not record.frozen:
        _refuse("CONFIGURATION_NOT_FROZEN", "claims above OBSERVED need a frozen configuration")
    if level == "TASK_CAUSAL_CONTRIBUTION_SUPPORTED":
        if not evidence.get("intervention_receipt_sha256") or not evidence.get("matched_control_receipt_sha256"):
            _refuse("CLAIM_EVIDENCE", "task-causal claims need an intervention receipt and a matched control receipt")
        if evidence.get("task_metric") not in ("PARTS_REACH_SCORES", "CHECKED_ANSWER"):
            _refuse("CLAIM_EVIDENCE", "task-causal claims need a task metric, not a probe score")
    cas = dict(record.cas_definition)
    if level == "CAS_READOUT_SUPPORTED" and cas["noetic"] is not None and cas["mapping_class"] == "PROPOSED":
        cas["mapping_class"] = "ADAPTED"
    return replace(record, claim_level=level, evidence=record.evidence + (dict(evidence),), cas_definition=cas)


def configuration_to_json(record):
    body = asdict(record)
    body["configuration_id"] = record.configuration_id
    body["record_digest"] = digest(body)
    return canonical(body) + "\n"


def configuration_from_json(text):
    body = json.loads(text)
    expected = body.pop("record_digest", None)
    if expected != digest(body):
        _refuse("CONFIGURATION_RECORD_TAMPERED")
    body.pop("configuration_id")
    body["input_sha256s"] = tuple(body["input_sha256s"])
    body["coordinates"] = tuple(tuple(pair) for pair in body["coordinates"])
    body["signed_values"] = tuple(body["signed_values"])
    body["evidence"] = tuple(body["evidence"])
    record = ConfigurationRecord(**body)
    if record.frozen and record.frozen_digest != digest(_identity_body(record)):
        _refuse("CONFIGURATION_RECORD_TAMPERED", "frozen digest")
    return record


# ---------------------------------------------------------------------------------------------------------
# Readout (HH07): the Harness margin formula, labeled with its calibration substrate
# ---------------------------------------------------------------------------------------------------------

def readout_margin(logits, site):
    if site not in LOGIT_SITES:
        _refuse("READOUT_SITE", "%s carries no option logits" % site)
    values = [_finite_float(v, "READOUT_NONFINITE") for v in logits]
    if len(values) < 2:
        _refuse("READOUT_OPTIONS", "at least two options")
    top = sorted(values, reverse=True)[:2]
    return {"schema": READOUT_SCHEMA, "site": site, "options": len(values), "raw_margin": float(top[0] - top[1]),
            "normalised": harness._softmax_margin(values), "harness_function": "_softmax_margin",
            "relationship": HARNESS_REUSE["_softmax_margin"]["relationship"], "saturation_constant": 6.0,
            "calibration": "PYTHIA_160M_EMPIRICAL_NOT_HELM_CALIBRATED",
            "claim": "READOUT_LEVEL_ONLY_NOT_TASK_CAUSAL"}


def reuse_manifest():
    """HH01 record: parent, vendored Harness identity, learner identity, and every reuse relationship."""
    return {"schema": "helm.harness.reuse-manifest/0.1", "task": TASK_ID, "extends": EXTENDS,
            "cas_parent": {"definitions": "docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md Clarification 1",
                           "noetics": dict(CANONICAL_NOETICS), "domains": DOMAINS, "registers": REGISTERS},
            "harness": {"commit": HARNESS_SOURCE_COMMIT, "vendored_path": HARNESS_VENDOR_PATH,
                        "sha256": HARNESS_VENDOR_SHA256},
            "helm": {"scientific_source": SCIENTIFIC_SOURCE, "learner_sha256": LEARNER_SHA256,
                     "anchors": {k: {"line": v[0], "value": v[1]} for k, v in LEARNER_ANCHORS.items()}},
            "reuse": {name: dict(row) for name, row in HARNESS_REUSE.items()},
            "sites": {site: dict(row) for site, row in SITE_SEMANTICS.items()},
            "authority": AUTHORITY, "basis": BASIS, "capture_default": CAPTURE_DEFAULT}
