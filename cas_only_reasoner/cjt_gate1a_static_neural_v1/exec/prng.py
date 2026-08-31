"""prng.py -- the FROZEN hash/counter deterministic random stream.

Replaces every use of Python's random.Random in claim-bearing generation (owner
audit 2026-08-31, section 8): random.Random's helper methods (sample/shuffle/
choice) have changed implementation across CPython versions, so byte-identical
regeneration across a 3.14 laptop and a 3.11 container was an unresolved risk.

This stream is pure SHA-256 counter mode over integers and bytes:
    block(k) = SHA256( domain_utf8 || b"|" || decimal(k) )
consumed left to right, k = 0, 1, 2, ...  Every derived draw (randbelow via
REJECTION sampling on the minimal bit width, Fisher-Yates shuffle, pop-based
sample) is defined here in ~60 lines of version-independent integer arithmetic.
Identical output on every CPython >= 3.8, any OS, any architecture.

Draws are UNBIASED (rejection sampling, never modulo). Deterministic: no
wall-clock, no OS entropy, no process state.
"""
from __future__ import annotations

import hashlib


class HashPRNG:
    """Deterministic byte stream keyed by a domain string."""

    def __init__(self, domain: str):
        self._domain = domain.encode("utf-8")
        self._counter = 0
        self._buf = b""
        self._pos = 0

    def _next_block(self) -> bytes:
        block = hashlib.sha256(
            self._domain + b"|" + str(self._counter).encode("ascii")).digest()
        self._counter += 1
        return block

    def take_bytes(self, n: int) -> bytes:
        out = bytearray()
        while len(out) < n:
            if self._pos >= len(self._buf):
                self._buf = self._next_block()
                self._pos = 0
            need = n - len(out)
            out += self._buf[self._pos:self._pos + need]
            self._pos += min(need, len(self._buf) - self._pos)
        return bytes(out)

    def bits(self, k: int) -> int:
        """A k-bit unsigned integer (big-endian) from the stream."""
        nbytes = (k + 7) // 8
        v = int.from_bytes(self.take_bytes(nbytes), "big")
        return v >> (nbytes * 8 - k)

    def randbelow(self, n: int) -> int:
        """Uniform integer in [0, n) by rejection sampling -- no modulo bias."""
        if n <= 0:
            raise ValueError("randbelow needs n >= 1")
        k = (n - 1).bit_length() or 1
        while True:
            v = self.bits(k)
            if v < n:
                return v

    def randint(self, a: int, b: int) -> int:
        """Uniform integer in [a, b] inclusive (random.Random.randint signature)."""
        return a + self.randbelow(b - a + 1)

    def choice(self, seq):
        return seq[self.randbelow(len(seq))]

    def shuffle(self, x: list) -> None:
        """In-place Fisher-Yates, high index down (frozen order of operations)."""
        for i in range(len(x) - 1, 0, -1):
            j = self.randbelow(i + 1)
            x[i], x[j] = x[j], x[i]

    def sample(self, seq, k: int) -> list:
        """k items without replacement via pop-based selection (frozen order)."""
        pool = list(seq)
        if k > len(pool):
            raise ValueError("sample larger than population")
        return [pool.pop(self.randbelow(len(pool))) for _ in range(k)]

    def random(self) -> float:
        """Uniform float in [0, 1) with 53 bits (for non-claim-bearing fixtures)."""
        return self.bits(53) / (1 << 53)
