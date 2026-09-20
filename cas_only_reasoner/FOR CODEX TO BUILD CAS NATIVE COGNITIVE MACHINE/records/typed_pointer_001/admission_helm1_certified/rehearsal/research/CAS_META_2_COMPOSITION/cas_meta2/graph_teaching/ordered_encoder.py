"""Versioned, fixed ordered problem binding; no learner or answer parser.

Pure framing and signed permutations can be inspected without torch.  The
numeric adapter accepts an existing frozen encoder and requires CUDA before
touching any tensor.  It changes only the problem encoding.  It cannot make a
finite-width projection injective or establish learned competence.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
import math
import re

from cas_meta2.codec import PolicyContractError, validate_public
from cas_meta2.features_v2 import CLS_ID, LosslessPublicTokenizer

PROFILE_ID = "cas.graph-ordered-problem-encoder/0.1"
ALGORITHM = "sha256-full-signed-permutation-line-binding/1"
MAX_DIMENSION = 4096
_STRUCTURAL = re.compile(r"^(node|rel)(?:\s|$)")
_IDENTITY_FIELDS = frozenset({
    "profile_id", "algorithm", "tokenizer_sha256", "projection_sha256", "d_model",
    "permutation_seed", "max_length", "frame_scaling", "zero_frame",
    "structural_order", "framing_order", "option_path", "legacy_checkpoint_compatible",
    "native_flow", "identity_sha256",
})


def _require(condition, reason):
    if not condition:
        raise PolicyContractError(reason)


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TokenFrame:
    kind: str
    ordinal: int
    token_ids: tuple[int, ...]


def compile_frames(public, tokenizer):
    """Frame public syntax only; structural line order is intentionally ignored.

    Newlines delimit frames.  All other characters, including whitespace and
    unseen UTF-8 bytes, use the inherited tokenizer unchanged.  Framing/query
    lines retain their relative order.  No graph operation is evaluated here.
    """
    _require(isinstance(tokenizer, LosslessPublicTokenizer),
             "ORDERED_TOKENIZER_TYPE_INVALID")
    validate_public(public)  # Reject target, record ID, and private fields.
    tokenizer.encode_public(public)  # Enforce the inherited complete-input cap.
    structural, framing = [], [TokenFrame("framing", 0, (CLS_ID,))]
    for line in public["problem"].split("\n"):
        if not line:
            continue
        ids = tuple(tokenizer._text_ids(line))
        _require(ids, "ORDERED_EMPTY_TOKEN_FRAME")
        match = _STRUCTURAL.match(line.lstrip())
        if match:
            structural.append(TokenFrame(match[1], 0, ids))
        else:
            framing.append(TokenFrame("framing", len(framing), ids))
    _require(structural, "ORDERED_STRUCTURAL_FRAMES_REQUIRED")
    # Linewise tokenization can use byte fallback for a whitespace unit whose
    # training spelling included a newline.  Check that bound separately too.
    _require(sum(len(frame.token_ids) for frame in structural + framing)
             <= tokenizer.max_length, "ORDERED_FRAMED_INPUT_TOO_LONG")
    structural.sort(key=lambda frame: (frame.kind, frame.token_ids))
    return tuple(structural + framing)


def _validate_coordinates(seed, kind, ordinal, position, d_model):
    _require(type(seed) is int and 0 <= seed < 2**63, "ORDERED_SEED_INVALID")
    _require(kind in ("node", "rel", "framing"), "ORDERED_FRAME_KIND_INVALID")
    _require(type(ordinal) is int and 0 <= ordinal <= 65536
             and (kind == "framing" or ordinal == 0), "ORDERED_FRAME_ORDINAL_INVALID")
    _require(type(position) is int and 0 <= position < 65536,
             "ORDERED_TOKEN_POSITION_INVALID")
    _require(type(d_model) is int and 2 <= d_model <= MAX_DIMENSION,
             "ORDERED_DIMENSION_INVALID")


@lru_cache(maxsize=16384)
def signed_permutation(*, seed, kind, ordinal, position, d_model):
    """Full coordinate permutation and independent signs for one token role.

    Sorting distinct coordinate IDs by SHA256 (then by ID for hash ties) gives
    a bijection.  No periodic roll or product of small token coordinates is
    used.  The explicit hash domain is part of the versioned profile.
    """
    _validate_coordinates(seed, kind, ordinal, position, d_model)
    base = [ALGORITHM, seed, kind, ordinal, position, d_model]
    order = tuple(sorted(range(d_model),
                         key=lambda index: (_digest(base + ["permutation", index]), index)))
    signs = tuple(1 if int(_digest(base + ["sign", index])[-1], 16) % 2 else -1
                  for index in range(d_model))
    return order, signs


def linear_binding_terms(frame, *, d_model, seed):
    """Exact integer coefficients before line scaling/normalization.

    This pure inspection seam exposes the linear map from inherited token-row
    coordinates. Different terms remove the forced token-multiset symmetry;
    they do not promise different outputs for every possible projection.
    """
    _require(isinstance(frame, TokenFrame) and bool(frame.token_ids),
             "ORDERED_FRAME_INVALID")
    _validate_coordinates(seed, frame.kind, frame.ordinal, 0, d_model)
    rows = [dict() for _ in range(d_model)]
    for position, token in enumerate(frame.token_ids):
        _require(type(token) is int and token >= 0, "ORDERED_TOKEN_ID_INVALID")
        order, signs = signed_permutation(seed=seed, kind=frame.kind,
                                         ordinal=frame.ordinal, position=position,
                                         d_model=d_model)
        for destination, (source, sign) in enumerate(zip(order, signs)):
            key = (token, source)
            rows[destination][key] = rows[destination].get(key, 0) + sign
    return tuple(tuple((token, source, count) for (token, source), count in sorted(row.items())
                       if count) for row in rows)


def profile_identity(tokenizer, *, d_model, seed, projection_sha256):
    _require(isinstance(tokenizer, LosslessPublicTokenizer),
             "ORDERED_TOKENIZER_TYPE_INVALID")
    _validate_coordinates(seed, "framing", 0, 0, d_model)
    _require(type(projection_sha256) is str
             and re.fullmatch(r"[0-9a-f]{64}", projection_sha256) is not None,
             "ORDERED_PROJECTION_DIGEST_INVALID")
    value = {
        "profile_id": PROFILE_ID, "algorithm": ALGORITHM,
        "tokenizer_sha256": tokenizer.digest,
        "projection_sha256": projection_sha256, "d_model": d_model,
        "permutation_seed": seed, "max_length": tokenizer.max_length,
        "frame_scaling": "sum/sqrt(length); unit-L2 per nonzero frame",
        "zero_frame": "reject exactly zero or nonfinite norm",
        "structural_order": "sort(kind, token_ids); duplicates retained",
        "framing_order": "relative nonempty line ordinal; separate CLS frame",
        "option_path": "inherited unchanged",
        "legacy_checkpoint_compatible": False,
        "native_flow": "UNAVAILABLE_NO_NATIVE_FLOW_TAP",
    }
    return {**value, "identity_sha256": _digest(value)}


def validate_checkpoint_identity(checkpoint_metadata, expected_profile):
    """Require an explicit complete identity, including actual projection bytes."""
    _require(type(expected_profile) is dict
             and set(expected_profile) == _IDENTITY_FIELDS
             and expected_profile.get("profile_id") == PROFILE_ID
             and expected_profile.get("algorithm") == ALGORITHM
             and expected_profile.get("legacy_checkpoint_compatible") is False,
             "ORDERED_EXPECTED_PROFILE_INVALID")
    body = {key: value for key, value in expected_profile.items() if key != "identity_sha256"}
    _require(expected_profile.get("identity_sha256") == _digest(body),
             "ORDERED_EXPECTED_PROFILE_DIGEST_INVALID")
    _require(type(checkpoint_metadata) is dict
             and checkpoint_metadata.get("encoder_identity") == expected_profile,
             "ORDERED_CHECKPOINT_IDENTITY_MISMATCH")
    return True


def build_ordered_encoder(torch, inherited_encoder, *, seed=20260916, device):
    """Wrap already-built CUDA embeddings; do not refit or seed a new projection.

    Caller owns GPU execution authority.  Merely importing this module never
    imports torch, constructs tensors, or runs a model.
    """
    device_name = str(device)
    _require(re.fullmatch(r"cuda(?::[0-9]+)?", device_name) is not None,
             "ORDERED_ENCODER_REQUIRES_CUDA")
    _require(torch.cuda.is_available(), "ORDERED_CUDA_UNAVAILABLE")
    requested_device = (torch.device("cuda", torch.cuda.current_device())
                        if device_name == "cuda" else torch.device(device_name))
    _require(type(inherited_encoder) is dict, "ORDERED_INHERITED_ENCODER_INVALID")
    _require("ordered_profile" not in inherited_encoder,
             "ORDERED_ENCODER_ALREADY_WRAPPED")
    tokenizer = inherited_encoder.get("tokenizer")
    _require(isinstance(tokenizer, LosslessPublicTokenizer),
             "ORDERED_TOKENIZER_TYPE_INVALID")
    d_model = inherited_encoder.get("d_model")
    _validate_coordinates(seed, "framing", 0, 0, d_model)
    _require(inherited_encoder.get("projection_frozen") is True
             and callable(inherited_encoder.get("embed"))
             and callable(inherited_encoder.get("encode")),
             "ORDERED_FROZEN_ENCODER_REQUIRED")
    # Only read inherited rows.  The option encoder retains the same callable.
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
                key = (frame.kind, frame.ordinal, position)
                if key not in cache:
                    order, signs = signed_permutation(seed=seed, kind=frame.kind,
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

    return {**inherited_encoder, "encode_problem": encode_problem,
            "ordered_profile": identity}
