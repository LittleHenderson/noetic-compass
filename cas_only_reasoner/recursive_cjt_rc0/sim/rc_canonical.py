"""rc_canonical.py -- EXACT-TYPE canonical encoding (OWNER DIRECTIVE RC-0.4 section 3).

The owner independently reproduced a digest collision in the RC-0.3 encoder:

    json.dumps(..., default=str)  made  canonical((b"A",)) == canonical(("b'A'",))

so two DIFFERENT authoritative state values received the SAME digest, and frozenset
serialization went through str(...), whose element order varies with PYTHONHASHSEED --
the same logical value could get different bytes in different processes.

`default=str` (or any untyped fallback) is PROHIBITED for state, intent, receipt, or
trace authority. This module is the single canonicalization authority; every value is
transformed into an unambiguous JSON structure BEFORE json.dumps, with no default hook.

Encoding scheme (injective by construction):
  - None / bool / int / float / str  -> raw JSON values (mutually unambiguous in JSON:
    null, true/false, number-without-point, number-with-point, quoted string).
    NaN and infinities are REJECTED (and allow_nan=False backstops the dumps call).
  - list      -> bare JSON array of encoded items (no other form is a bare array).
  - tuple     -> {"$t": "tuple", "items": [...]}
  - bytes     -> {"$t": "bytes", "hex": "<lowercase hex>"}
  - frozenset -> {"$t": "frozenset", "items": [<items' canonical JSON strings, sorted
                 by those encoded bytes>]}  -- deterministic under any PYTHONHASHSEED.
  - enum      -> {"$t": "enum", "cls": "<module>.<qualname>", "member": name,
                 "value": encoded member value} -- class identity is the QUALIFIED
                 name and the member VALUE is bound (internal audit of RC-0.4: the
                 bare-__name__ tag let two same-named classes collide).
  - dict      -> {"$t": "dict", "entries": {key: encoded value}} (str keys only), so a
                 data dict can NEVER collide with one of these tag objects.
  - dataclass instance (registered state record, e.g. RegionRecord/RPMState)
              -> {"$t": "record", "cls": "<module>.<qualname>", "fields": {...}}
  - anything else -> TypeError. No fallback to str or repr, ever.

Every tagged form is a JSON object carrying "$t"; raw dicts are themselves tagged, so
no crafted data value can imitate a tag. Distinct typed values yield distinct bytes.
Deterministic, CPU-only, stdlib-only.
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import math

_JSON_KW = dict(sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def _canon(obj):
    if obj is None:
        return None
    if isinstance(obj, bool):          # bool BEFORE int: isinstance(True, int) is True
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f"canonical() rejects non-finite float {obj!r} "
                             "(NaN/inf cannot enter authoritative state)")
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, bytes):
        return {"$t": "bytes", "hex": obj.hex()}
    if isinstance(obj, enum.Enum):
        cls = type(obj)
        return {"$t": "enum", "cls": f"{cls.__module__}.{cls.__qualname__}",
                "member": obj.name, "value": _canon(obj.value)}
    if isinstance(obj, tuple):
        return {"$t": "tuple", "items": [_canon(x) for x in obj]}
    if isinstance(obj, list):
        return [_canon(x) for x in obj]
    if isinstance(obj, frozenset):
        encoded = sorted(json.dumps(_canon(x), **_JSON_KW) for x in obj)
        return {"$t": "frozenset", "items": encoded}
    if isinstance(obj, dict):
        for k in obj:
            if not isinstance(k, str):
                raise TypeError(f"canonical() dict keys must be str, got {type(k).__name__}")
        return {"$t": "dict", "entries": {k: _canon(v) for k, v in obj.items()}}
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        cls = type(obj)
        return {"$t": "record", "cls": f"{cls.__module__}.{cls.__qualname__}",
                "fields": {f.name: _canon(getattr(obj, f.name))
                           for f in dataclasses.fields(obj)}}
    raise TypeError(f"canonical() cannot encode {type(obj).__name__}: no untyped "
                    "fallback exists (default=str is prohibited for state, intent, "
                    "receipt, or trace authority -- OWNER DIRECTIVE RC-0.4 section 3)")


def canonical(obj) -> str:
    """Exact-type canonical JSON string. Injective over the allowed value domain."""
    return json.dumps(_canon(obj), **_JSON_KW)


def digest(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()
