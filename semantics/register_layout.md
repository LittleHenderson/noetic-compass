# Register layout and decoding order (pinned)

Program length L (1..4 supported; the fixture uses L = 3).

| Register | Qubits (L = 3) | Count | Role |
| --- | --- | --- | --- |
| selection | 0..5 | 2L = 6 | slot k uses qubit 2k (opcode MSB) and 2k+1 (opcode LSB) |
| data | 6 (lsb), 7 (msb) | 2 | two-bit value x = lsb + 2*msb |
| check flags | 8, 9, 10, 11 | 4 | one per public input; flag i = 1 iff f(x_i) equals the target |
| decomposition ancillas | none | 0 | multi-controlled gates are single abstract gates in this IR |
| **total** | | **12** | the compiler output; six selection qubits are not the whole machine |

Index convention: qubit i is bit i of the basis-state index (little-endian index bits).

Decoding order `instruction-left-to-right;two-bit-op-msb-first`: read the selection
qubits in order 0..2L-1; opcode_k = 2*bit(2k) + bit(2k+1); the program executes
opcode_0 first. Example: program (1, 2, 3) is the selection bitstring `011011`.
An LSB-first misreading of the same bits would yield (2, 1, 3); tests pin the
documented order.

Predicate circuit (per public input x, then all inputs):
1. prepare data = x (X gates), 2. execute the selected program (opcode-controlled
primitives), 3. flip flag_i iff data equals target_i (multi-controlled X with
polarity from the target bits), 4. uncompute 2 and 1; after all four inputs a
multi-controlled Z over the flags marks success with phase -1; the whole flag
block then runs in reverse so data and flags return to |0>. Selection is
preserved up to that phase.
