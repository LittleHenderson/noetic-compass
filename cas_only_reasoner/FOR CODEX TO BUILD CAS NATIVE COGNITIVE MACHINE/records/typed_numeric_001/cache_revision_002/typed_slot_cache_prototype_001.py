"""Uninstalled prototype: exact public-byte/profile LRU around held compiler.

1024 entries and 256 MiB serialized retention by default. The latter bounds
accounted packet/profile/plan bytes, NOT Python heap RSS. No teacher imports.
"""
from collections import OrderedDict
from copy import deepcopy
from hashlib import sha256
import json
from threading import RLock


class SlotCache:
    def __init__(self, compiler, current_profile, source, *, max_entries=1024,
                 max_serialized_bytes=256 * 1024 ** 2):
        if type(max_entries) is not int or not 1 <= max_entries <= 1024:
            raise ValueError("CACHE_ENTRY_BOUND")
        if type(max_serialized_bytes) is not int or not 1 <= max_serialized_bytes <= 256 * 1024 ** 2:
            raise ValueError("CACHE_SERIALIZED_BYTE_BOUND")
        self.compiler, self.current_profile, self.source = compiler, current_profile, source
        self.max_entries, self.max_bytes = max_entries, max_serialized_bytes
        self.entries, self.serialized_bytes = OrderedDict(), 0
        self.hits = self.misses = self.compiles = self.evictions = self.bypasses = 0
        self.lock = RLock()

    def __call__(self, packet):
        # Mandatory before cache lookup: tuples/custom types must not share a
        # JSON key with valid lists, and depth/cycle/size limits still apply.
        self.source._bounded(packet)
        raw = self.source.canonical(packet).encode()
        profile_raw = self.source.canonical(self.current_profile()).encode()
        key = (sha256(raw).digest(), sha256(profile_raw).digest())
        with self.lock:
            if key in self.entries:
                saved_raw, saved_profile, plan, _ = self.entries[key]
                if saved_raw != raw or saved_profile != profile_raw:
                    raise ValueError("CACHE_FULL_BYTES_COLLISION")
                self.hits += 1
                self.entries.move_to_end(key)
                return deepcopy(plan)
            self.misses += 1
            self.compiles += 1
        # JSON snapshot isolates compilation from later caller mutation. Errors
        # are never cached; no field is pruned and record_id alone is never used.
        plan = self.compiler(json.loads(raw))
        if (self.source.canonical(plan["profile"]).encode() != profile_raw or
                self.source.canonical(self.current_profile()).encode() != profile_raw or
                plan["packet_digest"] != sha256(raw).hexdigest()):
            raise ValueError("CACHE_COMPILATION_CONTEXT_CHANGED")
        size = len(raw) + len(profile_raw) + len(self.source.canonical(plan).encode())
        with self.lock:
            if size > self.max_bytes:
                self.bypasses += 1
                return deepcopy(plan)
            if key in self.entries:
                self.serialized_bytes -= self.entries.pop(key)[3]
            while self.entries and (len(self.entries) >= self.max_entries or self.serialized_bytes + size > self.max_bytes):
                self.serialized_bytes -= self.entries.popitem(last=False)[1][3]
                self.evictions += 1
            self.entries[key] = (raw, profile_raw, deepcopy(plan), size)
            self.serialized_bytes += size
            return deepcopy(plan)

    def stats(self):
        with self.lock:
            return {"hits": self.hits, "misses": self.misses, "compiles": self.compiles,
                "evictions": self.evictions, "oversize_bypasses": self.bypasses,
                "entries": len(self.entries), "retained_serialized_bytes": self.serialized_bytes,
                "max_entries": self.max_entries, "max_retained_serialized_bytes": self.max_bytes}
