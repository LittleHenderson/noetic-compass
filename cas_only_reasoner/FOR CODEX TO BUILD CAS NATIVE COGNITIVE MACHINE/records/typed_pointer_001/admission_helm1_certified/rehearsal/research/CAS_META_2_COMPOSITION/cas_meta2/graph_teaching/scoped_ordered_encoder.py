"""Context-scoped ordered problem binding, pending CUDA verification.

Pure syntax and exact integer binding maps are inspectable without a learner.
Structural order is ignored only within the preceding framing-line scope.
Finite-width projection collisions remain possible; no learning is established.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import math
import re

from cas_meta2.features_v2 import CLS_ID, MAX_SEQUENCE_LENGTH, LosslessPublicTokenizer
from cas_meta2.graph_teaching import ordered_encoder as base

PROFILE_ID = "cas.graph-scoped-ordered-problem-encoder/0.1"
ALGORITHM = "sha256-full-signed-permutation-scoped-line-binding/1"
MAX_DIMENSION = base.MAX_DIMENSION
_IDENTITY_FIELDS = base._IDENTITY_FIELDS | {"scope_binding"}
_SCOPE_BINDING = ("preceding nonempty framing ordinal; initial CLS anchor 0; "
                  "framing anchors equal their ordinal")
_STRUCTURAL_ORDER = "sort(scope_anchor, kind, token_ids); duplicates retained"
_STATIC_IDENTITY = {
    "profile_id": PROFILE_ID, "algorithm": ALGORITHM,
    "frame_scaling": "sum/sqrt(length); unit-L2 per nonzero frame",
    "zero_frame": "reject exactly zero or nonfinite norm",
    "structural_order": _STRUCTURAL_ORDER,
    "framing_order": "relative nonempty line ordinal; separate CLS frame",
    "scope_binding": _SCOPE_BINDING,
    "option_path": "inherited unchanged",
    "legacy_checkpoint_compatible": False,
    "native_flow": "UNAVAILABLE_NO_NATIVE_FLOW_TAP",
}
_require, _digest = base._require, base._digest


def _validate_coordinates(seed, kind, scope_anchor, ordinal, position, d_model):
    base._validate_coordinates(seed, kind, ordinal, position, d_model)
    _require(type(scope_anchor) is int and 0 <= scope_anchor <= 65536
             and (kind != "framing" or scope_anchor == ordinal),
             "SCOPED_ORDERED_SCOPE_ANCHOR_INVALID")


@dataclass(frozen=True)
class TokenFrame:
    kind: str
    ordinal: int
    token_ids: tuple[int, ...]
    scope_anchor: int

    def __post_init__(self):
        _validate_coordinates(0, self.kind, self.scope_anchor, self.ordinal, 0, 2)
        _require(type(self.token_ids) is tuple and 1 <= len(self.token_ids) <= 65536
                 and all(type(token) is int and token >= 0 for token in self.token_ids),
                 "SCOPED_ORDERED_TOKEN_IDS_INVALID")


def compile_frames(public, tokenizer):
    """Keep nonempty framing order and bind each structural line to its scope.

    A scope begins at each nonempty, non-node/rel line, including whitespace-only
    lines. Empty lines are ignored, matching the original ordered framing.
    Structural lines before any framing line use the initial CLS anchor zero.
    The inherited complete-public and linewise caps both apply. Options are
    validated by the inherited tokenizer but use the unchanged option path.
    """
    _require(isinstance(tokenizer, LosslessPublicTokenizer),
             "ORDERED_TOKENIZER_TYPE_INVALID")
    # This validates public fields/finite numeric rows and the full input cap.
    tokenizer.encode_public(public)
    structural, framing = [], [TokenFrame("framing", 0, (CLS_ID,), 0)]
    scope_anchor = 0
    for line in public["problem"].split("\n"):
        if not line:
            continue
        ids = tuple(tokenizer._text_ids(line))
        match = base._STRUCTURAL.match(line.lstrip())
        if match:
            structural.append(TokenFrame(match[1], 0, ids, scope_anchor))
        else:
            scope_anchor = len(framing)
            framing.append(TokenFrame("framing", scope_anchor, ids, scope_anchor))
    _require(structural, "ORDERED_STRUCTURAL_FRAMES_REQUIRED")
    _require(sum(len(frame.token_ids) for frame in structural + framing)
             <= tokenizer.max_length, "ORDERED_FRAMED_INPUT_TOO_LONG")
    structural.sort(key=lambda frame: (frame.scope_anchor, frame.kind, frame.token_ids))
    return tuple(structural + framing)


@lru_cache(maxsize=16384)
def _signed_permutation(seed, kind, scope_anchor, ordinal, position, d_model):
    domain = [ALGORITHM, seed, kind, scope_anchor, ordinal, position, d_model]
    order = tuple(sorted(range(d_model),
                         key=lambda index: (_digest(domain + ["permutation", index]), index)))
    signs = tuple(1 if int(_digest(domain + ["sign", index])[-1], 16) % 2 else -1
                  for index in range(d_model))
    return order, signs


def signed_permutation(*, seed, kind, scope_anchor, ordinal, position, d_model):
    """Scope is inside each token-role hash, not an added scope-only vector.

    Validate before memoization so cached integer coordinates cannot admit bool
    or float aliases. SHA ordering with an index tiebreak gives a bijection.
    """
    _validate_coordinates(seed, kind, scope_anchor, ordinal, position, d_model)
    return _signed_permutation(seed, kind, scope_anchor, ordinal, position, d_model)


def linear_binding_terms(frame, *, d_model, seed):
    """Exact integer map before per-frame scaling and normalization.

    Unequal maps remove a forced symmetry; they do not prove unequal numeric
    outputs for all inherited projections or after nonlinear normalization.
    """
    _require(type(frame) is TokenFrame, "SCOPED_ORDERED_FRAME_INVALID")
    _validate_coordinates(seed, frame.kind, frame.scope_anchor, frame.ordinal, 0, d_model)
    rows = [dict() for _ in range(d_model)]
    for position, token in enumerate(frame.token_ids):
        order, signs = signed_permutation(seed=seed, kind=frame.kind,
                                         scope_anchor=frame.scope_anchor,
                                         ordinal=frame.ordinal, position=position,
                                         d_model=d_model)
        for destination, (source, sign) in enumerate(zip(order, signs)):
            key = (token, source)
            rows[destination][key] = rows[destination].get(key, 0) + sign
    return tuple(tuple((token, source, count) for (token, source), count in sorted(row.items())
                       if count) for row in rows)


def profile_identity(tokenizer, *, d_model, seed, projection_sha256):
    # Reuse the original tokenizer/seed/dimension/projection-digest validation.
    inherited = base.profile_identity(tokenizer, d_model=d_model, seed=seed,
                                      projection_sha256=projection_sha256)
    value = {key: value for key, value in inherited.items() if key != "identity_sha256"}
    value.update(_STATIC_IDENTITY)
    return {**value, "identity_sha256": _digest(value)}


def validate_checkpoint_identity(checkpoint_metadata, expected_profile):
    """Require this complete scoped contract and exact canonical scalar types."""
    _require(type(expected_profile) is dict and set(expected_profile) == _IDENTITY_FIELDS,
             "SCOPED_ORDERED_EXPECTED_PROFILE_INVALID")
    _require(all(type(expected_profile[key]) is type(value)
                 and expected_profile[key] == value for key, value in _STATIC_IDENTITY.items()),
             "SCOPED_ORDERED_EXPECTED_PROFILE_INVALID")
    _validate_coordinates(expected_profile["permutation_seed"], "framing", 0, 0, 0,
                          expected_profile["d_model"])
    _require(type(expected_profile["max_length"]) is int
             and 16 <= expected_profile["max_length"] <= MAX_SEQUENCE_LENGTH,
             "SCOPED_ORDERED_EXPECTED_PROFILE_INVALID")
    _require(all(type(expected_profile[key]) is str
                 and re.fullmatch(r"[0-9a-f]{64}", expected_profile[key]) is not None
                 for key in ("tokenizer_sha256", "projection_sha256", "identity_sha256")),
             "SCOPED_ORDERED_EXPECTED_PROFILE_INVALID")
    body = {key: value for key, value in expected_profile.items() if key != "identity_sha256"}
    _require(expected_profile["identity_sha256"] == _digest(body),
             "SCOPED_ORDERED_EXPECTED_PROFILE_DIGEST_INVALID")
    actual = checkpoint_metadata.get("encoder_identity") if type(checkpoint_metadata) is dict else None
    # Equality alone would equate True/1 or 64.0/64. Check shape, types and value.
    _require(type(actual) is dict and set(actual) == _IDENTITY_FIELDS
             and all(type(actual[key]) is type(expected_profile[key])
                     and actual[key] == expected_profile[key] for key in expected_profile),
             "SCOPED_ORDERED_CHECKPOINT_IDENTITY_MISMATCH")
    return True


def build_scoped_ordered_encoder(torch, inherited_encoder, *, seed=20260916, device):
    """Worker-only factory over frozen inherited CUDA rows; CUDA check pending.

    Caller owns execution authority and supplies torch. Importing this module
    never imports a tensor package, builds projections, or executes a learner.
    """
    device_name = str(device)
    _require(re.fullmatch(r"cuda(?::[0-9]+)?", device_name) is not None,
             "ORDERED_ENCODER_REQUIRES_CUDA")
    _require(torch.cuda.is_available(), "ORDERED_CUDA_UNAVAILABLE")
    requested_device = (torch.device("cuda", torch.cuda.current_device())
                        if device_name == "cuda" else torch.device(device_name))
    _require(type(inherited_encoder) is dict, "ORDERED_INHERITED_ENCODER_INVALID")
    _require("ordered_profile" not in inherited_encoder, "ORDERED_ENCODER_ALREADY_WRAPPED")
    tokenizer = inherited_encoder.get("tokenizer")
    _require(isinstance(tokenizer, LosslessPublicTokenizer), "ORDERED_TOKENIZER_TYPE_INVALID")
    d_model = inherited_encoder.get("d_model")
    _validate_coordinates(seed, "framing", 0, 0, 0, d_model)
    _require(inherited_encoder.get("projection_frozen") is True
             and callable(inherited_encoder.get("embed"))
             and callable(inherited_encoder.get("encode")), "ORDERED_FROZEN_ENCODER_REQUIRED")
    rows = []
    for index in range(len(tokenizer.vocabulary)):
        row = inherited_encoder["embed"](index)
        _require(row.device.type == "cuda" and row.device == requested_device,
                 "ORDERED_PROJECTION_DEVICE_MISMATCH")
        _require(tuple(row.shape) == (d_model,) and not row.requires_grad,
                 "ORDERED_PROJECTION_ROW_INVALID")
        rows.append(row)
    projection = torch.stack(rows)
    _require(projection.is_floating_point() and bool(torch.isfinite(projection).all().item()),
             "ORDERED_PROJECTION_NONFINITE")
    raw = projection.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()
    projection_digest = _digest({"dtype": str(projection.dtype),
                                 "shape": list(projection.shape),
                                 "bytes_sha256": sha256(raw).hexdigest()})
    identity = profile_identity(tokenizer, d_model=d_model, seed=seed,
                                projection_sha256=projection_digest)
    cache = {}

    def encode_problem(public):
        frames = compile_frames(public, tokenizer)
        vectors = []
        for frame in frames:
            transformed = []
            for position, token in enumerate(frame.token_ids):
                key = (frame.kind, frame.scope_anchor, frame.ordinal, position)
                if key not in cache:
                    order, signs = signed_permutation(seed=seed, kind=frame.kind,
                                                      scope_anchor=frame.scope_anchor,
                                                      ordinal=frame.ordinal,
                                                      position=position, d_model=d_model)
                    cache[key] = (
                        torch.tensor(order, dtype=torch.long, device=projection.device),
                        torch.tensor(signs, dtype=projection.dtype, device=projection.device),
                    )
                order_tensor, sign_tensor = cache[key]
                transformed.append(projection[token].index_select(0, order_tensor) * sign_tensor)
            vector = torch.stack(transformed).sum(dim=0) / math.sqrt(len(transformed))
            norm = torch.linalg.vector_norm(vector)
            _require(bool(torch.isfinite(norm).item()) and bool((norm > 0).item()),
                     "ORDERED_FRAME_NORM_INVALID")
            vectors.append(vector / norm)
        result = torch.stack(vectors).sum(dim=0)
        _require(bool(torch.isfinite(result).all().item()), "ORDERED_RESULT_NONFINITE")
        return result

    return {**inherited_encoder, "encode_problem": encode_problem, "ordered_profile": identity}
