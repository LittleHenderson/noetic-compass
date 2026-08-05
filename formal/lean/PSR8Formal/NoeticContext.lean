/-!
# Noetic Topos 2.0 finite marked-context facts

The four atoms carry two Boolean coordinates.  ACBE covers split the first
coordinate and RPM covers split the second.  The theorems below check
exhaustiveness, properness at the global context, transverse singleton
refinement, and explicit global witness maps separating the two gluing tests.

These are formal facts about the candidate finite context factor only.  They
do not formalize the product-site comparison or license empirical meaning.
-/

set_option autoImplicit false
set_option warningAsError true

namespace PSR8
namespace NoeticContext

universe u v

structure Atom where
  acbe : Bool
  rpm : Bool
  deriving DecidableEq, Repr

abbrev Context := Atom → Prop

def top : Context := fun _ => True

def acbePiece (mark : Bool) (context : Context) : Context :=
  fun atom => context atom ∧ atom.acbe = mark

def rpmPiece (mark : Bool) (context : Context) : Context :=
  fun atom => context atom ∧ atom.rpm = mark

theorem acbe_exhaustive (context : Context) (atom : Atom) :
    context atom ↔ acbePiece false context atom ∨ acbePiece true context atom := by
  constructor
  · intro present
    cases h : atom.acbe <;> simp [acbePiece, present, h]
  · intro covered
    cases covered with
    | inl left => exact left.1
    | inr right => exact right.1

theorem rpm_exhaustive (context : Context) (atom : Atom) :
    context atom ↔ rpmPiece false context atom ∨ rpmPiece true context atom := by
  constructor
  · intro present
    cases h : atom.rpm <;> simp [rpmPiece, present, h]
  · intro covered
    cases covered with
    | inl left => exact left.1
    | inr right => exact right.1

def atom00 : Atom := ⟨false, false⟩
def atom01 : Atom := ⟨false, true⟩
def atom10 : Atom := ⟨true, false⟩
def atom11 : Atom := ⟨true, true⟩

theorem acbe_false_global_proper : ¬ acbePiece false top atom10 := by
  simp [acbePiece, top, atom10]

theorem acbe_true_global_proper : ¬ acbePiece true top atom00 := by
  simp [acbePiece, top, atom00]

theorem rpm_false_global_proper : ¬ rpmPiece false top atom01 := by
  simp [rpmPiece, top, atom01]

theorem rpm_true_global_proper : ¬ rpmPiece true top atom00 := by
  simp [rpmPiece, top, atom00]

theorem transverse_refinement_selects_atom
    (a r : Bool) (atom : Atom) :
    acbePiece a (rpmPiece r top) atom ↔ atom.acbe = a ∧ atom.rpm = r := by
  constructor
  · intro membership
    exact ⟨membership.2, membership.1.2⟩
  · intro coordinates
    exact ⟨⟨True.intro, coordinates.2⟩, coordinates.1⟩

def Injective {α : Sort u} {β : Sort v} (f : α → β) : Prop :=
  ∀ ⦃left right⦄, f left = f right → left = right

def Surjective {α : Sort u} {β : Sort v} (f : α → β) : Prop :=
  ∀ output, ∃ input, f input = output

def Bijective {α : Sort u} {β : Sort v} (f : α → β) : Prop :=
  Injective f ∧ Surjective f

/-- ACBE witness global sections and its exact ACBE gluing map. -/
abbrev ACBEGlobal := Bool × Bool
def acbeGlue (globalSection : ACBEGlobal) : Bool × Bool := globalSection

theorem acbe_glue_bijective : Bijective acbeGlue := by
  constructor
  · intro left right equality
    exact equality
  · intro output
    exact ⟨output, rfl⟩

/-- The same witness has only trivial RPM local data at the global context. -/
def rpmViewOfACBE (_globalSection : ACBEGlobal) : Unit := ()

theorem rpm_view_of_acbe_not_injective : ¬ Injective rpmViewOfACBE := by
  intro injective
  have impossible : (false, false) = (true, false) := injective rfl
  have false_eq_true : false = true := congrArg Prod.fst impossible
  exact Bool.noConfusion false_eq_true

/-- Symmetric RPM witness. -/
abbrev RPMGlobal := Bool × Bool
def rpmGlue (globalSection : RPMGlobal) : Bool × Bool := globalSection
def acbeViewOfRPM (_globalSection : RPMGlobal) : Unit := ()

theorem rpm_glue_bijective : Bijective rpmGlue := by
  constructor
  · intro left right equality
    exact equality
  · intro output
    exact ⟨output, rfl⟩

theorem acbe_view_of_rpm_not_injective : ¬ Injective acbeViewOfRPM := by
  intro injective
  have impossible : (false, false) = (false, true) := injective rfl
  have false_eq_true : false = true := congrArg Prod.snd impossible
  exact Bool.noConfusion false_eq_true

end NoeticContext
end PSR8
