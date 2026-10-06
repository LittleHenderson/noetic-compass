/-!
# Deterministic standard-basis lift: typed functor laws

This file gives a dependency-free finite model of the deterministic
standard-basis lift.  A map from `Fin sourceSize` to `Fin targetSize` sends the
standard basis vector indexed by `column` to the standard basis vector indexed
by its image.

The identity and composition laws below are exact equalities of basis actions
and matrix entries.  We do not define scalar finite sums or claim a theorem
about numerical matrix multiplication in this module.  Instead,
`lift_entry_composition_support` proves the exact entrywise relational-product
equivalent: a composite entry is one exactly when there is a middle index at
which both factor entries are one.
-/

set_option autoImplicit false
set_option warningAsError true

namespace PSR8
namespace DeterministicLiftFunctor

/-- A total map between two explicitly finite typed carriers. -/
structure FiniteMap (sourceSize targetSize : Nat) where
  toFun : Fin sourceSize -> Fin targetSize

namespace FiniteMap

/-- Identity on one exact finite carrier. -/
def id (size : Nat) : FiniteMap size size :=
  { toFun := fun value => value }

/-- Typed composition; the shared middle cardinality is enforced by the type. -/
def comp {sourceSize middleSize targetSize : Nat}
    (after : FiniteMap middleSize targetSize)
    (before : FiniteMap sourceSize middleSize) :
    FiniteMap sourceSize targetSize :=
  { toFun := fun value => after.toFun (before.toFun value) }

theorem id_apply {size : Nat} (value : Fin size) :
    (id size).toFun value = value := rfl

theorem comp_apply {sourceSize middleSize targetSize : Nat}
    (after : FiniteMap middleSize targetSize)
    (before : FiniteMap sourceSize middleSize)
    (value : Fin sourceSize) :
    (comp after before).toFun value = after.toFun (before.toFun value) := rfl

theorem comp_id_left {sourceSize targetSize : Nat}
    (map : FiniteMap sourceSize targetSize) :
    comp (id targetSize) map = map := by
  cases map
  rfl

theorem comp_id_right {sourceSize targetSize : Nat}
    (map : FiniteMap sourceSize targetSize) :
    comp map (id sourceSize) = map := by
  cases map
  rfl

theorem comp_assoc {sizeA sizeB sizeC sizeD : Nat}
    (third : FiniteMap sizeC sizeD)
    (second : FiniteMap sizeB sizeC)
    (first : FiniteMap sizeA sizeB) :
    comp third (comp second first) = comp (comp third second) first := rfl

end FiniteMap

/-- The standard basis vector with its one at `column`. -/
def standardBasis {size : Nat} (column : Fin size) : Fin size -> Nat :=
  fun row => if row = column then 1 else 0

/-- The deterministic lift evaluated on a standard basis vector. -/
def liftOnBasis {sourceSize targetSize : Nat}
    (map : FiniteMap sourceSize targetSize)
    (column : Fin sourceSize) : Fin targetSize -> Nat :=
  standardBasis (map.toFun column)

/-- One entry of the deterministic standard-basis lift matrix. -/
def liftEntry {sourceSize targetSize : Nat}
    (map : FiniteMap sourceSize targetSize)
    (row : Fin targetSize)
    (column : Fin sourceSize) : Nat :=
  liftOnBasis map column row

/-- One entry of the identity matrix, represented without matrix infrastructure. -/
def identityEntry {size : Nat} (row column : Fin size) : Nat :=
  standardBasis column row

/-- `A_id = I`, stated at every matrix entry. -/
theorem lift_entry_identity {size : Nat} (row column : Fin size) :
    liftEntry (FiniteMap.id size) row column = identityEntry row column := rfl

/-- The identity lift fixes every standard basis vector exactly. -/
theorem lift_basis_identity {size : Nat} (column : Fin size) :
    liftOnBasis (FiniteMap.id size) column = standardBasis column := rfl

/-- `A_(g o f)` and `A_g o A_f` agree exactly on each standard basis vector. -/
theorem lift_basis_composition {sourceSize middleSize targetSize : Nat}
    (after : FiniteMap middleSize targetSize)
    (before : FiniteMap sourceSize middleSize)
    (column : Fin sourceSize) :
    liftOnBasis (FiniteMap.comp after before) column =
      liftOnBasis after (before.toFun column) := rfl

/-- A lift entry is one exactly at the image of its column. -/
theorem lift_entry_eq_one_iff {sourceSize targetSize : Nat}
    (map : FiniteMap sourceSize targetSize)
    (row : Fin targetSize)
    (column : Fin sourceSize) :
    liftEntry map row column = 1 <-> row = map.toFun column := by
  unfold liftEntry liftOnBasis standardBasis
  by_cases atImage : row = map.toFun column
  · rw [if_pos atImage]
    constructor
    · intro _entryIsOne
      exact atImage
    · intro _rowAtImage
      rfl
  · rw [if_neg atImage]
    constructor
    · intro impossible
      cases impossible
    · intro rowAtImage
      exact False.elim (atImage rowAtImage)

/--
Exact support-level entrywise composition law.  This is the relational-product
counterpart of the finite-sum matrix equation `(A_g A_f) z x`.
-/
theorem lift_entry_composition_support
    {sourceSize middleSize targetSize : Nat}
    (after : FiniteMap middleSize targetSize)
    (before : FiniteMap sourceSize middleSize)
    (row : Fin targetSize)
    (column : Fin sourceSize) :
    liftEntry (FiniteMap.comp after before) row column = 1 <->
      Exists fun middle : Fin middleSize =>
        liftEntry after row middle = 1 /\
        liftEntry before middle column = 1 := by
  constructor
  · intro compositeEntry
    refine Exists.intro (before.toFun column) ?_
    constructor
    · exact (lift_entry_eq_one_iff after row (before.toFun column)).2
        ((lift_entry_eq_one_iff (FiniteMap.comp after before) row column).1
          compositeEntry)
    · exact (lift_entry_eq_one_iff before (before.toFun column) column).2 rfl
  · intro factors
    cases factors with
    | intro middle factorEntries =>
      cases factorEntries with
      | intro afterEntry beforeEntry =>
        have rowEqualsAfter : row = after.toFun middle :=
          (lift_entry_eq_one_iff after row middle).1 afterEntry
        have middleEqualsBefore : middle = before.toFun column :=
          (lift_entry_eq_one_iff before middle column).1 beforeEntry
        apply (lift_entry_eq_one_iff (FiniteMap.comp after before) row column).2
        rw [FiniteMap.comp_apply]
        rw [← middleEqualsBefore]
        exact rowEqualsAfter

/-- The lift has no nonzero support away from the image of a column. -/
theorem lift_entry_eq_zero_iff {sourceSize targetSize : Nat}
    (map : FiniteMap sourceSize targetSize)
    (row : Fin targetSize)
    (column : Fin sourceSize) :
    liftEntry map row column = 0 <-> Not (row = map.toFun column) := by
  unfold liftEntry liftOnBasis standardBasis
  by_cases atImage : row = map.toFun column
  · rw [if_pos atImage]
    constructor
    · intro impossible
      cases impossible
    · intro awayFromImage
      exact False.elim (awayFromImage atImage)
  · rw [if_neg atImage]
    constructor
    · intro _entryIsZero
      exact atImage
    · intro _awayFromImage
      rfl

end DeterministicLiftFunctor
end PSR8
