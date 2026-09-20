"""Lazy CUDA-only frozen typed encoder. Importing this module runs no tensors.

Caller-supplied torch is used only by build/restore. Pure expected identities
describe row bytes, not observed CUDA behavior. The worker must independently
attest loaded sources/wheels, call verify_frozen before/after work, and measure
norms, separation, cache equality and reload behavior. No numeric pass is claimed.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from hashlib import sha256
import math
from pathlib import Path
import re
import sys

from . import binding, slots, tokenization

PROFILE_SCHEMA = "cas.typed-teaching-frozen-encoder-profile/0.1"
IDENTITY_SCHEMA = "cas.typed-teaching-frozen-encoder-identity/0.1"
STATE_SCHEMA = "cas.typed-teaching-frozen-encoder-state/0.1"
MAX_PACKET_CACHE = 1024
MAX_SLOT_CACHE = 8192
MAX_PLAN_CACHE = 1024
MAX_ROLE_ELEMENTS = 8 * 1024 * 1024
_require, _canonical, _digest = binding._require, binding._canonical, binding._digest


def profile():
    raw = Path(__file__).read_bytes()
    body = {"schema": PROFILE_SCHEMA, "binding_profile": binding.profile(),
            "source": {"path": "cas_meta2/typed_teaching/encoder.py", "bytes": len(raw), "sha256": sha256(raw).hexdigest()},
            "dtype": "float32LE", "d_model": 64, "readout_symbols": list(slots.SYMBOLS),
            "bulk_binding": "one token-ID upload per packet; cached row permutation/sign matrices; gather and reduction per row",
            "cache_limits": {"packets": MAX_PACKET_CACHE, "slots": MAX_SLOT_CACHE,
                             "plans": MAX_PLAN_CACHE, "role_elements": MAX_ROLE_ELEMENTS},
            "cache_binding": "encoder identity + exact packet/frame/tokenizer/binding plan; slots additionally bind full plan and slot",
            "cache_guard": "tensor metadata and mutation version per call; full source and actual row byte verification at worker boundaries",
            "loaded_source_and_wheel_attestation": "REQUIRED_FROM_WORKER_NOT_ESTABLISHED_BY_THIS_PROFILE",
            "numeric_acceptance": False}
    return {**body, "profile_digest": _digest(body)}


def _row_receipt(raw, rows):
    return {"dtype": "float32LE", "shape": [rows, 64], "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def expected_identity(tokenizer, *, seed, d_model=64):
    """Pure expected byte identity, with no claim that a device used these rows."""
    binding.validate_config(seed, d_model)
    projection = binding.projection_bytes(tokenizer, seed=seed, d_model=d_model)
    readout = binding.readout_bytes(seed=seed, d_model=d_model)
    body = {"schema": IDENTITY_SCHEMA, "profile": profile(), "tokenizer_digest": tokenizer.digest,
            "seed": seed, "d_model": d_model,
            "projection": _row_receipt(projection, len(tokenizer.vocabulary)),
            "readout": _row_receipt(readout, 90),
            "row_authority": "DETERMINISTIC_EXPECTED_BYTES_ACTUAL_DEVICE_ROWS_REQUIRE_VERIFICATION"}
    return {**body, "identity_digest": _digest(body)}


def validate_identity(tokenizer, identity):
    _require(type(identity) is dict and set(identity) == {"schema", "profile", "tokenizer_digest", "seed",
        "d_model", "projection", "readout", "row_authority", "identity_digest"}, "TYPED_ENCODER_IDENTITY_FIELDS")
    expected = expected_identity(tokenizer, seed=identity["seed"], d_model=identity["d_model"])
    _require(_canonical(identity) == _canonical(expected), "TYPED_ENCODER_IDENTITY_MISMATCH")
    return deepcopy(expected)


def _device(torch, device):
    name = str(device)
    _require(re.fullmatch(r"cuda(?::[0-9]+)?", name) is not None, "TYPED_ENCODER_CUDA_ONLY")
    _require(sys.byteorder == "little", "TYPED_ENCODER_FLOAT32LE_HOST_REQUIRED")
    _require(torch.cuda.is_available(), "TYPED_ENCODER_CUDA_UNAVAILABLE")
    return torch.device("cuda", torch.cuda.current_device()) if name == "cuda" else torch.device(name)


def _tensor_bytes(torch, value):
    return bytes(value.detach().to(device="cpu").contiguous().view(torch.uint8).reshape(-1).tolist())


def _check_tensor(torch, value, receipt, *, device):
    _require(torch.is_tensor(value) and tuple(value.shape) == tuple(receipt["shape"])
             and value.dtype == torch.float32 and value.device == device
             and value.layout == torch.strided and value.is_contiguous() and not value.requires_grad,
             "TYPED_ENCODER_FROZEN_TENSOR_METADATA")
    raw = _tensor_bytes(torch, value)
    _require(len(raw) == receipt["bytes"] and sha256(raw).hexdigest() == receipt["sha256"],
             "TYPED_ENCODER_ACTUAL_ROW_BYTES")


def _make_encoder(torch, tokenizer, identity, projection, readout, device):
    _check_tensor(torch, projection, identity["projection"], device=device)
    _check_tensor(torch, readout, identity["readout"], device=device)
    frozen_identity = deepcopy(identity)
    frozen_tokenizer = tokenization.FrameTokenizer.from_dict(tokenizer.to_dict())
    versions = (projection._version, readout._version)
    packet_cache, slot_cache, plan_cache, role_cache = (OrderedDict() for _ in range(4))
    packet_lookup = {}
    role_elements = 0
    counters = {"packet_cache_hits": 0, "packet_cache_misses": 0, "slot_cache_hits": 0,
                "slot_cache_misses": 0, "plan_cache_hits": 0, "plan_cache_misses": 0,
                "role_cache_hits": 0, "role_cache_misses": 0, "packet_encodes": 0, "slot_encodes": 0,
                "token_rows_bound": 0, "row_reductions": 0, "cuda_bulk_uploads": 2,
                "role_elements_uploaded": 0, "full_frozen_verifications": 0}
    def fast_guard():
        for tensor, receipt, version in ((projection, frozen_identity["projection"], versions[0]),
                                          (readout, frozen_identity["readout"], versions[1])):
            _require(tensor._version == version and tuple(tensor.shape) == tuple(receipt["shape"])
                     and tensor.dtype == torch.float32 and tensor.device == device
                     and tensor.is_contiguous() and not tensor.requires_grad,
                     "TYPED_ENCODER_FROZEN_ROWS_CHANGED")
    def normalize(value):
        norm = torch.linalg.vector_norm(value)
        _require(bool(torch.isfinite(norm).item()) and bool((norm > 0).item()), "TYPED_ENCODER_ZERO_OR_NONFINITE_NORM")
        return value / norm
    def remember(cache, key, value, maximum):
        cache[key] = value; cache.move_to_end(key)
        while len(cache) > maximum:
            removed, _ = cache.popitem(last=False)
            if cache is packet_cache:
                for pd in [pd for pd, cache_key in packet_lookup.items() if cache_key == removed]:
                    del packet_lookup[pd]
    def roles(row, use_cache):
        nonlocal role_elements
        key = (frozen_identity["identity_digest"], tuple(row["scope"]), row["ordinal"], row["count"])
        if use_cache and key in role_cache:
            counters["role_cache_hits"] += 1; role_cache.move_to_end(key)
            return role_cache[key]
        counters["role_cache_misses"] += 1
        count = row["count"] * 64
        _require(count <= MAX_ROLE_ELEMENTS, "TYPED_ENCODER_ROLE_ALLOCATION_BOUND")
        maps = [binding.signed_permutation(seed=identity["seed"], scope=row["scope"], ordinal=row["ordinal"],
                                           position=at, d_model=64) for at in range(row["count"])]
        order = torch.tensor([m[0] for m in maps], dtype=torch.long, device=device)
        signs = torch.tensor([m[1] for m in maps], dtype=torch.float32, device=device)
        counters["cuda_bulk_uploads"] += 2; counters["role_elements_uploaded"] += count
        if use_cache:
            while role_cache and role_elements + count > MAX_ROLE_ELEMENTS:
                old, _ = role_cache.popitem(last=False); role_elements -= old[-1] * 64
            role_cache[key] = (order, signs); role_elements += count
        return order, signs
    def packet_entry(packet, use_cache):
        fast_guard()
        pd = _digest(packet)
        key = packet_lookup.get(pd)
        if use_cache and key in packet_cache:
            counters["packet_cache_hits"] += 1; packet_cache.move_to_end(key)
            return packet_cache[key]
        counters["packet_cache_misses"] += 1
        plan = binding.compile_packet(packet, frozen_tokenizer, seed=identity["seed"])
        _require(_canonical(plan["profile"]) == _canonical(identity["profile"]["binding_profile"]),
                 "TYPED_ENCODER_BINDING_PROFILE_CHANGED")
        ids = [token for row in plan["rows"] for token in row["token_ids"]]
        token_ids = torch.tensor(ids, dtype=torch.long, device=device)
        counters["cuda_bulk_uploads"] += 1
        vectors = []
        with torch.no_grad():
            for row in plan["rows"]:
                order, signs = roles(row, use_cache)
                selected = projection.index_select(0, token_ids[row["start"]:row["start"] + row["count"]])
                value = selected.gather(1, order).mul(signs).sum(dim=0) / math.sqrt(row["count"])
                vectors.append(normalize(value))
            result = normalize(torch.stack(vectors).sum(dim=0) / math.sqrt(len(vectors))).detach()
        counters["packet_encodes"] += 1; counters["token_rows_bound"] += len(ids)
        counters["row_reductions"] += len(vectors)
        cache_body = {"encoder_identity": identity["identity_digest"], "packet_digest": pd,
                      "frame_digest": plan["frame_digest"], "tokenizer_digest": plan["tokenizer_digest"],
                      "binding_plan_digest": plan["plan_digest"]}
        key = _digest(cache_body)
        entry = {"key": key, "identity": cache_body, "vector": result}
        if use_cache:
            remember(packet_cache, key, entry, MAX_PACKET_CACHE); packet_lookup[pd] = key
        return entry
    class FrozenTypedEncoder:
        @property
        def identity(self):
            return deepcopy(frozen_identity)
        @property
        def readout_rows(self):
            fast_guard()
            return readout
        @property
        def symbol_to_index(self):
            return {symbol: i for i, symbol in enumerate(slots.SYMBOLS)}
        def encode_packet(self, packet, *, use_cache=True):
            _require(type(use_cache) is bool, "TYPED_ENCODER_CACHE_FLAG")
            return packet_entry(packet, use_cache)["vector"].clone()
        def encode_slot(self, packet, slotplan, slot, *, use_cache=True):
            _require(type(use_cache) is bool, "TYPED_ENCODER_CACHE_FLAG")
            entry = packet_entry(packet, use_cache)
            pk = (entry["key"], _digest(slotplan))
            if use_cache and pk in plan_cache:
                counters["plan_cache_hits"] += 1; plan_cache.move_to_end(pk)
                validated = plan_cache[pk]
            else:
                counters["plan_cache_misses"] += 1
                validated = slots.validate_plan(packet, slotplan)
                if use_cache: remember(plan_cache, pk, validated, MAX_PLAN_CACHE)
            _require(type(slot) is dict and any(_canonical(slot) == _canonical(v) for v in validated["slots"]),
                     "TYPED_ENCODER_SLOT_MEMBERSHIP")
            spec = binding._query_spec(validated, slot)
            raw = binding.row_bytes(["query", spec], seed=identity["seed"])
            key = _digest({"packet_encoding": entry["identity"], "slot_plan_digest": validated["plan_digest"],
                           "slot": slot, "query_spec": spec, "query_bytes_sha256": sha256(raw).hexdigest()})
            if use_cache and key in slot_cache:
                counters["slot_cache_hits"] += 1; slot_cache.move_to_end(key)
                return slot_cache[key].clone()
            counters["slot_cache_misses"] += 1
            with torch.no_grad():
                query = torch.frombuffer(bytearray(raw), dtype=torch.float32).clone().to(device=device)
                result = normalize((entry["vector"] + query) / math.sqrt(2.0)).detach()
            counters["cuda_bulk_uploads"] += 1; counters["slot_encodes"] += 1
            if use_cache: remember(slot_cache, key, result, MAX_SLOT_CACHE)
            return result.clone()
        def verify_frozen(self):
            fast_guard()
            _require(_canonical(profile()) == _canonical(frozen_identity["profile"]), "TYPED_ENCODER_SOURCE_PROFILE_CHANGED")
            _require(frozen_tokenizer.digest == frozen_identity["tokenizer_digest"], "TYPED_ENCODER_TOKENIZER_CHANGED")
            _check_tensor(torch, projection, frozen_identity["projection"], device=device)
            _check_tensor(torch, readout, frozen_identity["readout"], device=device)
            counters["full_frozen_verifications"] += 1
            return self.identity
        def work_counters(self):
            return {**counters, "packet_cache_entries": len(packet_cache), "slot_cache_entries": len(slot_cache),
                    "plan_cache_entries": len(plan_cache), "role_cache_entries": len(role_cache),
                    "role_cache_elements": role_elements}
        def export_state(self):
            self.verify_frozen()
            return {"schema": STATE_SCHEMA, "identity": self.identity, "tokenizer": frozen_tokenizer.to_dict(),
                    "projection": projection.detach().to(device="cpu").clone(),
                    "readout": readout.detach().to(device="cpu").clone()}
    return FrozenTypedEncoder()


def build_frozen_typed_encoder(torch, tokenizer, *, seed, d_model=64, device):
    """Worker-only fresh construction; no checkpoint or inherited projection."""
    binding.validate_config(seed, d_model)
    identity = expected_identity(tokenizer, seed=seed, d_model=d_model)
    target = _device(torch, device)
    def tensor(raw, shape):
        return torch.frombuffer(bytearray(raw), dtype=torch.float32).reshape(shape).clone().to(device=target)
    projection = tensor(binding.projection_bytes(tokenizer, seed=seed), identity["projection"]["shape"])
    readout = tensor(binding.readout_bytes(seed=seed), identity["readout"]["shape"])
    return _make_encoder(torch, tokenizer, identity, projection, readout, target)


def restore_frozen_typed_encoder(torch, payload, *, expected_identity, device):
    """Restore actual saved rows against a caller-pinned identity, not seed-only.

    The caller's checkpoint loader must use its safe weights-only CPU path and
    verify external file hashes before supplying this already loaded payload.
    """
    _require(type(payload) is dict and set(payload) == {"schema", "identity", "tokenizer", "projection", "readout"}
             and payload["schema"] == STATE_SCHEMA, "TYPED_ENCODER_STATE_FIELDS")
    tokenizer = tokenization.FrameTokenizer.from_dict(payload["tokenizer"])
    wanted = validate_identity(tokenizer, expected_identity)
    _require(_canonical(payload["identity"]) == _canonical(wanted), "TYPED_ENCODER_STATE_IDENTITY")
    target = _device(torch, device)
    cpu = torch.device("cpu")
    for key in ("projection", "readout"):
        _check_tensor(torch, payload[key], wanted[key], device=cpu)
    return _make_encoder(torch, tokenizer, wanted, payload["projection"].detach().clone().to(device=target),
                         payload["readout"].detach().clone().to(device=target), target)
