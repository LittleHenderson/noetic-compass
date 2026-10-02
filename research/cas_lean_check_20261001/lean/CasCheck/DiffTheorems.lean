import CasCheck.Differential
/-!
# The Lean copy agrees with the real compiler

Each theorem says: every record the real compiler produced agrees with the Lean copy of its rules,
and the expected number of records is present. Checked by compiled code (`native_decide`).
If the copy were wrong anywhere, this file would fail to build; `Main.lean` prints the details.
-/
namespace Cas.Diff

theorem compiler_was_python_fallback : Generated.engine = "python" := by native_decide

theorem core_matches_compiler : coreOk = true := by native_decide

theorem nesting_matches_compiler : nestOk = true := by native_decide

end Cas.Diff
