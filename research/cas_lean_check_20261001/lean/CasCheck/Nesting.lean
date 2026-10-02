/-!
# The Nesting Operator: canonical form and the Dual Cancellation criterion

Copies `_nesting_reduce` (line 1027) and `_nesting_criterion` (line 996) of `compiler.py` at
commit `8a3555b8`, then proves what they do.

Main results:
* `normal_form_unique_ordered` (general proof, any word length): in the compiler's
  "surfacing member first" reading, cancelling pairs in ANY order and stopping when nothing more
  cancels always ends on the compiler's own canonical form. The canonical form is well defined.
* `either_order_two_normal_forms` (FINDING N-A): in the "either order" reading this fails. The word
  `^2^C|T ∘ ^3^C ∘ ^2^C|f` ends on `^2^C|f` or on `^2^C|T`, depending on which pair is cancelled
  first. The compiler reports one of them (`^2^C|f`) as THE form.
-/
namespace Cas.Nesting

/-- One term of a nested word, as the compiler's `nesting.terms` entries carry it.
`domain`: 0..3 = P C E O, 4 = no Domain written. `drive`: 0 = none, 1..7 = F1..F7.
`label`: a code for everything else that appears in the term's printed label (Register etc.);
the cancelling rule never reads it, the canonical form prints it. -/
structure Term where
  noetic : Nat
  domain : Nat
  drive : Nat
  label : Nat
deriving DecidableEq, Repr, Inhabited

/-- `NESTING_PARTNER` (line 909). -/
def partner : Nat → Option Nat
  | 2 => some 3
  | 3 => some 2
  | 5 => some 6
  | 6 => some 5
  | 8 => some 9
  | 9 => some 8
  | _ => none

/-- Keys of `NESTING_SURFACING_MEMBER` (line 908). -/
def surfacing (n : Nat) : Bool := n == 2 || n == 5 || n == 8

/-- `NESTING_LANDING_SIDE` (line 910). -/
def landing (n : Nat) : Bool := n == 3 || n == 6 || n == 9

/-- `_nesting_same_setting` (line 991): same Domain and same Drive. -/
def sameSetting (a b : Term) : Bool := a.domain == b.domain && a.drive == b.drive

/-- The cancelling test inside `_nesting_reduce` (lines 1032-1035). `eo` is `either_order`. -/
def cancels (eo : Bool) (top t : Term) : Bool :=
  partner top.noetic == some t.noetic && (eo || surfacing top.noetic) && sameSetting top t

/-- One turn of the loop in `_nesting_reduce`. The stack is kept head-first:
the head is `survivors[-1]`. `key` reads the term out of whatever is being carried. -/
def step {α : Type} (key : α → Term) (eo : Bool) : List α → α → List α
  | top :: rest, t => if cancels eo (key top) (key t) then rest else t :: top :: rest
  | [], t => [t]

/-- `live` in `_analyse_nesting` (line 1059): the `^0` terms are dropped first. -/
def live {α : Type} (key : α → Term) (w : List α) : List α :=
  w.filter (fun x => (key x).noetic != 0)

/-- `_nesting_reduce` on the live terms: the surviving terms, in written order. -/
def reduce {α : Type} (key : α → Term) (eo : Bool) (w : List α) : List α :=
  ((live key w).foldl (step key eo) []).reverse

/-- No two neighbours cancel. -/
def noRedex {α : Type} (key : α → Term) (eo : Bool) : List α → Bool
  | a :: b :: rest => !cancels eo (key a) (key b) && noRedex key eo (b :: rest)
  | _ => true

/-- One cancellation anywhere in a live word: `x ++ [a, b] ++ y` becomes `x ++ y`. -/
inductive Step {α : Type} (key : α → Term) (eo : Bool) : List α → List α → Prop
  | cancel (x y : List α) (a b : α) :
      cancels eo (key a) (key b) = true → Step key eo (x ++ [a, b] ++ y) (x ++ y)

/-- Any number of cancellations, in any order. -/
inductive Reach {α : Type} (key : α → Term) (eo : Bool) : List α → List α → Prop
  | refl (w : List α) : Reach key eo w w
  | tail {u v w : List α} : Reach key eo u v → Step key eo v w → Reach key eo u w

/-! ## General proofs (any word length) -/

section Proofs
variable {α : Type} (key : α → Term)

/-- No two neighbours on the stack cancel (head = most recent; `next` was pushed before `top`). -/
def good (eo : Bool) : List α → Bool
  | top :: next :: rest => !cancels eo (key next) (key top) && good eo (next :: rest)
  | _ => true

theorem good_tail (eo : Bool) (top : α) (rest : List α) (h : good key eo (top :: rest) = true) :
    good key eo rest = true := by
  cases rest with
  | nil => rfl
  | cons n r =>
    simp only [good, Bool.and_eq_true] at h
    exact h.2

/-- The loop keeps the stack reduced. -/
theorem step_good (eo : Bool) (st : List α) (t : α) (h : good key eo st = true) :
    good key eo (step key eo st t) = true := by
  cases st with
  | nil => rfl
  | cons top rest =>
    by_cases hc : cancels eo (key top) (key t) = true
    · simp [step, hc]
      exact good_tail key eo top rest h
    · have hf : cancels eo (key top) (key t) = false := by simpa using hc
      simp [step, hf, good, h]

theorem foldl_good (eo : Bool) (l : List α) : ∀ st : List α, good key eo st = true →
    good key eo (l.foldl (step key eo) st) = true := by
  induction l with
  | nil => intro st h; simpa using h
  | cons x xs ih => intro st h; simp only [List.foldl_cons]; exact ih _ (step_good key eo st x h)

/-- A surfacing thought's partner is never itself surfacing. -/
theorem surfacing_partner_landing (n m : Nat) (hs : surfacing n = true) (hp : partner n = some m) :
    surfacing m = false := by
  have h3 : n = 2 ∨ n = 5 ∨ n = 8 := by
    simp [surfacing] at hs
    omega
  rcases h3 with rfl | rfl | rfl <;> simp [partner] at hp <;> subst hp <;> decide

theorem cancels_ordered_spec {x y : Term} (h : cancels false x y = true) :
    partner x.noetic = some y.noetic ∧ surfacing x.noetic = true := by
  simp only [cancels, Bool.false_or, Bool.and_eq_true] at h
  obtain ⟨⟨hp, hs⟩, _⟩ := h
  exact ⟨by simpa using hp, hs⟩

/-- In the surfacing-first reading two cancelling pairs can never overlap: if `x y` cancels,
`y z` cannot. -/
theorem ordered_no_overlap (x y z : Term) (h1 : cancels false x y = true) :
    cancels false y z = false := by
  obtain ⟨hp, hs⟩ := cancels_ordered_spec h1
  have hy := surfacing_partner_landing x.noetic y.noetic hs hp
  simp [cancels, hy]

/-- A cancelling pair pushed onto ANY stack leaves the stack as it was (surfacing-first reading). -/
theorem pair_vanishes_ordered (a b : α) (hab : cancels false (key a) (key b) = true)
    (st : List α) : [a, b].foldl (step key false) st = st := by
  cases st with
  | nil => simp [step, hab]
  | cons top rest =>
    have hta : cancels false (key top) (key a) = false := by
      cases h : cancels false (key top) (key a) with
      | false => rfl
      | true =>
        have hno := ordered_no_overlap (key top) (key a) (key b) h
        rw [hno] at hab
        cases hab
    simp [step, hta, hab]

/-- One cancellation anywhere in the word does not change the compiler's answer. -/
theorem fold_respects_cancel_ordered (x y : List α) (a b : α)
    (hab : cancels false (key a) (key b) = true) :
    (x ++ [a, b] ++ y).foldl (step key false) [] = (x ++ y).foldl (step key false) [] := by
  simp only [List.foldl_append]
  rw [pair_vanishes_ordered key a b hab]

/-- Any sequence of cancellations does not change the compiler's answer. -/
theorem reach_fold_ordered {u v : List α} (h : Reach key false u v) :
    u.foldl (step key false) [] = v.foldl (step key false) [] := by
  induction h with
  | refl => rfl
  | tail _ hs ih =>
    cases hs with
    | cancel x y a b hab => rw [ih, fold_respects_cancel_ordered key x y a b hab]

/-- On a word where no neighbours cancel, the loop only pushes. -/
theorem fold_noRedex (eo : Bool) (w : List α) : ∀ st : List α,
    noRedex key eo w = true →
    (∀ top a, st.head? = some top → w.head? = some a → cancels eo (key top) (key a) = false) →
    w.foldl (step key eo) st = w.reverse ++ st := by
  induction w with
  | nil => intro st _ _; simp
  | cons a rest ih =>
    intro st hn hhead
    have hstep : step key eo st a = a :: st := by
      cases st with
      | nil => rfl
      | cons top r =>
        have hc := hhead top a rfl rfl
        simp [step, hc]
    have hn' : noRedex key eo rest = true := by
      cases rest with
      | nil => rfl
      | cons b r =>
        simp only [noRedex, Bool.and_eq_true] at hn
        exact hn.2
    have hhead' : ∀ top b, (a :: st).head? = some top → rest.head? = some b →
        cancels eo (key top) (key b) = false := by
      intro top b htop hb
      cases rest with
      | nil => simp at hb
      | cons c r =>
        simp only [List.head?_cons, Option.some.injEq] at htop hb
        subst htop
        subst hb
        simp only [noRedex, Bool.and_eq_true, Bool.not_eq_true'] at hn
        exact hn.1
    simp only [List.foldl_cons, hstep]
    rw [ih (a :: st) hn' hhead']
    simp

/-- MAIN RESULT (surfacing-first reading). If any sequence of cancellations takes the live word
`u` to a word `v` where nothing more cancels, then `v` IS the compiler's canonical form of `u`.
So the canonical form does not depend on the order in which pairs are cancelled. -/
theorem normal_form_unique_ordered {u v : List α} (h : Reach key false u v)
    (hv : noRedex key false v = true) :
    (u.foldl (step key false) []).reverse = v := by
  rw [reach_fold_ordered key h,
      fold_noRedex key false v [] hv (by intro top a h1 _; simp at h1)]
  simp

end Proofs

/-! ## Either-order reading WITHOUT labels: the canonical form is unique (general proof)

The patent text and the Rust engine (`cas-engine/src/fractals/simplification.rs`, "Theorem 8.12:
Every fractal has a unique canonical form") cancel a dual pair in either order, on bare digits.
The proofs below show that this IS unique for words of any length, as long as the terms carry no
label the cancelling rule ignores (Register etc.). Finding N-A shows it fails once labels are kept. -/

theorem partner_involutive (n m k : Nat) (h1 : partner n = some m) (h2 : partner m = some k) :
    k = n := by
  unfold partner at h1
  split at h1 <;> simp at h1 <;> subst h1 <;> simp [partner] at h2 <;> omega

theorem cancels_either_spec {x y : Term} (h : cancels true x y = true) :
    partner x.noetic = some y.noetic ∧ x.domain = y.domain ∧ x.drive = y.drive := by
  simp only [cancels, Bool.true_or, Bool.and_true, Bool.and_eq_true, sameSetting] at h
  obtain ⟨hp, hd, hr⟩ := h
  exact ⟨by simpa using hp, by simpa using hd, by simpa using hr⟩

/-- If `x y` and `y z` both cancel (either order), `z` agrees with `x` on everything but the label. -/
theorem either_overlap (x y z : Term) (h1 : cancels true x y = true) (h2 : cancels true y z = true)
    (hx : x.label = 0) (hz : z.label = 0) : z = x := by
  obtain ⟨p1, d1, r1⟩ := cancels_either_spec h1
  obtain ⟨p2, d2, r2⟩ := cancels_either_spec h2
  have hn := partner_involutive x.noetic y.noetic z.noetic p1 p2
  cases x
  cases z
  simp_all

def labelFree (w : List Term) : Prop := ∀ t, t ∈ w → t.label = 0

theorem step_labelFree (eo : Bool) (st : List Term) (t : Term) (h : labelFree st) (ht : t.label = 0) :
    labelFree (step id eo st t) := by
  intro x hx
  cases st with
  | nil =>
    simp [step] at hx
    rw [hx]
    exact ht
  | cons top rest =>
    by_cases hc : cancels eo top t = true
    · simp [step, hc] at hx
      exact h x (by simp [hx])
    · simp [step, hc] at hx
      rcases hx with hx | hx
      · rw [hx]; exact ht
      · exact h x (by simpa using hx)

theorem foldl_labelFree (eo : Bool) (l : List Term) : ∀ st : List Term, labelFree st → labelFree l →
    labelFree (l.foldl (step id eo) st) := by
  induction l with
  | nil => intro st h _; simpa using h
  | cons x xs ih =>
    intro st h hl
    simp only [List.foldl_cons]
    apply ih
    · exact step_labelFree eo st x h (hl x (by simp))
    · intro t ht; exact hl t (by simp [ht])

/-- A cancelling pair pushed onto a reduced, label-free stack leaves it as it was (either order). -/
theorem pair_vanishes_either (a b : Term) (hab : cancels true a b = true)
    (_ha : a.label = 0) (hb : b.label = 0) (st : List Term)
    (hst : good id true st = true) (hl : labelFree st) :
    [a, b].foldl (step id true) st = st := by
  cases st with
  | nil => simp [step, hab]
  | cons top rest =>
    by_cases hta : cancels true top a = true
    · have hbt : b = top := either_overlap top a b hta hab (hl top (by simp)) hb
      rw [hbt]
      cases rest with
      | nil => simp [step, hta]
      | cons r rs =>
        have hr : cancels true r top = false := by
          simp only [good, id, Bool.and_eq_true, Bool.not_eq_true'] at hst
          exact hst.1
        simp [step, hta, hr]
    · have hf : cancels true top a = false := by simpa using hta
      simp [step, hf, hab]

theorem fold_respects_cancel_either (x y : List Term) (a b : Term)
    (hab : cancels true a b = true) (hall : labelFree (x ++ [a, b] ++ y)) :
    (x ++ [a, b] ++ y).foldl (step id true) [] = (x ++ y).foldl (step id true) [] := by
  have hx : labelFree x := fun t ht => hall t (by simp [ht])
  have ha : a.label = 0 := hall a (by simp)
  have hb : b.label = 0 := hall b (by simp)
  simp only [List.foldl_append]
  rw [pair_vanishes_either a b hab ha hb _ (foldl_good id true x [] rfl)
        (foldl_labelFree true x [] (fun _ h => by simp at h) hx)]

theorem reach_labelFree {u v : List Term} (h : Reach id true u v) : labelFree u → labelFree v := by
  induction h with
  | refl => exact fun hu => hu
  | tail _ hs ih =>
    intro hu
    have hv := ih hu
    cases hs with
    | cancel x y a b _ =>
      intro t ht
      apply hv t
      simp only [List.mem_append] at ht ⊢
      rcases ht with h | h
      · exact Or.inl (Or.inl h)
      · exact Or.inr h

theorem reach_fold_either {u v : List Term} (h : Reach id true u v) : labelFree u →
    u.foldl (step id true) [] = v.foldl (step id true) [] := by
  induction h with
  | refl => intro _; rfl
  | tail h1 hs ih =>
    intro hu
    cases hs with
    | cancel x y a b hab =>
      rw [ih hu, fold_respects_cancel_either x y a b hab (reach_labelFree h1 hu)]

/-- MAIN RESULT (either-order reading, no labels). Any order of either-order cancellations that
ends where nothing more cancels ends on the compiler's either-order canonical form, for words of
any length whose terms carry no label. This is the setting of the patent's / Rust engine's
"unique canonical form" theorem, and there the claim holds. -/
theorem normal_form_unique_either_unlabelled {u v : List Term} (h : Reach id true u v)
    (hv : noRedex id true v = true) (hu : labelFree u) :
    (u.foldl (step id true) []).reverse = v := by
  rw [reach_fold_either h hu,
      fold_noRedex id true v [] hv (by intro top a h1 _; simp at h1)]
  simp

/-! ## FINDING N-A: the either-order reading has two canonical forms -/

/-- `^2^C|T` -/
def t2T : Term := ⟨2, 1, 0, 1⟩
/-- `^3^C` -/
def t3 : Term := ⟨3, 1, 0, 0⟩
/-- `^2^C|f` -/
def t2f : Term := ⟨2, 1, 0, 3⟩

theorem either_order_two_normal_forms :
    Reach id true [t2T, t3, t2f] [t2f] ∧ Reach id true [t2T, t3, t2f] [t2T] ∧
    noRedex id true [t2f] = true ∧ noRedex id true [t2T] = true ∧ t2T ≠ t2f ∧
    reduce id true [t2T, t3, t2f] = [t2f] ∧ reduce id false [t2T, t3, t2f] = [t2f] := by
  refine ⟨?_, ?_, rfl, rfl, by decide, by decide, by decide⟩
  · exact Reach.tail (Reach.refl _) (Step.cancel [] [t2f] t2T t3 (by decide))
  · exact Reach.tail (Reach.refl _) (Step.cancel [t2T] [] t3 t2f (by decide))

/-! ## The Dual Cancellation criterion (`_nesting_criterion`, line 996) -/

/-- Which landing thought may resolve surfacing thought `n`: its exact partner, or with
`any_landing` any landing-side Noetic. -/
def wanted (anyLanding : Bool) (n m : Nat) : Bool :=
  if anyLanding then landing m else partner n == some m

/-- Positions paired with live terms, as in `live = [p for p in positions if ...]`. -/
def livePositions (w : List Term) : List (Nat × Term) :=
  ((List.range w.length).zip w).filter (fun p => p.2.noetic != 0)

/-- The state carried through the loop: used landing positions, resolved pairs, unresolved positions. -/
abbrev CritState := List Nat × List (Nat × Nat) × List Nat

def critStep (eo anyLanding : Bool) (lv : List (Nat × Term)) (acc : CritState) (p : Nat × Term) :
    CritState :=
  if !surfacing p.2.noetic then acc else
    let used := acc.1
    let ok := fun (q : Nat × Term) =>
      !used.contains q.1 && wanted anyLanding p.2.noetic q.2.noetic && sameSetting p.2 q.2
    let found := match lv.find? (fun q => decide (q.1 > p.1) && ok q) with
      | some q => some q
      | none => if eo then lv.find? (fun q => decide (q.1 < p.1) && ok q) else none
    match found with
    | some q => (q.1 :: used, acc.2.1 ++ [(min p.1 q.1, max p.1 q.1)], acc.2.2)
    | none => (used, acc.2.1, acc.2.2 ++ [p.1])

/-- `_nesting_criterion`: (resolved pairs, unresolved surfacing positions). -/
def criterion (eo anyLanding : Bool) (w : List Term) : List (Nat × Nat) × List Nat :=
  let lv := livePositions w
  let r := lv.foldl (critStep eo anyLanding lv) ([], [], [])
  (r.2.1, r.2.2)

/-- The `met` field: `false` if a surfacing thought is unresolved, `true` if every one is
resolved and there is at least one, `none` (Python `None`) if there is none. -/
def met (eo anyLanding : Bool) (w : List Term) : Option Bool :=
  if !(criterion eo anyLanding w).2.isEmpty then some false
  else if (livePositions w).any (fun p => surfacing p.2.noetic) then some true else none

/-- Exhaustive search: can EVERY surfacing thought get its own partner under the same rules? -/
def resolveAll (eo anyLanding : Bool) (lv : List (Nat × Term)) : List (Nat × Term) → List Nat → Bool
  | [], _ => true
  | p :: ps, used => lv.any (fun q =>
      !used.contains q.1 && (decide (q.1 > p.1) || (eo && decide (q.1 < p.1))) &&
      wanted anyLanding p.2.noetic q.2.noetic && sameSetting p.2 q.2 &&
      resolveAll eo anyLanding lv ps (q.1 :: used))

def canResolveAll (eo anyLanding : Bool) (w : List Term) : Bool :=
  let lv := livePositions w
  resolveAll eo anyLanding lv (lv.filter (fun p => surfacing p.2.noetic)) []

/-! ## All normal forms by brute force (used by the bounded checks) -/

/-- Every word reachable in one cancellation. -/
def oneStep (eo : Bool) : List Term → List (List Term)
  | a :: b :: rest =>
      (if cancels eo a b then [rest] else []) ++ (oneStep eo (b :: rest)).map (a :: ·)
  | _ => []

/-- Every word reachable where nothing more cancels (fuel = word length is enough: each step
removes two terms). -/
def normalForms (eo : Bool) : Nat → List Term → List (List Term)
  | 0, w => [w]
  | fuel + 1, w =>
    match oneStep eo w with
    | [] => [w]
    | nexts => (nexts.flatMap (normalForms eo fuel)).eraseDups

end Cas.Nesting
