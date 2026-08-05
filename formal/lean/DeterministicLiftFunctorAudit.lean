import PSR8Formal.DeterministicLiftFunctor

set_option autoImplicit false
set_option warningAsError true

/-!
Kernel dependency audit for the deterministic standard-basis lift lane.
The verification command captures these reports and rejects `sorryAx` or any
project-specific axiom.  No scalar finite-sum matrix product is claimed.
-/

#print axioms PSR8.DeterministicLiftFunctor.FiniteMap.comp_id_left
#print axioms PSR8.DeterministicLiftFunctor.FiniteMap.comp_id_right
#print axioms PSR8.DeterministicLiftFunctor.FiniteMap.comp_assoc
#print axioms PSR8.DeterministicLiftFunctor.lift_entry_identity
#print axioms PSR8.DeterministicLiftFunctor.lift_basis_identity
#print axioms PSR8.DeterministicLiftFunctor.lift_basis_composition
#print axioms PSR8.DeterministicLiftFunctor.lift_entry_eq_one_iff
#print axioms PSR8.DeterministicLiftFunctor.lift_entry_composition_support
#print axioms PSR8.DeterministicLiftFunctor.lift_entry_eq_zero_iff
