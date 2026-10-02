/-!
# CAS compiler core: a Lean copy of the rules

Every definition below copies one rule of the Python fallback path of the CAS compiler,
`noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`, at commit `8a3555b8`
(git blob `439c4908df2718a3ca1e1ff40bda63020cf71efa`, 6,415 lines). Line numbers refer to that file.

The copy is checked against the real compiler in `Differential.lean`: a Python script runs real
CAS source text through `compile_expression` and Lean compares every answer with these rules.

Encodings (the compiler's own):
* a Noetic `^n` is the number `n`, 0..9;
* a Domain is its precedence rank `DOMAIN_ORDER` (line 67): P = 0, C = 1, E = 2, O = 3;
* a state index is `rank * 10 + noetic` (line 1824), 0..39.
-/
namespace Cas

/-- `_compose_operators` (line 2043), Python fallback: `(left + right) % 10`.
Used by `∘` (CIRC), by `×` (TIMES) on the Noetic, by `compose(...)` and by `fractal(...)`. -/
def compose (a b : Nat) : Nat := (a + b) % 10

/-- `_OPERATOR_INVOLUTION_PAIRS` (line 2049) read as a map. The four self-duals map to themselves. -/
def inv : Nat → Nat
  | 2 => 3
  | 3 => 2
  | 5 => 6
  | 6 => 5
  | 8 => 9
  | 9 => 8
  | n => n

/-- `_is_involution_pair` (line 2052). -/
def isInvPair (a b : Nat) : Bool :=
  (a == 2 && b == 3) || (a == 3 && b == 2) || (a == 5 && b == 6) ||
  (a == 6 && b == 5) || (a == 8 && b == 9) || (a == 9 && b == 8)

/-- `_is_admissible` (line 2056), Python fallback. `s` and `t` are state indices. -/
def admissible (op s t : Nat) : Bool :=
  if op == 0 then s == t else (s / 10 == t / 10) || (t % 10 == op)

/-- `_state_index` (line 1824). -/
def stateIndex (d op : Nat) : Nat := d * 10 + op

/-- `dominant_domain` (line 802): `"PCEO"[idx // 10]`, as a rank. -/
def domainOf (i : Nat) : Nat := i / 10

/-- `dominant_operator` (line 806): `idx % 10`. -/
def opOf (i : Nat) : Nat := i % 10

/-- `÷` (DIVIDE), lines 5233-5243, Python fallback, for two states in the same Domain. -/
def divide (a b : Nat) : Nat :=
  if a == b || isInvPair a b then 0 else ((a + b) / 2) % 10

/-- `÷` across Domains is refused (line 5234). -/
def divideDomain (l r : Nat) : Option Nat :=
  if l == r then some l else none

/-- `×` (TIMES) Domain rule, lines 5225-5232: the result takes the later Domain;
an earlier Domain on the right ("ascent") is refused. -/
def timesDomain (l r : Nat) : Option Nat :=
  if l ≤ r then some r else none

/-- `->` (ARROW), lines 5324-5327: the pair (`admissible`, `domain_descent_ok`) the compiler reports.
The operator handed to `_is_admissible` is the TARGET's own Noetic. -/
def arrow (s t : Nat) : Bool × Bool :=
  (admissible (opOf t) s t, decide (domainOf s ≤ domainOf t))

/-- Type check of `->` (line 3893): an expression whose left Domain comes after its right Domain
does not compile at all. -/
def arrowCompiles (s t : Nat) : Bool :=
  decide (domainOf s ≤ domainOf t)

/-- `<-` (LARROW), lines 5328-5331: the operator handed to `_is_admissible` is the LEFT state's
Noetic, and the move checked is right -> left. -/
def larrow (s t : Nat) : Bool × Bool :=
  (admissible (opOf s) t s, decide (domainOf t ≤ domainOf s))

/-- Type check of `<-` (line 3898): refused when the right Domain comes after the left one. -/
def larrowCompiles (s t : Nat) : Bool :=
  decide (domainOf t ≤ domainOf s)

/-- `<->` (BIARROW), lines 5332-5336: both checks, and the Domains must match. -/
def biarrow (s t : Nat) : Bool × Bool :=
  (admissible (opOf t) s t && admissible (opOf s) t s, domainOf s == domainOf t)

/-- Type check of `<->` (line 3903): refused unless both sides share a Domain. -/
def biarrowCompiles (s t : Nat) : Bool :=
  domainOf s == domainOf t

/-- `×` on two single states (lines 5222-5232 Python, Rust `multiply_states`): the state index of
the result, or `none` when the Domain step would ascend. -/
def timesState (s t : Nat) : Option Nat :=
  (timesDomain (domainOf s) (domainOf t)).map (fun d => stateIndex d (compose (opOf s) (opOf t)))

/-- `÷` on two single states (lines 5233-5243 Python, Rust `divide_states`). -/
def divideState (s t : Nat) : Option Nat :=
  (divideDomain (domainOf s) (domainOf t)).map (fun d => stateIndex d (divide (opOf s) (opOf t)))

/-! ## `+` and `-` on states (lines 5141-5185)

A state is a dictionary from state index to weight. Python dictionaries keep insertion order,
and `max(self.states, key=self.states.get)` (line 799) returns the FIRST key with the largest
weight. Weights are scaled to whole numbers here: `normalized()` divides every weight by the same
positive total, which keeps their order. -/

/-- A state as the compiler stores it: (state index, weight) in insertion order. -/
abbrev Dist := List (Nat × Nat)

/-- `dominant_state` (line 799): the first key with the largest weight. -/
def dominant (d : Dist) : Option Nat :=
  (d.foldl (fun acc kw =>
      match acc with
      | none => some kw
      | some best => if kw.2 > best.2 then some kw else some best) none).map (·.1)

/-- `merged[key] = merged.get(key, 0.0) + value` on a copy of the left dictionary. -/
def addKey (d : Dist) (k w : Nat) : Dist :=
  if d.any (·.1 == k) then d.map (fun kv => if kv.1 == k then (kv.1, kv.2 + w) else kv)
  else d ++ [(k, w)]

/-- `+` (PLUS) on two states, lines 5141-5164. -/
def plus (l r : Dist) : Dist := r.foldl (fun acc kv => addKey acc kv.1 kv.2) l

/-- `-` (MINUS) on two states, lines 5166-5185: subtract weights of shared keys, floor at 0;
if nothing is left, return the LEFT state unchanged. -/
def minus (l r : Dist) : Dist :=
  let rem := l.map (fun kv =>
    match r.find? (·.1 == kv.1) with
    | some kw => (kv.1, kv.2 - kw.2)
    | none => kv)
  if rem.all (·.2 == 0) then l else rem

/-- A single state literal such as `^2^C` is `{index: 1.0}`. -/
def lit (i : Nat) : Dist := [(i, 1)]

end Cas
