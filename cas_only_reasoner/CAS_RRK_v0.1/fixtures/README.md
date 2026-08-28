# Golden conformance fixtures

Six CAS-Sem problem packets (JSON); no English in the input. Each has a
golden expected result in ../golden/expected/. The nine authority-attack
rejections are listed in ../golden/expected_failures/attack_cases.json.

    modux_ponens         P, P -> Q, query Q          -> CONCLUDED Q
    transitive_reasoning precedes chain              -> CONCLUDED precedes(a,c)
    contradiction        P and not-P                 -> CONFLICT_UNRESOLVED
    missing_information  P -> Q, query Q, P absent   -> NEEDS_INFORMATION
    candidate_planning   three plans, incompatible
                         constraints; falsified
                         branches roll back          -> CONCLUDED viable(P1)
    rpm_recursion        goal requires missing
                         knowledge; child resolves;
                         parent resumes              -> CONCLUDED executable(P_launch)

Trace digests: after the first green run, each fixture's trace digest is
frozen into golden/expected_traces/<problem_id>.digest by the
freeze_trace_digests utility (kernel/fixtures.py). A frozen digest makes
any future behavioral change visible as a replay mismatch.
