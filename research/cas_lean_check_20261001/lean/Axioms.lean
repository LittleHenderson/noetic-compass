import CasCheck
/-!
`lake env lean Axioms.lean` prints, for every theorem, the axioms its proof rests on.
* `propext`, `Quot.sound`, `Classical.choice`: Lean's standard axioms.
* `Lean.ofReduceBool`: the proof trusts compiled code (`native_decide`), not only the kernel.
* `sorryAx` would mean an unfinished proof. It must not appear.
-/
open Cas Cas.Nesting Cas.Diff

#print axioms compose_closed
#print axioms compose_comm
#print axioms compose_assoc
#print axioms compose_zero_left
#print axioms compose_zero_right
#print axioms inv_inv
#print axioms inv_fixed_points
#print axioms invPair_iff
#print axioms stateIndex_roundtrip
#print axioms stateIndex_onto
#print axioms D0_is_diagonal
#print axioms admissible_refl
#print axioms timesDomain_descends
#print axioms timesDomain_assoc_when_defined
#print axioms arrow_descent_flag_always_true
#print axioms B1_arrow_admissible_is_vacuous
#print axioms B1_arrow_admissible_is_vacuous_general
#print axioms B2_compose_of_pairs
#print axioms B2_compose_never_cancels_a_pair
#print axioms B2_divide_cancels_pairs
#print axioms B2_compose_inverse
#print axioms B3_divide_comm
#print axioms B4_divide_zero_not_identity
#print axioms B4_divide_examples
#print axioms B5_inv_not_hom
#print axioms B5_inv_count
#print axioms B6_plus_order_matters
#print axioms B6_consequence
#print axioms B7_minus_self
#print axioms B8_times_brackets_matter
#print axioms B8_count
#print axioms B8_direction
#print axioms B6_count
#print axioms B7_minus_keeps_left
#print axioms B9_minus_leaves_zero_weight
#print axioms B1_larrow_flag
#print axioms B1_biarrow_flag
#print axioms B1_larrow_flag_general
#print axioms good_tail
#print axioms step_good
#print axioms foldl_good
#print axioms partner_involutive
#print axioms either_overlap
#print axioms pair_vanishes_either
#print axioms fold_respects_cancel_either
#print axioms reach_fold_either
#print axioms normal_form_unique_either_unlabelled
#print axioms either_order_unique_without_labels
#print axioms surfacing_partner_landing
#print axioms ordered_no_overlap
#print axioms pair_vanishes_ordered
#print axioms fold_respects_cancel_ordered
#print axioms reach_fold_ordered
#print axioms fold_noRedex
#print axioms normal_form_unique_ordered
#print axioms either_order_two_normal_forms
#print axioms W5_count
#print axioms reduce_is_irreducible
#print axioms ordered_unique_bounded
#print axioms either_order_answer_is_a_normal_form
#print axioms greedy_criterion_is_optimal
#print axioms compiler_was_python_fallback
#print axioms core_matches_compiler
#print axioms nesting_matches_compiler
