"""Hash-bound adapter from PCBA finite transitions to the exact TKS v8 kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
import inspect
from pathlib import Path
from types import MappingProxyType
from typing import Hashable, Mapping

from .boundary import (
    ResearchBoundary,
    fixed_research_boundary,
    require_research_boundary,
)
from .drc import validate_board
from .finite_values import (
    TaggedFiniteValue,
    finite_value_key,
    finite_value_payload,
)
from .integrity import canonical_json, require_safe_reference, require_sha256, sha256_payload
from .model import (
    Board,
    ComponentInstance,
    FiniteTransitionSemantics,
    board_sha256,
    canonical_board_payload,
    canonical_component_payload,
    component_sha256,
)


TKS_KERNEL_PROFILE = "tks-v8.finite-category.kernel.v1"
TKS_KERNEL_SHA256 = "7EDCB89F0C464BEAADAC219AD6793915B1E6168839BF05F2056182B7F52D071E"
ADAPTER_PROFILE = "cas-pcba-v8.tks-adapter-certificate.v3"


class TksAdapterError(ValueError):
    """Raised when PCBA data or the ambient TKS kernel is not exact."""


def _kernel_source_sha256(root: Path) -> str:
    hasher = hashlib.sha256()
    for name in ("__init__.py", "category.py"):
        path = root / name
        if not path.is_file():
            raise TksAdapterError(f"TKS kernel source {name!r} is missing")
        hasher.update(name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest().upper()


def _load_exact_kernel() -> tuple[type, type, dict[str, object]]:
    expected_root = Path(__file__).resolve().parents[1] / "tks_v8_core"
    expected_init = (expected_root / "__init__.py").resolve()
    expected_category = (expected_root / "category.py").resolve()
    actual_sha = _kernel_source_sha256(expected_root)
    if actual_sha != TKS_KERNEL_SHA256:
        raise TksAdapterError("installed TKS kernel source digest is not approved")
    try:
        module = importlib.import_module("tks_v8_core")
    except ImportError as exc:
        raise TksAdapterError("typed TKS v8 kernel is unavailable") from exc
    module_file = getattr(module, "__file__", None)
    if not module_file or Path(module_file).resolve() != expected_init:
        raise TksAdapterError("ambient tks_v8_core module provenance is untrusted")
    finite_object = getattr(module, "FiniteObject", None)
    finite_arrow = getattr(module, "FiniteArrow", None)
    if not isinstance(finite_object, type) or not isinstance(finite_arrow, type):
        raise TksAdapterError("ambient TKS kernel lacks exact finite types")
    try:
        object_source = Path(inspect.getsourcefile(finite_object) or "").resolve()
        arrow_source = Path(inspect.getsourcefile(finite_arrow) or "").resolve()
    except (OSError, TypeError, ValueError) as exc:
        raise TksAdapterError("ambient TKS types have no trusted source") from exc
    if object_source != expected_category or arrow_source != expected_category:
        raise TksAdapterError("ambient TKS finite types were substituted")
    identity = {
        "profile": TKS_KERNEL_PROFILE,
        "sha256": actual_sha,
        "package_source": "tks_v8_core/__init__.py",
        "category_source": "tks_v8_core/category.py",
    }
    return finite_object, finite_arrow, identity


def _certificate_payload(
    *,
    board: Board,
    component: ComponentInstance,
    kernel_identity: Mapping[str, object],
    pcba_certificate_sha256: str,
    board_sha256_value: str,
    component_sha256_value: str,
    transition_sha256: str,
    semantic_profile: str,
    component_ref: str,
    source_name: str,
    target_name: str,
    source_values: tuple[Hashable, ...],
    target_values: tuple[Hashable, ...],
    mapping: tuple[int, ...],
    boundary: ResearchBoundary,
) -> dict[str, object]:
    return {
        "profile": ADAPTER_PROFILE,
        "board": canonical_board_payload(board),
        "component": canonical_component_payload(component),
        "kernel_identity": dict(kernel_identity),
        "pcba_certificate_sha256": pcba_certificate_sha256,
        "board_sha256": board_sha256_value,
        "component_sha256": component_sha256_value,
        "transition_sha256": transition_sha256,
        "semantic_profile": semantic_profile,
        "component_ref": component_ref,
        "source_name": source_name,
        "target_name": target_name,
        "source_values": [finite_value_payload(item) for item in source_values],
        "target_values": [finite_value_payload(item) for item in target_values],
        "mapping": list(mapping),
        "boundary": boundary.to_dict(),
    }


@dataclass(frozen=True, slots=True)
class TksAdapterCertificate:
    """Immutable evidence of one exact, typed, finite adapter operation."""

    board: Board
    component: ComponentInstance
    arrow: object
    kernel_identity: Mapping[str, object]
    pcba_certificate_sha256: str
    board_sha256: str
    component_sha256: str
    transition_sha256: str
    semantic_profile: str
    component_ref: str
    source_name: str
    target_name: str
    source_values: tuple[Hashable, ...]
    target_values: tuple[Hashable, ...]
    mapping: tuple[int, ...]
    adapter_sha256: str
    boundary: ResearchBoundary = field(default_factory=fixed_research_boundary)

    def __post_init__(self) -> None:
        if type(self) is not TksAdapterCertificate:
            raise TksAdapterError("adapter certificate subclasses are not accepted")
        copied_kernel = dict(self.kernel_identity)
        if any(
            type(key) is not str or type(value) is not str
            for key, value in copied_kernel.items()
        ):
            raise TksAdapterError("adapter kernel identity must contain exact strings")
        object.__setattr__(
            self,
            "kernel_identity",
            MappingProxyType(copied_kernel),
        )
        object.__setattr__(self, "source_values", tuple(self.source_values))
        object.__setattr__(self, "target_values", tuple(self.target_values))
        object.__setattr__(self, "mapping", tuple(self.mapping))
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not TksAdapterCertificate:
            raise TksAdapterError("adapter certificates must use the exact type")
        require_research_boundary(self.boundary)
        if type(self.board) is not Board or type(self.component) is not ComponentInstance:
            raise TksAdapterError("adapter must embed exact PCBA board/component values")
        self.board.revalidate()
        self.component.revalidate()
        if (
            board_sha256(self.board) != self.board_sha256
            or component_sha256(self.component) != self.component_sha256
        ):
            raise TksAdapterError("adapter PCBA identity linkage is stale or tampered")
        matches = [
            item for item in self.board.components if item.ref == self.component.ref
        ]
        if (
            len(matches) != 1
            or component_sha256(matches[0]) != component_sha256(self.component)
        ):
            raise TksAdapterError("adapter component is not exact on its embedded board")
        report = validate_board(self.board)
        if not report.is_clean:
            raise TksAdapterError("adapter embedded board is no longer DRC-clean")
        finite_object, finite_arrow, current_kernel = _load_exact_kernel()
        kernel_payload = dict(self.kernel_identity)
        if (
            set(kernel_payload) != set(current_kernel)
            or any(
                type(key) is not str or type(value) is not str
                for key, value in kernel_payload.items()
            )
            or canonical_json(kernel_payload) != canonical_json(current_kernel)
        ):
            raise TksAdapterError("adapter kernel identity is stale or tampered")
        if type(self.arrow) is not finite_arrow:
            raise TksAdapterError("adapter arrow is not from the exact TKS kernel")
        if (
            type(self.arrow.source) is not finite_object
            or type(self.arrow.target) is not finite_object
        ):
            raise TksAdapterError("adapter arrow carriers are not exact TKS objects")
        for field_name in (
            "pcba_certificate_sha256",
            "board_sha256",
            "component_sha256",
            "transition_sha256",
            "adapter_sha256",
        ):
            require_sha256(getattr(self, field_name), field_name)
        for field_name in (
            "semantic_profile",
            "component_ref",
            "source_name",
            "target_name",
        ):
            require_safe_reference(getattr(self, field_name), field_name)
        if type(self.source_values) is not tuple or type(self.target_values) is not tuple:
            raise TksAdapterError("adapter carriers must use exact tuples")
        for item in self.source_values + self.target_values:
            finite_value_payload(item)
        if type(self.mapping) is not tuple or any(type(item) is not int for item in self.mapping):
            raise TksAdapterError("adapter mapping must contain exact integers")
        reconstructed = FiniteTransitionSemantics.certify(
            profile=self.semantic_profile,
            source_name=self.source_name,
            source_elements=self.source_values,
            target_name=self.target_name,
            target_elements=self.target_values,
            mapping=self.mapping,
        )
        if (
            reconstructed.certificate_sha256 != self.transition_sha256
            or self.pcba_certificate_sha256 != self.transition_sha256
        ):
            raise TksAdapterError("adapter transition identity is stale or tampered")
        semantics = self.component.finite_transition
        if (
            self.component.kind != "finite_transition"
            or self.component.semantic_profile != self.semantic_profile
            or self.component.ref != self.component_ref
            or self.component.parameters
            or self.component.state_bindings
            or type(semantics) is not FiniteTransitionSemantics
            or semantics.computed_sha256() != self.transition_sha256
            or semantics.certificate_sha256 != self.pcba_certificate_sha256
            or semantics.source_name != self.source_name
            or semantics.target_name != self.target_name
            or tuple(finite_value_key(item) for item in semantics.source_elements)
            != tuple(finite_value_key(item) for item in self.source_values)
            or tuple(finite_value_key(item) for item in semantics.target_elements)
            != tuple(finite_value_key(item) for item in self.target_values)
            or semantics.mapping != self.mapping
            or not semantics.total
            or not semantics.deterministic
            or semantics.stateful
            or semantics.stochastic
        ):
            raise TksAdapterError("adapter component semantics linkage is inconsistent")
        expected_source_tokens = tuple(
            TaggedFiniteValue.from_value(item) for item in self.source_values
        )
        expected_target_tokens = tuple(
            TaggedFiniteValue.from_value(item) for item in self.target_values
        )
        if (
            type(self.arrow.name) is not str
            or self.arrow.name != self.component_ref
            or type(self.arrow.source.name) is not str
            or self.arrow.source.name != self.source_name
            or type(self.arrow.target.name) is not str
            or self.arrow.target.name != self.target_name
        ):
            raise TksAdapterError("adapter arrow or carrier names were substituted")
        actual_source_tokens = _token_primitives(self.arrow.source.elements)
        actual_target_tokens = _token_primitives(self.arrow.target.elements)
        if actual_source_tokens != _token_primitives(expected_source_tokens):
            raise TksAdapterError("adapter source carrier identity was substituted")
        if actual_target_tokens != _token_primitives(expected_target_tokens):
            raise TksAdapterError("adapter target carrier identity was substituted")
        if (
            type(self.arrow.mapping) is not tuple
            or any(type(item) is not int for item in self.arrow.mapping)
            or tuple(self.arrow.mapping) != tuple(self.mapping)
        ):
            raise TksAdapterError("adapter arrow mapping was substituted")
        payload = _certificate_payload(
            board=self.board,
            component=self.component,
            kernel_identity=self.kernel_identity,
            pcba_certificate_sha256=self.pcba_certificate_sha256,
            board_sha256_value=self.board_sha256,
            component_sha256_value=self.component_sha256,
            transition_sha256=self.transition_sha256,
            semantic_profile=self.semantic_profile,
            component_ref=self.component_ref,
            source_name=self.source_name,
            target_name=self.target_name,
            source_values=self.source_values,
            target_values=self.target_values,
            mapping=self.mapping,
            boundary=self.boundary,
        )
        if self.adapter_sha256 != sha256_payload(payload):
            raise TksAdapterError("adapter certificate identity is stale or tampered")

    def __call__(self, value: Hashable) -> Hashable:
        self.revalidate()
        key = finite_value_key(value)
        keys = tuple(finite_value_key(item) for item in self.source_values)
        try:
            index = keys.index(key)
        except ValueError as exc:
            raise TksAdapterError("value is outside the tagged source carrier") from exc
        token = TaggedFiniteValue.from_value(self.source_values[index])
        output_token = self.arrow(token)
        if type(output_token) is not TaggedFiniteValue:
            raise TksAdapterError("kernel returned an untyped target token")
        actual_keys = _token_primitives(self.arrow.target.elements)
        try:
            output_index = actual_keys.index(
                (output_token.type_tag, output_token.canonical_value)
            )
        except ValueError as exc:
            raise TksAdapterError("kernel returned an unknown tagged target") from exc
        return self.target_values[output_index]


def _token_primitives(values: object) -> tuple[tuple[str, str], ...]:
    if type(values) is not tuple:
        raise TksAdapterError("TKS carrier elements must use an exact tuple")
    result: list[tuple[str, str]] = []
    for item in values:
        if type(item) is not TaggedFiniteValue:
            raise TksAdapterError("TKS carrier contains a substituted token")
        item.revalidate()
        result.append((item.type_tag, item.canonical_value))
    return tuple(result)


def adapt_certified_finite_transition(
    board: Board,
    component: ComponentInstance,
) -> TksAdapterCertificate:
    """Bind one clean board component to the exact local TKS finite kernel."""

    require_research_boundary(fixed_research_boundary())
    if type(board) is not Board or type(component) is not ComponentInstance:
        raise TypeError("finite transition adapter requires Board and ComponentInstance")
    board.revalidate()
    component.revalidate()
    report = validate_board(board)
    if not report.is_clean:
        raise TksAdapterError("finite adapter requires a DRC-clean board")
    matches = [item for item in board.components if item.ref == component.ref]
    if len(matches) != 1 or component_sha256(matches[0]) != component_sha256(component):
        raise TksAdapterError("component is not the exact unique board component")
    if component.kind != "finite_transition":
        raise TksAdapterError("only finite_transition components enter the adapter")
    if component.semantic_profile != "pcba8.finite-transition.v0":
        raise TksAdapterError("finite transition semantic profile is unresolved")
    if component.parameters or component.state_bindings:
        raise TksAdapterError("finite adapter component metadata is undeclared")
    semantics = component.finite_transition
    if semantics is None or semantics.profile != component.semantic_profile:
        raise TksAdapterError("finite transition certificate profile is unresolved")
    if (
        not semantics.total
        or not semantics.deterministic
        or semantics.stateful
        or semantics.stochastic
    ):
        raise TksAdapterError(
            "adapter requires a total deterministic stateless non-stochastic table"
        )
    try:
        transition_sha = semantics.computed_sha256()
    except (TypeError, ValueError) as exc:
        raise TksAdapterError(f"finite payload is not canonical: {exc}") from exc
    if semantics.certificate_sha256 != transition_sha:
        raise TksAdapterError("finite transition certificate digest is stale")

    finite_object, finite_arrow, kernel_identity = _load_exact_kernel()
    source_tokens = tuple(
        TaggedFiniteValue.from_value(item) for item in semantics.source_elements
    )
    target_tokens = tuple(
        TaggedFiniteValue.from_value(item) for item in semantics.target_elements
    )
    try:
        source = finite_object(semantics.source_name, source_tokens)
        target = finite_object(semantics.target_name, target_tokens)
        arrow = finite_arrow(component.ref, source, target, semantics.mapping)
    except (TypeError, ValueError) as exc:
        raise TksAdapterError(f"TKS finite-function validation failed: {exc}") from exc

    fixed_boundary = fixed_research_boundary()
    board_digest = board_sha256(board)
    component_digest = component_sha256(component)
    payload = _certificate_payload(
        board=board,
        component=component,
        kernel_identity=kernel_identity,
        pcba_certificate_sha256=semantics.certificate_sha256,
        board_sha256_value=board_digest,
        component_sha256_value=component_digest,
        transition_sha256=transition_sha,
        semantic_profile=component.semantic_profile,
        component_ref=component.ref,
        source_name=semantics.source_name,
        target_name=semantics.target_name,
        source_values=semantics.source_elements,
        target_values=semantics.target_elements,
        mapping=semantics.mapping,
        boundary=fixed_boundary,
    )
    return TksAdapterCertificate(
        board=board,
        component=component,
        arrow=arrow,
        kernel_identity=kernel_identity,
        pcba_certificate_sha256=semantics.certificate_sha256,
        board_sha256=board_digest,
        component_sha256=component_digest,
        transition_sha256=transition_sha,
        semantic_profile=component.semantic_profile,
        component_ref=component.ref,
        source_name=semantics.source_name,
        target_name=semantics.target_name,
        source_values=semantics.source_elements,
        target_values=semantics.target_elements,
        mapping=semantics.mapping,
        adapter_sha256=sha256_payload(payload),
        boundary=fixed_boundary,
    )
