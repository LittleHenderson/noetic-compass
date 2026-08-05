import PSR8Formal

set_option autoImplicit false
set_option warningAsError true

/-!
The verifier runs this file separately and rejects `sorryAx` or unexpected
axioms in the printed dependency reports.
-/

#print axioms PSR8.Arrow.associativity
#print axioms PSR8.DeterministicLift.constant_two_lift_not_contractive
#print axioms PSR8.NoeticContext.acbe_exhaustive
#print axioms PSR8.NoeticContext.rpm_exhaustive
#print axioms PSR8.NoeticContext.transverse_refinement_selects_atom
#print axioms PSR8.NoeticContext.rpm_view_of_acbe_not_injective
#print axioms PSR8.NoeticContext.acbe_view_of_rpm_not_injective
