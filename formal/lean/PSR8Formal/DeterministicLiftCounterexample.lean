/-!
# Deterministic-lift correction fixture

This module kernel-checks the exact two-state counterexample.  It proves that
the inherited universal contractivity statement is false.  It does not claim
the universal corrected operator-norm theorem; that real/complex Hilbert-space
formalization remains open.
-/

set_option autoImplicit false
set_option warningAsError true

namespace PSR8
namespace DeterministicLift

/-- Squared Euclidean norm for a two-coordinate integer test vector. -/
def normSquared (vector : Int × Int) : Int :=
  vector.1 * vector.1 + vector.2 * vector.2

/-- Standard-basis lift of the constant map f(0)=f(1)=0. -/
def constantTwoLift (vector : Int × Int) : Int × Int :=
  (vector.1 + vector.2, 0)

theorem input_norm_squared : normSquared (1, 1) = 2 := by decide

theorem output_norm_squared : normSquared (constantTwoLift (1, 1)) = 4 := by decide

/-- The constant two-state lift expands the witness vector, so it is not contractive. -/
theorem constant_two_lift_not_contractive :
    ¬ normSquared (constantTwoLift (1, 1)) ≤ normSquared (1, 1) := by decide

/-- A declared matrix fixture, represented by its four entries. -/
def declaredConstantTwoMatrixFixture : Int × Int × Int × Int := (1, 1, 0, 0)

/-- A declared input-Gram fixture.  This module has no generic matrix calculus. -/
def declaredConstantTwoInputGramFixture : Int × Int × Int × Int := (1, 1, 1, 1)

theorem declared_matrix_fixture :
    declaredConstantTwoMatrixFixture = (1, 1, 0, 0) := rfl

theorem declared_input_gram_fixture :
    declaredConstantTwoInputGramFixture = (1, 1, 1, 1) := rfl

/-- Literal arithmetic used by the executable fixture: this is not a formal
matrix trace or rank theorem until generic matrix/Gram/rank definitions and
bridge lemmas are added. -/
theorem literal_two_ne_one : (2 : Nat) ≠ 1 := by decide

end DeterministicLift
end PSR8
