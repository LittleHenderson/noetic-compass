"""Probe-adapter architecture compatibility gate for frontier-scale runs.

This is frontier run-gate (6) of the experimental 300B-4T lane. Gate (5)
established *which* weights will be audited (identity + license + hash). This
gate answers the next, equally hard question: *can the CAS Harness probe worker
mechanically hook this architecture at all?* If it cannot, auditing it would
produce a fabricated result, so we refuse the run.

Honesty is anchored to what the worker code can actually do -- not to an
aspirational list. The probe worker
(``live-trace-worker/scripts/run_open_weight_probe_shard.py``) locates a model's
decoder layer stack with exactly four hardcoded attribute paths::

    ("gpt_neox", "layers")    # GPT-NeoX / Pythia
    ("model", "layers")       # Llama, Mistral, Qwen2/3, Gemma, OLMo, DeepSeek, ...
    ("transformer", "h")      # GPT-2 / GPT-J / GPT-Neo / BLOOM / Falcon
    ("transformer", "blocks") # MPT

and raises ``RuntimeError`` for anything else; it then hooks each layer's
``.mlp`` submodule (falling back to the whole layer when there is no ``.mlp``).
This registry mirrors those four paths exactly. An architecture whose ``model_type``
does not resolve to one of them is **refused**, because the worker would raise
rather than capture activations.

Honesty contract (mirrors the provenance gate's declared-vs-verified split):

* We never claim an architecture is *verified* hookable until the worker has
  actually loaded the model, located the layer stack, and confirmed the
  ``model_type`` -- that is ``ARCHITECTURE_ADAPTER_VERIFIED`` and only the probe
  worker can produce it.
* A *declared* architecture whose ``model_type`` resolves to a supported layer
  stack is ``ARCHITECTURE_ADAPTER_AVAILABLE`` -- enough to *create* a frontier
  run, never enough on its own to reach a customer ACCEPT (the real model layout
  is confirmed worker-side at load time).
* A ``model_type`` (or inferred architecture class) that resolves to none of the
  four supported stacks is ``ARCHITECTURE_ADAPTER_UNSUPPORTED`` and refuses the run.

Scope (deliberately narrow, so the gate stays honest): this gate checks that the
worker can *locate and hook* the decoder stack. It does NOT certify that the
40-Element readout has been *empirically validated* on that family -- that is the
separate scale-validation ladder (``EMPIRICALLY_VALIDATED`` vs
``ENGINEERED_NOT_VALIDATED`` vs ``EXPERIMENTAL_NOT_VALIDATED``). A frontier run is
``EXPERIMENTAL_NOT_VALIDATED`` by definition; this gate only refuses the runs we
cannot mechanically probe at all. Dimension cross-checks (declared
``num_hidden_layers`` vs the planned layer shards) are recorded for traceability
but are a labelled future enhancement, not yet an enforcement criterion.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

ArchitectureAdapterStatus = Literal[
    "ARCHITECTURE_ADAPTER_VERIFIED",
    "ARCHITECTURE_ADAPTER_AVAILABLE",
    "ARCHITECTURE_ADAPTER_UNSUPPORTED",
]

# The four decoder-stack attribute paths the probe worker actually tries, in
# order. Kept as data so the gate's notices can cite the exact mechanism.
SUPPORTED_LAYER_STACK_PATHS: tuple[tuple[str, ...], ...] = (
    ("gpt_neox", "layers"),
    ("model", "layers"),
    ("transformer", "h"),
    ("transformer", "blocks"),
)


@dataclass(frozen=True)
class ProbeAdapterProfile:
    """One supported architecture family: how the worker hooks it.

    ``layer_stack_path`` is one of the four real paths in
    ``locate_transformer_layers``; ``model_types`` is the set of Hugging Face
    ``config.model_type`` values known to use that path. ``validation`` records
    how far we have actually exercised the adapter -- ``empirically_validated``
    for the family we reproduced end-to-end (GPT-NeoX / Pythia), else
    ``structurally_supported`` (stack is locatable and hookable, but the readout
    is not empirically validated on this family).
    """

    family: str
    layer_stack_path: tuple[str, ...]
    model_types: frozenset[str]
    hook_submodule: str
    validation: Literal["empirically_validated", "structurally_supported"]
    notes: str

    @property
    def layer_stack_attr(self) -> str:
        return ".".join(self.layer_stack_path)

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "layer_stack_attr": self.layer_stack_attr,
            "model_types": sorted(self.model_types),
            "hook_submodule": self.hook_submodule,
            "validation": self.validation,
            "notes": self.notes,
        }


# Registry of architecture families the probe worker can mechanically hook.
# Mirrors locate_transformer_layers' four paths. Extend DELIBERATELY: an unknown
# model_type is refused (honest) rather than waved through and then crashed on
# the worker. Membership here means "the worker can locate + hook this stack",
# NOT "the 40E readout is validated on this family" (that is the scale ladder).
_PROBE_ADAPTER_REGISTRY: tuple[ProbeAdapterProfile, ...] = (
    ProbeAdapterProfile(
        family="gpt_neox",
        layer_stack_path=("gpt_neox", "layers"),
        model_types=frozenset({"gpt_neox", "gptneox"}),
        hook_submodule="mlp",
        validation="empirically_validated",
        notes="Pythia / GPT-NeoX. Reproduced end-to-end on CPU (Pythia-160M).",
    ),
    ProbeAdapterProfile(
        family="llama_like",
        layer_stack_path=("model", "layers"),
        model_types=frozenset(
            {
                "llama",
                "mistral",
                "mixtral",
                "qwen2",
                "qwen3",
                "qwen2_moe",
                "qwen3_moe",
                "gemma",
                "gemma2",
                "gemma3_text",
                "olmo",
                "olmo2",
                "deepseek",
                "deepseek_v2",
                "deepseek_v3",
                "phi",
                "phi3",
                "cohere",
                "command_r",
                "granite",
                "exaone",
                "nemotron",
            }
        ),
        hook_submodule="mlp",
        validation="structurally_supported",
        notes=(
            "Standard `model.layers` decoder stack with a per-layer `.mlp`. Stack is "
            "locatable and hookable; the 40E readout is not empirically validated on "
            "these families (a frontier run is EXPERIMENTAL_NOT_VALIDATED by definition)."
        ),
    ),
    ProbeAdapterProfile(
        family="gpt2_like",
        layer_stack_path=("transformer", "h"),
        model_types=frozenset(
            {"gpt2", "gptj", "gpt_neo", "bloom", "falcon", "rw"}
        ),
        hook_submodule="mlp",
        validation="structurally_supported",
        notes=(
            "Classic `transformer.h` decoder stack (GPT-2 / GPT-J / GPT-Neo / BLOOM / "
            "Falcon). Locatable and hookable; readout not empirically validated here."
        ),
    ),
    ProbeAdapterProfile(
        family="mpt_like",
        layer_stack_path=("transformer", "blocks"),
        model_types=frozenset({"mpt"}),
        hook_submodule="block",
        validation="structurally_supported",
        notes=(
            "MPT `transformer.blocks` stack. MPT blocks expose `.ffn`, not `.mlp`, so the "
            "worker's `getattr(layer, 'mlp', layer)` hook falls back to the whole block -- "
            "it captures block output, not the MLP output. Honest caveat, not a blocker."
        ),
    ),
)

# Common architecture class-name stems (config.architectures[0]) -> model_type,
# used only when model_type is absent. Conservative: unknown stems stay unknown.
_ARCHITECTURE_CLASS_TO_MODEL_TYPE: dict[str, str] = {
    "gptneox": "gpt_neox",
    "llama": "llama",
    "mistral": "mistral",
    "mixtral": "mixtral",
    "qwen2": "qwen2",
    "qwen3": "qwen3",
    "gemma": "gemma",
    "gemma2": "gemma2",
    "gemma3": "gemma3_text",
    "olmo": "olmo",
    "olmo2": "olmo2",
    "phi": "phi",
    "phi3": "phi3",
    "cohere": "cohere",
    "falcon": "falcon",
    "gptj": "gptj",
    "gptneo": "gpt_neo",
    "gpt2": "gpt2",
    "bloom": "bloom",
    "mpt": "mpt",
}

_MODEL_TYPE_ALIASES: dict[str, str] = {
    "gptneox": "gpt_neox",
    "qwen": "qwen2",
    "deepseekv2": "deepseek_v2",
    "deepseekv3": "deepseek_v3",
    "commandr": "command_r",
}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_model_type(model_type: str) -> str:
    """Lower-case, collapse separators to underscores, apply known aliases."""

    normalized = _NON_ALNUM.sub("_", model_type.strip().lower()).strip("_")
    return _MODEL_TYPE_ALIASES.get(normalized, normalized)


def _model_type_from_architecture_class(architecture_class: str) -> str | None:
    """Best-effort map ``LlamaForCausalLM`` -> ``llama`` (only when confident)."""

    stem = architecture_class.strip().lower()
    for suffix in (
        "forcausallm",
        "forconditionalgeneration",
        "lmheadmodel",
        "model",
    ):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    stem = _NON_ALNUM.sub("", stem)
    return _ARCHITECTURE_CLASS_TO_MODEL_TYPE.get(stem)


def find_adapter_for_model_type(model_type: str) -> ProbeAdapterProfile | None:
    normalized = normalize_model_type(model_type)
    for profile in _PROBE_ADAPTER_REGISTRY:
        if normalized in profile.model_types:
            return profile
    return None


def supported_model_types() -> tuple[str, ...]:
    out: set[str] = set()
    for profile in _PROBE_ADAPTER_REGISTRY:
        out.update(profile.model_types)
    return tuple(sorted(out))


def frontier_architecture_requirement_notice() -> str:
    paths = ", ".join(".".join(p) for p in SUPPORTED_LAYER_STACK_PATHS)
    return (
        "A frontier-scale (300B-4T) run requires a model architecture declaration whose "
        "model_type resolves to a probe adapter CAS Harness can mechanically hook. The "
        f"probe worker locates the decoder stack via one of: {paths}; an architecture it "
        "cannot locate would raise rather than produce activations, so it is refused. "
        "Architecture is run-gate (6)."
    )


@dataclass(frozen=True)
class ModelArchitectureDeclaration:
    """Caller-supplied statement of the model's architecture family.

    ``model_type`` is the canonical key (Hugging Face ``config.model_type``).
    ``architectures`` (e.g. ``["LlamaForCausalLM"]``) is an optional fallback /
    cross-check. The dims are recorded for traceability; they are not yet an
    enforcement criterion.
    """

    model_type: str | None = None
    architectures: tuple[str, ...] = ()
    num_hidden_layers: int | None = None
    hidden_size: int | None = None
    num_attention_heads: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "model_type": self.model_type,
            "architectures": list(self.architectures),
            "num_hidden_layers": self.num_hidden_layers,
            "hidden_size": self.hidden_size,
            "num_attention_heads": self.num_attention_heads,
        }


@dataclass(frozen=True)
class ArchitectureAdapterSummary:
    """Honest rollup of the architecture check, mirroring the provenance shape."""

    status: ArchitectureAdapterStatus
    declared_model_type: str | None
    declared_architectures: tuple[str, ...]
    resolved_model_type: str | None
    adapter_family: str | None
    layer_stack_attr: str | None
    hook_submodule: str | None
    adapter_validation: str | None
    adapter_available: bool
    notice: str
    reasons: tuple[str, ...] = ()
    declared_num_hidden_layers: int | None = None
    declared_hidden_size: int | None = None
    declared_num_attention_heads: int | None = None

    @property
    def accepted(self) -> bool:
        """True when the architecture is good enough to *create* a frontier run."""

        return self.status != "ARCHITECTURE_ADAPTER_UNSUPPORTED"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "declared_model_type": self.declared_model_type,
            "declared_architectures": list(self.declared_architectures),
            "resolved_model_type": self.resolved_model_type,
            "adapter_family": self.adapter_family,
            "layer_stack_attr": self.layer_stack_attr,
            "hook_submodule": self.hook_submodule,
            "adapter_validation": self.adapter_validation,
            "adapter_available": self.adapter_available,
            "notice": self.notice,
            "reasons": list(self.reasons),
            "declared_num_hidden_layers": self.declared_num_hidden_layers,
            "declared_hidden_size": self.declared_hidden_size,
            "declared_num_attention_heads": self.declared_num_attention_heads,
        }


def _unsupported(
    reasons: list[str],
    *,
    declared_model_type: str | None,
    declared_architectures: tuple[str, ...],
    resolved_model_type: str | None,
    declaration: ModelArchitectureDeclaration | None = None,
) -> ArchitectureAdapterSummary:
    return ArchitectureAdapterSummary(
        status="ARCHITECTURE_ADAPTER_UNSUPPORTED",
        declared_model_type=declared_model_type,
        declared_architectures=declared_architectures,
        resolved_model_type=resolved_model_type,
        adapter_family=None,
        layer_stack_attr=None,
        hook_submodule=None,
        adapter_validation=None,
        adapter_available=False,
        notice=(
            "Model architecture adapter unsupported: "
            + "; ".join(reasons)
            + ". "
            + frontier_architecture_requirement_notice()
        ),
        reasons=tuple(reasons),
        declared_num_hidden_layers=declaration.num_hidden_layers if declaration else None,
        declared_hidden_size=declaration.hidden_size if declaration else None,
        declared_num_attention_heads=declaration.num_attention_heads if declaration else None,
    )


def summarize_architecture_adapter(
    *,
    declaration: ModelArchitectureDeclaration | None,
) -> ArchitectureAdapterSummary:
    """Check a declared architecture against the probe-adapter registry.

    Returns ``ARCHITECTURE_ADAPTER_AVAILABLE`` when the declared ``model_type``
    (or an inferred architecture class) resolves to a supported decoder stack;
    ``ARCHITECTURE_ADAPTER_UNSUPPORTED`` otherwise. ``ARCHITECTURE_ADAPTER_VERIFIED``
    is reserved for the probe worker, which is the only place the real model is
    loaded and its layer stack actually located.
    """

    if declaration is None:
        return _unsupported(
            ["no model architecture declaration attached"],
            declared_model_type=None,
            declared_architectures=(),
            resolved_model_type=None,
        )

    declared_model_type = (declaration.model_type or "").strip() or None
    declared_architectures = tuple(
        a for a in (s.strip() for s in declaration.architectures) if a
    )

    # Resolve a model_type: prefer the explicit one, else infer from the class names.
    resolved_model_type: str | None = None
    if declared_model_type:
        resolved_model_type = normalize_model_type(declared_model_type)
    else:
        for arch_class in declared_architectures:
            inferred = _model_type_from_architecture_class(arch_class)
            if inferred is not None:
                resolved_model_type = inferred
                break

    if resolved_model_type is None:
        return _unsupported(
            [
                "architecture declaration provides neither a model_type nor a "
                "recognizable architecture class (e.g. 'LlamaForCausalLM')"
            ],
            declared_model_type=declared_model_type,
            declared_architectures=declared_architectures,
            resolved_model_type=None,
            declaration=declaration,
        )

    profile = find_adapter_for_model_type(resolved_model_type)
    if profile is None:
        return _unsupported(
            [
                f"no probe adapter for model_type '{resolved_model_type}' -- the worker can "
                f"only hook decoder stacks at: "
                + ", ".join(".".join(p) for p in SUPPORTED_LAYER_STACK_PATHS)
            ],
            declared_model_type=declared_model_type,
            declared_architectures=declared_architectures,
            resolved_model_type=resolved_model_type,
            declaration=declaration,
        )

    hook_note = (
        f"the probe worker locates the stack via `{profile.layer_stack_attr}` and hooks "
        f"each layer's `{profile.hook_submodule}`"
    )
    notice = (
        f"Probe adapter available for the '{profile.family}' architecture family "
        f"(model_type '{resolved_model_type}'): {hook_note}. The actual model layout has "
        "NOT yet been confirmed by loading the model -- confirmation happens worker-side "
        "when the weights load (that is when the status can become "
        "ARCHITECTURE_ADAPTER_VERIFIED). Adapter validation depth: "
        f"{profile.validation}. {profile.notes}"
    )

    return ArchitectureAdapterSummary(
        status="ARCHITECTURE_ADAPTER_AVAILABLE",
        declared_model_type=declared_model_type,
        declared_architectures=declared_architectures,
        resolved_model_type=resolved_model_type,
        adapter_family=profile.family,
        layer_stack_attr=profile.layer_stack_attr,
        hook_submodule=profile.hook_submodule,
        adapter_validation=profile.validation,
        adapter_available=True,
        notice=notice,
        reasons=(),
        declared_num_hidden_layers=declaration.num_hidden_layers,
        declared_hidden_size=declaration.hidden_size,
        declared_num_attention_heads=declaration.num_attention_heads,
    )


def validate_frontier_architecture(
    *,
    declaration: ModelArchitectureDeclaration | None,
) -> ArchitectureAdapterSummary:
    """Frontier run-gate: raise ``ValueError`` unless the architecture is hookable.

    Acceptable means ARCHITECTURE_ADAPTER_AVAILABLE (or VERIFIED) -- a declared
    architecture whose model_type resolves to a supported decoder stack is enough
    to *create* a frontier run. ARCHITECTURE_ADAPTER_UNSUPPORTED (missing
    declaration / unrecognized model_type / no adapter) refuses it. Callers
    convert this ValueError to HTTP 422.
    """

    summary = summarize_architecture_adapter(declaration=declaration)
    if summary.status == "ARCHITECTURE_ADAPTER_UNSUPPORTED":
        raise ValueError(
            "frontier-scale run refused: unsupported model architecture -- "
            + "; ".join(summary.reasons)
            + ". "
            + frontier_architecture_requirement_notice()
        )
    return summary
