import CasCheck.Core
/-!
# Laws of the compiler's core rules, checked by Lean's kernel

Each theorem below is about the rules copied in `Core.lean`. "By decide" means Lean's kernel
evaluated every case (for example all 10 x 10 Noetic pairs); nothing is sampled.

Section A holds laws that come out TRUE. Section B holds FINDINGS: facts that are true of the
code but that a reader of the CAS documents may not expect. A finding is a fact about the code,
not a ruling on what the theory should say.
-/
namespace Cas
set_option maxRecDepth 100000

/-! ## A. Laws that hold -/

/-- `∘` is closed: the result is always one of the ten Noetics. -/
theorem compose_closed (a b : Nat) : compose a b < 10 := Nat.mod_lt _ (by decide)

/-- `∘` is commutative. (So the written ORDER of `^a ∘ ^b` never changes the legacy `composed_operator`.) -/
theorem compose_comm (a b : Nat) : compose a b = compose b a := by
  unfold compose; rw [Nat.add_comm]

/-- `∘` is associative. -/
theorem compose_assoc (a b c : Nat) : compose (compose a b) c = compose a (compose b c) := by
  unfold compose; omega

/-- `^0` is the identity of `∘` (the monoid `(N, ∘, CO-0)` in CLAUDE.md). -/
theorem compose_zero_left : ∀ a, a < 10 → compose 0 a = a := by decide
theorem compose_zero_right : ∀ a, a < 10 → compose a 0 = a := by decide

/-- The involution undoes itself. -/
theorem inv_inv : ∀ a, a < 10 → inv (inv a) = a := by decide

/-- The self-duals are exactly ^0, ^1, ^4, ^7. -/
theorem inv_fixed_points : ∀ a, a < 10 → (inv a = a ↔ (a = 0 ∨ a = 1 ∨ a = 4 ∨ a = 7)) := by decide

/-- `_is_involution_pair` agrees with the map: the pairs are exactly 2↔3, 5↔6, 8↔9. -/
theorem invPair_iff : ∀ a, a < 10 → ∀ b, b < 10 → (isInvPair a b = true ↔ (inv a = b ∧ a ≠ b)) := by
  decide

/-- State indices: every (Domain, Noetic) has one index, and every index 0..39 has one (Domain, Noetic). -/
theorem stateIndex_roundtrip (d o : Nat) (hd : d < 4) (ho : o < 10) :
    domainOf (stateIndex d o) = d ∧ opOf (stateIndex d o) = o ∧ stateIndex d o < 40 := by
  unfold domainOf opOf stateIndex; omega

theorem stateIndex_onto (i : Nat) (hi : i < 40) :
    stateIndex (domainOf i) (opOf i) = i ∧ domainOf i < 4 ∧ opOf i < 10 := by
  unfold domainOf opOf stateIndex; omega

/-- Correction 1 of CLAUDE.md: D0 is the diagonal. `^0` admits a move only from a state to itself. -/
theorem D0_is_diagonal (s t : Nat) : admissible 0 s t = (s == t) := by
  simp [admissible]

/-- Every operator admits staying put. -/
theorem admissible_refl (op s : Nat) : admissible op s s = true := by
  unfold admissible; split <;> simp

/-- `×` keeps Domain descent: when it is defined, the result is never earlier than either side. -/
theorem timesDomain_descends : ∀ l, l < 4 → ∀ r, r < 4 →
    ∀ d, timesDomain l r = some d → l ≤ d ∧ r ≤ d := by
  decide

/-- `(a × b) × c` and `a × (b × c)` on Domains. -/
def timesL (a b c : Nat) : Option Nat := (timesDomain a b).bind (fun x => timesDomain x c)
def timesR (a b c : Nat) : Option Nat := (timesDomain b c).bind (fun x => timesDomain a x)

/-- When both bracketings of a `×` chain are accepted, they give the same Domain. -/
theorem timesDomain_assoc_when_defined : ∀ a, a < 4 → ∀ b, b < 4 → ∀ c, c < 4 →
    (!(timesL a b c).isSome || !(timesR a b c).isSome || timesL a b c == timesR a b c) = true := by
  decide

/-- When `->` compiles at all, the reported `domain_descent_ok` is always true. -/
theorem arrow_descent_flag_always_true (s t : Nat) (h : arrowCompiles s t = true) :
    (arrow s t).2 = true := by
  simpa [arrow, arrowCompiles] using h

/-! ## B. Findings -/

/-- FINDING B1. The `admissible` flag of `->` is empty for 36 of the 40 targets.
`_is_admissible` is called with the target's own Noetic, and its second test
`target % 10 == operator` is then always true. So the flag says only:
"the target is not a `^0` state, or source and target are the same state".
Checked here for all 40 x 40 pairs of states. -/
theorem B1_arrow_admissible_is_vacuous : ∀ s, s < 40 → ∀ t, t < 40 →
    (arrow s t).1 = (opOf t != 0 || s == t) := by
  decide

/-- B1, the same fact for EVERY pair of numbers (a general proof, not a case check). -/
theorem B1_arrow_admissible_is_vacuous_general (s t : Nat) :
    (arrow s t).1 = (opOf t != 0 || s == t) := by
  unfold arrow admissible opOf
  by_cases h : t % 10 = 0 <;> simp [h]

/-- FINDING B2. `∘` and `×` never cancel an involution pair to `^0`:
`^2 ∘ ^3 = ^5`, `^5 ∘ ^6 = ^1`, `^8 ∘ ^9 = ^7`. -/
theorem B2_compose_of_pairs : compose 2 3 = 5 ∧ compose 5 6 = 1 ∧ compose 8 9 = 7 := by decide

theorem B2_compose_never_cancels_a_pair : ∀ a, a < 10 → isInvPair a (inv a) = true →
    compose a (inv a) ≠ 0 := by
  decide

/-- B2, continued. `÷` DOES cancel every involution pair to `^0`. So `×` and `÷` disagree on
exactly the pairs the theory calls duals. -/
theorem B2_divide_cancels_pairs : ∀ a, a < 10 → isInvPair a (inv a) = true →
    divide a (inv a) = 0 := by
  decide

/-- B2, continued. Under `∘` the number that undoes `^a` is `^((10 - a) % 10)`, not the dual
partner: `^8 ∘ ^2 = ^0`, `^9 ∘ ^1 = ^0`, `^5 ∘ ^5 = ^0`. -/
theorem B2_compose_inverse : ∀ a, a < 10 → ∀ b, b < 10 → (compose a b = 0 ↔ b = (10 - a) % 10) := by
  decide

/-- FINDING B3. `÷` is commutative: `^a ÷ ^b = ^b ÷ ^a` for every pair. -/
theorem B3_divide_comm : ∀ a, a < 10 → ∀ b, b < 10 → divide a b = divide b a := by decide

/-- FINDING B4. `÷` does not undo `×`, and `^0` is not a right identity of `÷`:
`^a ÷ ^0 = ^a` only for `a = 0`; for example `^4 ÷ ^0 = ^2` and `(^1 × ^0) ÷ ^0 = ^0`. -/
theorem B4_divide_zero_not_identity : ∀ a, a < 10 → (divide a 0 = a ↔ a = 0) := by decide

theorem B4_divide_examples : divide 4 0 = 2 ∧ divide (compose 1 0) 0 = 0 := by decide

/-- FINDING B5. The involution does not respect `∘`, in either order:
`inv (^2 ∘ ^2) = ^4` but `inv ^2 ∘ inv ^2 = ^6`. The rule `inv (a ∘ b) = inv b ∘ inv a`
holds for only 46 of the 100 pairs (`B5_inv_count`). -/
theorem B5_inv_not_hom : inv (compose 2 2) ≠ compose (inv 2) (inv 2) := by decide

theorem B5_inv_count : (List.range 10).foldl (fun n a => (List.range 10).foldl
    (fun n b => if inv (compose a b) == compose (inv b) (inv a) then n + 1 else n) n) 0 = 46 := by
  decide

/-- FINDING B6. `+` is not symmetric in what it hands on. When two states tie, `dominant_state`
keeps the one written FIRST. So `^2^C + ^3^C` is dominated by `^2^C` and `^3^C + ^2^C` by `^3^C`,
and any operator that reads the dominant state (`×`, `÷`, `∘`, `->`, `compose`, `RPM`) gives
different answers for the two spellings. -/
theorem B6_plus_order_matters :
    dominant (plus (lit 12) (lit 13)) = some 12 ∧ dominant (plus (lit 13) (lit 12)) = some 13 := by
  decide

/-- B6, consequence: `(^2^C + ^3^C) × ^5^C` lands on `^7`, `(^3^C + ^2^C) × ^5^C` on `^8`. -/
theorem B6_consequence : compose 2 5 = 7 ∧ compose 3 5 = 8 := by decide

/-- FINDING B7. `-` has no zero: subtracting a state from itself returns the state unchanged. -/
theorem B7_minus_self : ∀ i, i < 40 → minus (lit i) (lit i) = lit i := by decide

/-- FINDING B8 (found by Lean: the associativity law I first wrote down was FALSE).
Whether a `×` chain compiles depends on the brackets. `(^1^E × ^1^C) × ^1^O` is refused
(E then C is an ascent), but `^1^E × (^1^C × ^1^O)` is accepted and lands in O.
The parser groups `×` to the left, so the unbracketed `^1^E × ^1^C × ^1^O` is refused. -/
theorem B8_times_brackets_matter : timesL 2 1 3 = none ∧ timesR 2 1 3 = some 3 := by decide

/-- B8, counted over all 64 Domain triples: the left grouping is accepted for 20, the right
grouping for 30, and they disagree for 10 (every disagreement: right accepts, left refuses). -/
theorem B8_count :
    ((List.range 4).flatMap fun a => (List.range 4).flatMap fun b => (List.range 4).map fun c =>
        ((timesL a b c).isSome, (timesR a b c).isSome)).foldl
      (fun (n : Nat × Nat × Nat) p =>
        (n.1 + (if p.1 then 1 else 0), n.2.1 + (if p.2 then 1 else 0),
         n.2.2 + (if p.1 != p.2 then 1 else 0))) (0, 0, 0) = (20, 30, 10) := by
  decide

theorem B8_direction : ∀ a, a < 4 → ∀ b, b < 4 → ∀ c, c < 4 →
    (timesL a b c).isSome = true → (timesR a b c).isSome = true := by
  decide

end Cas
