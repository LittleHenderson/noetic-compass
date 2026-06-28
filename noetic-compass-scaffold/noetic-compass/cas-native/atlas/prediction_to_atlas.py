"""Map a CAS-Native prediction dict to an IdeaAtlas.

The prediction dict is the 12-key shape emitted by
``cas_native.inference.predict_cas.Predictor.__call__``. See the docstring
on :func:`prediction_to_atlas` for the canonical shape.

Walk-down semantics (single-state predictions, the v77 baseline)
----------------------------------------------------------------

Given a prediction with a single argmax noetic ``^N``, optional domain
``^D``, optional drive ``F_k``, and zero-or-more registers ``|R``:

1. **Primary positive-space node.** Always emit the compound state node
   (or bare-Noetic node if domain/drive are absent).
2. **Involution shadow.** If ``^N`` is in an involution pair (``^2↔^3``,
   ``^5↔^6``, ``^8↔^9``), emit a *negative-space* node for the pair
   partner at low intensity, with an ``involution_pair`` edge connecting
   the two. The user's vision: surface the absent Idea.
3. **Domain descent edges.** When the prediction names a single domain
   ``^D``, emit the position of ``^D`` within ``P → C → E → O`` as a
   tooltip on the primary node (no edges to other-domain ghosts; that
   would clutter the atlas). When the model later predicts multi-domain
   states, edges fill in.
4. **Drive inversion shadow.** If the lit drive is in a pair (F1↔F7,
   F2↔F6, F3↔F5), emit the inversion-pair drive as a tooltip on the
   primary node (drive nodes are not separate atlas nodes; drive lives as
   an attribute of the state node).
5. **Register treatment.** Each lit register becomes part of the primary
   node's ``register`` field (single register) or — if the prediction's
   ``register_mode`` is ``"co_presence"`` / ``"set_spec"`` /
   ``"integration"`` — a separate node per register, joined by edges of
   kind ``register_co_presence`` or ``register_integration``. This
   honours CAS v7.7 Clarification 10's notational discipline.
6. **Compound expression unpacking.** When ``has_omega`` or
   ``has_meta_logic`` is true, additional Ω/recipe/cluster nodes and
   edges are emitted (``recipe_prerequisite``, ``production_target``,
   ``cluster_member``). The v0 implementation stubs these branches —
   real recipe parsing piggybacks on the compiler diagram in a follow-on
   pass; see ``trace_mapping.merge_with_diagram``.

Why this is one-directional (prediction → atlas, not atlas → prediction):
the prediction is the source of truth (the model said this); the atlas is
a *view* of the prediction. The reverse direction is the diagram's job
(compile a CAS expression → typed graph).
"""

from __future__ import annotations

from typing import Any, Mapping

from .idea_atlas import (
    DOMAIN_DESCENT_ORDER,
    DRIVE_INVERSION_PAIRS,
    INVOLUTION_PAIRS,
    NOETIC_LABELS,
    SELF_DUAL_NOETICS,
    IdeaAtlas,
    IdeaEdge,
    IdeaNode,
)


# Default intensities for derived nodes. Tuned by visual feedback during
# scaffold review — these are conservative (low ghost intensity to keep
# them visually distinct from positive-space).
_PRIMARY_NODE_INTENSITY: float = 1.0
_INVOLUTION_SHADOW_INTENSITY: float = 0.18
_REGISTER_NODE_INTENSITY: float = 0.7
_OMEGA_NODE_INTENSITY: float = 0.85


# ---------------------------------------------------------------------------
# Helpers — id construction and label rendering
# ---------------------------------------------------------------------------


def _state_node_id(
    noetic: str,
    domain: str | None,
    drive: str | None,
    register: str | None,
    *,
    suffix: str | None = None,
) -> str:
    """Construct a stable id for a state node.

    Format mirrors the rendered CAS expression closely so that humans
    inspecting JSON can pattern-match nodes by id.
    """
    parts = [noetic]
    if domain is not None:
        parts.append(f"^{domain}")
    if drive is not None:
        parts.append(f"_{{{drive}}}")
    if register is not None:
        parts.append(f"|{register}")
    if suffix:
        parts.append(f":{suffix}")
    return "".join(parts)


def _state_node_label(
    noetic: str,
    domain: str | None,
    drive: str | None,
    register: str | None,
) -> str:
    """Human-readable label for a state node.

    The label is what the dashboard shows in tooltips and panel headers.
    It uses the authoritative Noetic name (CLAUDE.md verbatim) plus the
    domain / drive / register annotations.
    """
    n_index = int(noetic[1])
    pieces: list[str] = [f"{noetic} {NOETIC_LABELS[n_index]}"]
    if domain is not None:
        pieces.append(f"^{domain}")
    if drive is not None:
        pieces.append(f"_{{{drive}}}")
    if register is not None:
        pieces.append(f"|{register}")
    return " ".join(pieces)


def _drive_inversion_partner(drive: str | None) -> str | None:
    if drive is None:
        return None
    for a, b in DRIVE_INVERSION_PAIRS:
        if drive == a:
            return b
        if drive == b:
            return a
    return None  # F4 is self-dual


def _involution_partner(noetic: str) -> str | None:
    n = int(noetic[1])
    if n in SELF_DUAL_NOETICS:
        return None
    for a, b in INVOLUTION_PAIRS:
        if n == a:
            return f"^{b}"
        if n == b:
            return f"^{a}"
    return None


def _domain_descent_position(domain: str | None) -> int | None:
    if domain is None:
        return None
    try:
        return DOMAIN_DESCENT_ORDER.index(domain)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Prediction extraction helpers
# ---------------------------------------------------------------------------


def _normalize_prediction(prediction: Mapping[str, Any]) -> dict[str, Any]:
    """Return a normalized copy with sane defaults for missing fields.

    The v77 prediction shape carries 12 keys; older / partial shapes carry
    fewer. We accept any shape that names at least the noetic; everything
    else falls back to a documented default.
    """
    if not isinstance(prediction, Mapping):
        raise TypeError(
            f"prediction must be a mapping, got {type(prediction).__name__}"
        )
    if "noetic" not in prediction:
        raise ValueError("prediction must include 'noetic' (int 0..9)")

    noetic = int(prediction["noetic"])
    if not 0 <= noetic <= 9:
        raise ValueError(f"noetic must be in 0..9, got {noetic}")

    return {
        "turn_type": prediction.get("turn_type", "ANSWER"),
        "expression_family": prediction.get("expression_family", "state"),
        "transition_kind": prediction.get("transition_kind", "state"),
        "noetic": noetic,
        "domain": prediction.get("domain"),
        "drive": prediction.get("drive"),
        "register_mode": prediction.get("register_mode", "none"),
        "registers": tuple(prediction.get("registers") or ()),
        "authority": prediction.get("authority", "none"),
        "has_omega": bool(prediction.get("has_omega", False)),
        "has_meta_logic": bool(prediction.get("has_meta_logic", False)),
        "meta_relations": tuple(prediction.get("meta_relations") or ()),
    }


def _render_cas_expression(pred: Mapping[str, Any]) -> str:
    """Render a canonical CAS expression string from a normalized prediction.

    Note: this is a *display* string only — the canonical compiler-side
    rendering lives in ``cas_native.inference.cas_renderer``. We intentionally
    don't import that here to keep this module pure-stdlib (the renderer
    pulls in torch via its sibling modules).
    """
    noetic = f"^{pred['noetic']}"
    domain = pred.get("domain")
    drive = pred.get("drive")
    registers = pred.get("registers") or ()
    register_mode = pred.get("register_mode", "none")

    parts = [noetic]
    if domain:
        parts.append(f"^{domain}")
    if drive:
        parts.append(f"_{{{drive}}}")

    if registers:
        if register_mode == "set_spec" and len(registers) > 1:
            parts.append(f"|⟨{','.join(registers)}⟩")
        elif register_mode == "co_presence" and len(registers) > 1:
            base = "".join(parts)
            return " + ".join(f"{base}|{r}" for r in registers)
        elif register_mode == "integration" and len(registers) > 1:
            base = "".join(parts)
            return (
                "("
                + " × ".join(f"{base}|{r}" for r in registers)
                + ") = Ω"
            )
        else:
            parts.append(f"|{registers[0]}")

    return "".join(parts)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def prediction_to_atlas(
    prediction: Mapping[str, Any],
    generation_id: str,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> IdeaAtlas:
    """Derive an :class:`IdeaAtlas` from a CAS-Native prediction.

    Parameters
    ----------
    prediction
        12-key dict from
        ``cas_native.inference.predict_cas.Predictor.__call__``. Required
        keys: ``noetic`` (int 0..9). Optional keys: ``domain`` (str |
        None), ``drive`` (str | None), ``registers`` (list[str]),
        ``register_mode`` (str), ``has_omega`` (bool),
        ``has_meta_logic`` (bool), ``authority`` (str), ``turn_type``
        (str), ``expression_family`` (str), ``transition_kind`` (str),
        ``meta_relations`` (list[str]).
    generation_id
        UUID4 hex (or any non-empty string) identifying the prediction.
        The atlas, the diagram, and the prediction all share this id.
    metadata
        Optional free-form metadata (timestamp_ms, checkpoint_id, etc.).

    Returns
    -------
    IdeaAtlas
        Frozen atlas. Caller may serialize via ``.to_json()`` and ship it
        to the dashboard.

    Raises
    ------
    TypeError
        If ``prediction`` is not a mapping.
    ValueError
        If ``noetic`` is missing or out of range.
    """
    pred = _normalize_prediction(prediction)
    nodes: list[IdeaNode] = []
    edges: list[IdeaEdge] = []

    noetic = f"^{pred['noetic']}"
    domain = pred["domain"]
    drive = pred["drive"]
    registers: tuple[str, ...] = pred["registers"]
    register_mode = pred["register_mode"]
    cas_expression = _render_cas_expression(pred)

    # ---- Step 1: Primary positive-space node(s) -----------------------

    # Single-register and "none" modes collapse to one primary node carrying
    # the (single) register. Multi-register modes split into N nodes.
    if register_mode in ("co_presence", "set_spec", "integration") and len(registers) > 1:
        per_register_nodes: list[IdeaNode] = []
        for reg in registers:
            node_id = _state_node_id(noetic, domain, drive, reg)
            per_register_nodes.append(
                IdeaNode(
                    id=node_id,
                    label=_state_node_label(noetic, domain, drive, reg),
                    noetic=noetic,
                    domain=domain,
                    drive=drive,
                    register=reg,
                    intensity=_PRIMARY_NODE_INTENSITY,
                    is_positive_space=True,
                    metadata={
                        "register_mode": register_mode,
                        "domain_descent_position": _domain_descent_position(domain),
                        "noetic_name": NOETIC_LABELS[pred["noetic"]],
                        "expression_family": pred["expression_family"],
                        "turn_type": pred["turn_type"],
                        "authority": pred["authority"],
                    },
                )
            )
        nodes.extend(per_register_nodes)

        # Wire registers together according to mode.
        edge_kind = (
            "register_co_presence"
            if register_mode in ("co_presence", "set_spec")
            else "register_integration"
        )
        for i in range(len(per_register_nodes) - 1):
            edges.append(
                IdeaEdge(
                    source_id=per_register_nodes[i].id,
                    target_id=per_register_nodes[i + 1].id,
                    edge_kind=edge_kind,
                    label="+" if edge_kind == "register_co_presence" else "×",
                    metadata={"register_mode": register_mode},
                )
            )

        primary_node_ids = tuple(n.id for n in per_register_nodes)
    else:
        # Single primary node.
        register: str | None
        register = registers[0] if registers else None

        primary_id = _state_node_id(noetic, domain, drive, register)
        primary_node = IdeaNode(
            id=primary_id,
            label=_state_node_label(noetic, domain, drive, register),
            noetic=noetic,
            domain=domain,
            drive=drive,
            register=register,
            intensity=_PRIMARY_NODE_INTENSITY,
            is_positive_space=True,
            metadata={
                "register_mode": register_mode,
                "domain_descent_position": _domain_descent_position(domain),
                "noetic_name": NOETIC_LABELS[pred["noetic"]],
                "expression_family": pred["expression_family"],
                "turn_type": pred["turn_type"],
                "authority": pred["authority"],
                "drive_inversion_partner": _drive_inversion_partner(drive),
            },
        )
        nodes.append(primary_node)
        primary_node_ids = (primary_id,)

    # ---- Step 2: Involution shadow ------------------------------------

    partner = _involution_partner(noetic)
    if partner is not None:
        # Mirror the primary node(s) but in negative space, low intensity.
        shadow_register = registers[0] if registers else None
        shadow_id = _state_node_id(
            partner, domain, drive, shadow_register, suffix="negspace"
        )
        partner_index = int(partner[1])
        shadow_node = IdeaNode(
            id=shadow_id,
            label=(
                f"(absent) {partner} {NOETIC_LABELS[partner_index]}"
                + (f" ^{domain}" if domain else "")
                + (f" _{{{drive}}}" if drive else "")
                + (f" |{shadow_register}" if shadow_register else "")
            ),
            noetic=partner,
            domain=domain,
            drive=drive,
            register=shadow_register,
            intensity=_INVOLUTION_SHADOW_INTENSITY,
            is_positive_space=False,
            metadata={
                "shadow_of": primary_node_ids[0],
                "noetic_name": NOETIC_LABELS[partner_index],
                "involution_kind": "noetic",
            },
        )
        nodes.append(shadow_node)
        edges.append(
            IdeaEdge(
                source_id=primary_node_ids[0],
                target_id=shadow_id,
                edge_kind="involution_pair",
                label=f"{noetic}↔{partner}",
                metadata={"involution_kind": "noetic"},
            )
        )

    # ---- Step 3: Ω / recipe stub --------------------------------------

    if pred["has_omega"]:
        omega_id = "Ω"
        omega_node = IdeaNode(
            id=omega_id,
            label="Ω (production target)",
            noetic="^0",  # Ω is an Idea-level emergent; ^0 is the canonical
                          # carrier per CLAUDE.md "All things in and outside
                          # the Mind".
            domain=None,
            drive=None,
            register=None,
            intensity=_OMEGA_NODE_INTENSITY,
            is_positive_space=True,
            metadata={
                "kind": "omega",
                "has_meta_logic": pred["has_meta_logic"],
            },
        )
        nodes.append(omega_node)
        for src in primary_node_ids:
            edges.append(
                IdeaEdge(
                    source_id=src,
                    target_id=omega_id,
                    edge_kind="production_target",
                    label="→Ω",
                    metadata={"kind": "omega_bind"},
                )
            )

    # ---- Step 4: Meta-logic stub --------------------------------------

    # When the prediction asserts has_meta_logic, the typed-cluster /
    # set-membership structure lives in the compiler diagram. The atlas
    # links to the primary node with a placeholder cluster_member edge to
    # indicate that the diagram view will surface richer structure. The
    # actual cluster nodes are populated by `trace_mapping.merge_with_diagram`.
    if pred["has_meta_logic"] and pred["meta_relations"]:
        for rel in pred["meta_relations"]:
            cluster_id = f"cluster:{rel}"
            if not any(n.id == cluster_id for n in nodes):
                nodes.append(
                    IdeaNode(
                        id=cluster_id,
                        label=f"cluster: {rel}",
                        noetic="^0",  # Idea-level container
                        domain=None,
                        drive=None,
                        register=None,
                        intensity=0.5,
                        is_positive_space=True,
                        metadata={
                            "kind": "cluster",
                            "meta_relation": rel,
                            "stub": True,
                        },
                    )
                )
            edges.append(
                IdeaEdge(
                    source_id=primary_node_ids[0],
                    target_id=cluster_id,
                    edge_kind="cluster_member",
                    label=rel,
                    metadata={"meta_relation": rel, "stub": True},
                )
            )

    # ---- Compose ------------------------------------------------------

    atlas_metadata: dict[str, Any] = {
        "prediction": dict(pred),
        "schema_version": "idea_atlas_v0.1",
    }
    if metadata:
        atlas_metadata.update(metadata)

    return IdeaAtlas(
        nodes=tuple(nodes),
        edges=tuple(edges),
        generation_id=generation_id,
        cas_expression=cas_expression,
        metadata=atlas_metadata,
    )


__all__ = ["prediction_to_atlas"]
