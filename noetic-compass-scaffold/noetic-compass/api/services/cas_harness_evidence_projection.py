"""Evidence-Packet redaction projection — the IP-containment core of the
CAS Harness "Explain this packet" AI explainer.

This module is the **only** path from a stored Evidence Packet (EP) to the model
input that backs the plain-English explainer. It is deliberately small, pure, and
allow-list-driven so the IP-containment guarantee is auditable field-by-field.

Authoritative design: ``docs/design/cas_harness_evidence_packet_ai_explainer_spec.md``
— §3 (just-enough / input minimalism), §4 (allow-list / deny-list), §5 (highlighted
prompts & blind spots).

Design contract (do not weaken):

1. **Allow-list driven (§4).** ``build_packet_projection`` copies ONLY the keys in
   :data:`CUSTOMER_FACING_ALLOW_LIST` (and the explicitly enumerated sub-keys of the
   nested customer-facing structures). Every other field on the EP — known or unknown,
   present now or added later — is dropped by default. New EP fields are invisible to
   the model until a human adds them here on purpose. This is "drop-unknown-by-default":
   the safe direction to fail.

2. **Status words verbatim (§4).** A proof chip's ``status`` is passed through exactly
   as recorded (``verified`` / ``present`` / ``missing`` / ``failed`` / ``unavailable``).
   It is NEVER normalized, softened, or mapped to "pass"/"ok". Honesty over polish.

3. **Verdict fidelity (§2 G1).** The literal verdict is copied verbatim, together with
   any scope qualifier (``decision_scope`` from the verifier decision, plus the audit
   scope's disposition). A scoped-validation ACCEPT must never read as a customer-
   production ACCEPT downstream, so the scope-carrying fields travel with the verdict.

4. **Deny-list never leaks (§4 G2).** This projection never reads or emits scoring math /
   NCCS weights, operator / drive / register internals, dial values, probe-generation
   logic or "why this probe", prompt templates, other tenants' data, or secrets. It only
   copies named customer-facing result fields; it never copies a whole nested EP object
   wholesale (which could smuggle internal keys), and it never serializes the raw packet.

5. **Highlighted prompts are evidence, not methodology (§5).** A blind-spot / inversion
   finding may carry the customer's OWN flagged prompt/input verbatim and the observed
   behavior that tripped the finding, plus which axis flagged and the severity band. The
   proprietary probe construction behind that prompt is NEVER included.

The public signature ``build_packet_projection(ep) -> dict`` is stable; the explainer
endpoint imports it.
"""

from __future__ import annotations

from typing import Any, Mapping


# ---------------------------------------------------------------------------
# Allow-list — the ONLY customer-facing top-level keys that may reach the model.
#
# Anything not in this set is dropped. Keep this list and the assembly logic in
# ``build_packet_projection`` in lock-step; the field-by-field test asserts both
# directions (every allow-listed key may appear; every other key is absent).
# ---------------------------------------------------------------------------
CUSTOMER_FACING_ALLOW_LIST: frozenset[str] = frozenset(
    {
        "verdict",            # literal verdict (ACCEPT / FLAG_FOR_HUMAN_REVIEW / SUPPRESS)
        "verdict_scope",      # scope qualifier(s) so scoped != customer-production
        "confidence",         # the packet's own confidence number, if it carries one
        "proof_chips",        # [{id, label, status}] — status VERBATIM
        "blind_spots",        # [{axis, severity_band, flagged_prompt, observed_behavior, note}]
        "anchor",             # {status, retention_mode, trace_id}
        "model_target",       # the customer's OWN declared model/endpoint label
        "audit_mode",         # BALANCED / HIGH_PRECISION / MAX_COVERAGE_TRIAGE
        "trace_id",           # evidence packet trace id (the only internal plumbing exposed)
        "timestamps",         # {created_at, updated_at, generated_at}
        "counts",             # {proof_chips_total, proof_chips_ready, blind_spots_total}
    }
)


# Allowed sub-keys for each nested customer-facing structure. Enumerated so a
# nested EP object can never smuggle an internal key through wholesale copying.
_PROOF_CHIP_KEYS: frozenset[str] = frozenset({"id", "label", "status"})
_BLIND_SPOT_KEYS: frozenset[str] = frozenset(
    {"axis", "severity_band", "flagged_prompt", "observed_behavior", "note"}
)
_ANCHOR_KEYS: frozenset[str] = frozenset({"status", "retention_mode", "trace_id"})

# Proof-chip status vocabulary (SPEC §4). The projection passes status through
# verbatim; this set exists only so an out-of-vocabulary status is preserved as-is
# rather than silently dropped (still never mapped to "pass").
_ALLOWED_CHIP_STATUSES: frozenset[str] = frozenset(
    {"verified", "present", "missing", "failed", "unavailable"}
)

# Proof-chip id -> customer-facing label. Mirrors ``_PROOF_CHIP_NAMES`` in
# ``cas_harness_audit_sessions``; used only when a chip lacks an explicit label.
_PROOF_CHIP_LABELS: dict[str, str] = {
    "model_proof": "Model proof",
    "cas_readout": "CAS readout",
    "causal_proof": "Causal proof",
    "control_proof": "Control proof",
    "output_proof": "Output proof",
    "packet_proof": "Packet proof",
}


def build_packet_projection(ep: Any) -> dict:
    """Project an Evidence Packet down to its customer-facing, model-safe view.

    This is the single, allow-list-driven redaction boundary between a stored
    Evidence Packet and the explainer's model input. Returns a plain ``dict``
    containing ONLY customer-facing fields (SPEC §4 allow-list); every other field
    — including any not yet known — is dropped by default.

    ``ep`` may be a Pydantic-style object exposing ``model_dump`` /  ``to_dict``,
    a dataclass-like object, or already a mapping. It is read defensively; missing
    fields simply produce a smaller projection rather than raising.

    Never includes (SPEC §4 deny-list): scoring math / NCCS weights, operator /
    drive / register internals, dial values, probe-generation logic, "why this
    probe", prompt templates, other tenants' data, or secrets.
    """
    packet = _as_mapping(ep)
    projection: dict[str, Any] = {}

    # --- verdict (literal) + scope qualifier (G1 verdict fidelity) -------------
    verdict = _clean_str(packet.get("verdict"))
    if verdict is not None:
        projection["verdict"] = verdict

    verdict_scope = _verdict_scope(packet)
    if verdict_scope:
        projection["verdict_scope"] = verdict_scope

    confidence = _clean_number(packet.get("confidence"))
    if confidence is not None:
        projection["confidence"] = confidence

    # --- proof chips (status VERBATIM) ----------------------------------------
    proof_chips = _project_proof_chips(packet)
    if proof_chips:
        projection["proof_chips"] = proof_chips

    # --- blind-spot / inversion findings (customer evidence, not methodology) --
    blind_spots = _project_blind_spots(packet)
    if blind_spots:
        projection["blind_spots"] = blind_spots

    # --- anchor status + trace_id ---------------------------------------------
    anchor = _project_anchor(packet)
    if anchor:
        projection["anchor"] = anchor

    # --- model target label, audit mode, timestamps, trace id ------------------
    model_target = _model_target(packet)
    if model_target is not None:
        projection["model_target"] = model_target

    audit_mode = _clean_str(packet.get("audit_mode"))
    if audit_mode is not None:
        projection["audit_mode"] = audit_mode

    trace_id = _trace_id(packet)
    if trace_id is not None:
        projection["trace_id"] = trace_id

    timestamps = _timestamps(packet)
    if timestamps:
        projection["timestamps"] = timestamps

    # --- counts ("4 of 6 proof chips ready") ----------------------------------
    counts = _counts(proof_chips, blind_spots)
    if counts:
        projection["counts"] = counts

    return projection


# ---------------------------------------------------------------------------
# Field projectors — each reads only named customer-facing keys.
# ---------------------------------------------------------------------------
def _verdict_scope(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Collect scope qualifiers so a scoped ACCEPT can never read as production.

    Pulls the verifier decision's ``decision_scope`` and the audit scope's
    ``verdict_disposition`` (e.g. ``held_for_human_review``) — both customer-facing
    scope statements. Scoring internals on these objects are NOT copied.
    """
    scope: dict[str, Any] = {}

    decision = _as_mapping(packet.get("verifier_decision"))
    decision_scope = _clean_str(decision.get("decision_scope"))
    if decision_scope is not None:
        scope["decision_scope"] = decision_scope
    decision_source = _clean_str(decision.get("source"))
    if decision_source is not None:
        scope["decision_source"] = decision_source

    audit_scope = _as_mapping(packet.get("audit_scope"))
    disposition = _clean_str(audit_scope.get("verdict_disposition"))
    if disposition is not None:
        scope["verdict_disposition"] = disposition
    scope_label = _clean_str(audit_scope.get("label"))
    if scope_label is not None:
        scope["scope_label"] = scope_label
    # NB: audit_scope["kind"] (e.g. ``open_weight_live_trace``) is an INTERNAL
    # scope-machine identifier, not customer-facing prose. It is intentionally not
    # projected — the customer-facing scope is fully carried by ``verdict_disposition``,
    # ``scope_label`` and ``internal_activation_access``. (It also collides with the
    # "weight" deny-token substring, so projecting it would trip the leak scan.)
    internal_access = audit_scope.get("internal_activation_access")
    if isinstance(internal_access, bool):
        scope["internal_activation_access"] = internal_access

    return scope


def _project_proof_chips(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Project proof / provenance chips to {id, label, status} with status verbatim.

    Accepts the chips under either ``proof_chips`` or ``provenance_chips`` (the
    stored record uses ``provenance_chips``; live-runner results use ``proof_chips``).
    The chip ``detail`` field is intentionally NOT projected — it can carry method
    language; the customer reads detail in the real EP, not via the model.
    """
    rows = _first_list(packet, "proof_chips", "provenance_chips")
    chips: list[dict[str, Any]] = []
    for row in rows:
        chip = _as_mapping(row)
        chip_id = _clean_str(chip.get("id"))
        status = _chip_status(chip.get("status"))
        if chip_id is None and status is None:
            continue
        out: dict[str, Any] = {}
        if chip_id is not None:
            out["id"] = chip_id
        label = _clean_str(chip.get("label")) or _clean_str(chip.get("name"))
        if label is None and chip_id is not None:
            label = _PROOF_CHIP_LABELS.get(chip_id)
        if label is not None:
            out["label"] = label
        if status is not None:
            out["status"] = status
        # Defensive: only ever the allow-listed sub-keys leave this function.
        chips.append({k: v for k, v in out.items() if k in _PROOF_CHIP_KEYS})
    return chips


def _project_blind_spots(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Project blind-spot / inversion findings in customer terms only (SPEC §5).

    Surfaces which axis flagged, the severity band, and the customer's OWN flagged
    prompt + observed behavior. The proprietary probe construction behind the prompt
    (how CAS derived/selected/mutated it, the scoring math, the internal reasoning)
    is NEVER projected — those keys are simply not read.
    """
    rows = _first_list(packet, "blind_spots", "inversion_findings", "inversions")
    findings: list[dict[str, Any]] = []
    for row in rows:
        finding = _as_mapping(row)
        out: dict[str, Any] = {}
        axis = _clean_str(finding.get("axis")) or _clean_str(finding.get("inversion_axis"))
        if axis is not None:
            out["axis"] = axis
        severity = (
            _clean_str(finding.get("severity_band"))
            or _clean_str(finding.get("severity"))
        )
        if severity is not None:
            out["severity_band"] = severity
        flagged_prompt = (
            _clean_str(finding.get("flagged_prompt"))
            or _clean_str(finding.get("prompt"))
            or _clean_str(finding.get("input"))
        )
        if flagged_prompt is not None:
            out["flagged_prompt"] = flagged_prompt
        observed = (
            _clean_str(finding.get("observed_behavior"))
            or _clean_str(finding.get("observed"))
            or _clean_str(finding.get("behavior"))
        )
        if observed is not None:
            out["observed_behavior"] = observed
        note = _clean_str(finding.get("note"))
        if note is not None:
            out["note"] = note
        if out:
            # Defensive: only ever the allow-listed sub-keys leave this function.
            findings.append({k: v for k, v in out.items() if k in _BLIND_SPOT_KEYS})
    return findings


def _project_anchor(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Project WORM-anchor status + retention mode + trace_id (SPEC §4).

    Reads either an already-shaped ``anchor`` object or the static-anchor WORM
    summary fields (``worm_retained`` / ``anchor_status`` / ``anchor_mode``) carried
    on ``hashes.external_anchor``. Maps to the customer-facing anchored / not-anchored
    statement. No internal hash-log plumbing beyond the trace_id is exposed.
    """
    anchor_obj = _as_mapping(packet.get("anchor"))
    out: dict[str, Any] = {}

    explicit_status = _clean_str(anchor_obj.get("status"))
    if explicit_status is not None:
        out["status"] = explicit_status
    retention_mode = _clean_str(anchor_obj.get("retention_mode")) or _clean_str(
        anchor_obj.get("anchor_mode")
    )
    if retention_mode is not None:
        out["retention_mode"] = retention_mode
    anchor_trace = _clean_str(anchor_obj.get("trace_id"))
    if anchor_trace is not None:
        out["trace_id"] = anchor_trace

    if "status" not in out:
        worm = _worm_summary(packet)
        if worm:
            retained = worm.get("worm_retained")
            if isinstance(retained, bool):
                out["status"] = "anchored" if retained else "not-anchored"
            elif _clean_str(worm.get("anchor_status")) is not None:
                # Fall back to the literal anchor status if retention is unknown.
                status = _clean_str(worm.get("anchor_status"))
                out["status"] = "anchored" if status == "anchored" else "not-anchored"
            if "retention_mode" not in out:
                mode = _clean_str(worm.get("anchor_mode"))
                if mode is not None:
                    out["retention_mode"] = mode

    if "trace_id" not in out:
        trace = _trace_id(packet)
        if trace is not None:
            out["trace_id"] = trace

    return {k: v for k, v in out.items() if k in _ANCHOR_KEYS}


def _model_target(packet: Mapping[str, Any]) -> str | None:
    """The customer's own declared model/endpoint label.

    Prefers an explicit ``model_target``; otherwise the declared ``model_id``; only
    then the endpoint URL host. Never a secret, never a credential.
    """
    explicit = _clean_str(packet.get("model_target"))
    if explicit is not None:
        return explicit
    model_id = _clean_str(packet.get("model_id"))
    if model_id is not None:
        return model_id
    return _clean_str(packet.get("endpoint_url"))


def _trace_id(packet: Mapping[str, Any]) -> str | None:
    return _clean_str(packet.get("evidence_packet_trace_id")) or _clean_str(
        packet.get("trace_id")
    )


def _timestamps(packet: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("created_at", "updated_at", "generated_at"):
        value = _clean_str(packet.get(key))
        if value is not None:
            out[key] = value
    return out


def _counts(
    proof_chips: list[dict[str, Any]], blind_spots: list[dict[str, Any]]
) -> dict[str, Any]:
    """Derive customer-facing counts (e.g. "4 of 6 proof chips ready").

    Derived only from the already-projected (already-redacted) structures, so the
    counts can never reintroduce a non-allow-listed field.
    """
    out: dict[str, Any] = {}
    if proof_chips:
        ready = sum(
            1 for chip in proof_chips if chip.get("status") in {"verified", "present"}
        )
        out["proof_chips_total"] = len(proof_chips)
        out["proof_chips_ready"] = ready
    if blind_spots:
        out["blind_spots_total"] = len(blind_spots)
    return out


# ---------------------------------------------------------------------------
# Small, defensive helpers.
# ---------------------------------------------------------------------------
def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Coerce an EP-ish object into a read-only mapping, defensively.

    Supports Pydantic models (``model_dump``), records exposing ``to_dict``, and
    plain mappings. Anything else yields an empty mapping rather than raising —
    the projector degrades to a smaller projection, never a 500.
    """
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump(mode="json")
        except TypeError:
            dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        dumped = to_dict()
        if isinstance(dumped, Mapping):
            return dumped
    return {}


def _worm_summary(packet: Mapping[str, Any]) -> Mapping[str, Any]:
    """Locate the static-anchor WORM summary fields, if the EP carries them.

    Looks at a top-level ``worm_status`` summary or ``hashes.external_anchor``.
    Returns an empty mapping when neither is present.
    """
    worm_status = _as_mapping(packet.get("worm_status"))
    if worm_status:
        return worm_status
    hashes = _as_mapping(packet.get("hashes"))
    external = _as_mapping(hashes.get("external_anchor"))
    return external


def _first_list(packet: Mapping[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = packet.get(key)
        if isinstance(value, list):
            return value
    return []


def _chip_status(value: Any) -> str | None:
    """Return the chip status VERBATIM (never mapped to pass/ok).

    Out-of-vocabulary statuses are preserved as-is so honesty survives a schema
    drift; this function only ever strips whitespace, never rewrites meaning.
    """
    status = _clean_str(value)
    return status


def _clean_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _clean_number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None
