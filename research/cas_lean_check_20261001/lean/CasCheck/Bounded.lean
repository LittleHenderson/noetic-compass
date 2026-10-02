import CasCheck.Nesting
/-!
# Bounded checks of the Nesting Operator (every word up to a fixed length)

These are complete checks over a FINITE set of words, not proofs for all lengths. They are run by
compiled code (`native_decide`), so they trust Lean's compiler as well as its kernel. Each claim
names the alphabet and the length bound it covers.

Alphabet (9 letters): `^2^C`, `^3^C`, `^2^C|f`, `^3^E`, `^8^C`, `^9^C`, `^6^C`, `^0^C`, `^3^C_{F2}`.
It mixes a cancelling pair, a Register difference, a Domain difference, a Drive difference,
a wrong partner (`^8` with `^6`), and the identity `^0`.
-/
namespace Cas.Nesting

def alphabet : List Term :=
  [⟨2, 1, 0, 0⟩, ⟨3, 1, 0, 0⟩, ⟨2, 1, 0, 3⟩, ⟨3, 2, 0, 0⟩, ⟨8, 1, 0, 0⟩, ⟨9, 1, 0, 0⟩,
   ⟨6, 1, 0, 0⟩, ⟨0, 1, 0, 0⟩, ⟨3, 1, 2, 0⟩]

/-- All words of exactly `n` letters. -/
def wordsOf (alpha : List Term) : Nat → List (List Term)
  | 0 => [[]]
  | n + 1 => (wordsOf alpha n).flatMap (fun w => alpha.map (fun a => a :: w))

/-- All words of 1..n letters. -/
def wordsUpTo (alpha : List Term) (n : Nat) : List (List Term) :=
  (List.range n).flatMap (fun k => wordsOf alpha (k + 1))

def W5 : List (List Term) := wordsUpTo alphabet 5

/-- 9 + 81 + 729 + 6561 + 59049 = 66429 words. -/
theorem W5_count : W5.length = 66429 := by native_decide

/-- The compiler's canonical form never contains two neighbours that still cancel (both readings). -/
theorem reduce_is_irreducible :
    W5.all (fun w => noRedex id false (reduce id false w) && noRedex id true (reduce id true w)) = true := by
  native_decide

/-- Surfacing-first reading: every word has exactly ONE normal form, and it is the compiler's.
(The general proof is `normal_form_unique_ordered`; this re-checks it by brute force.) -/
theorem ordered_unique_bounded :
    W5.all (fun w => normalForms false w.length (live id w) == [reduce id false w]) = true := by
  native_decide

/-- Either-order reading: the words with MORE than one normal form. -/
def eitherOrderAmbiguous : List (List Term) :=
  W5.filter (fun w => (normalForms true w.length (live id w)).length > 1)

/-- FINDING N-A, counted: how many of the 66,429 words have two or more either-order normal forms,
and the compiler's either-order answer is always ONE of them. -/
theorem either_order_answer_is_a_normal_form :
    W5.all (fun w => (normalForms true w.length (live id w)).contains (reduce id true w)) = true := by
  native_decide

/-- The greedy pairing in `_nesting_criterion` never misses: in all three readings it resolves
every surfacing thought exactly when some pairing could. -/
theorem greedy_criterion_is_optimal :
    W5.all (fun w =>
      ((criterion false false w).2.isEmpty == canResolveAll false false w) &&
      ((criterion true false w).2.isEmpty == canResolveAll true false w) &&
      ((criterion false true w).2.isEmpty == canResolveAll false true w)) = true := by
  native_decide

end Cas.Nesting
