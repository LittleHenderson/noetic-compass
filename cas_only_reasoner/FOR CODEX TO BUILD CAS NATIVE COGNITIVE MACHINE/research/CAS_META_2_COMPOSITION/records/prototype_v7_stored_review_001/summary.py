"""Human summary of an already completed v7 stored review. Pure on import."""


def build(result):
    if result.get('status')!='PROTOTYPE_V7_STORED_REVIEW_PASSED' or result.get('completed') is not True:
        raise ValueError('V7_COMPLETED_REVIEW_REQUIRED_FOR_REPORT')
    d=result['diagnostics'];total=d['before_after']['all']
    lines=['# V7 exact-original256 training experiment — checked results','',
        f"CAS task correctness: {total['cas']['correct_before']}/72 before → {total['cas']['correct_after']}/72 after.",
        f"Generic task correctness: {total['generic']['correct_before']}/72 before → {total['generic']['correct_after']}/72 after.",
        f"Rule control: {d['summaries']['all']['rule']['correct']}/72.",'',
        'The main saved program executions were independently checked. A valid trace is not a correct answer. '
        'The checkpoint files were checked as opaque bytes, not loaded or rerun.','',
        '## Data meaning','',
        'This run appends the exact original 256 practice records to a new 640-record base: 896 training records '
        '(128 depth-1, 384 depth-2, 384 depth-3). The original records are allowed only in training. '
        'The full 8,837 known graph exclusions remain in force for the new base, validation and test data. '
        'The merge preserves every validation and test byte from that new base.','',
        'Validation has 96 records: 32 at each of depths 1, 2 and 3. Test has 72 variants in 24 related triplets: '
        '48 depth-3 and 24 depth-4. These are overlapping condition views, not 72 independent program structures. '
        'The recorded development/checkpoint-selection measures are not native task correctness.','',
        'The earlier v6 run used 640 training records without the literal original256; its recovered scores remain '
        'CAS 0/72 → 0/72, generic 0/72 → 0/72 and rule 72/72. The still earlier generic 12/72 result belongs '
        'to another experiment and is not replaced by either run.','',
        '## Main task results','',
        '| Group | Cases | CAS before → after | Generic before → after | Rule |',
        '|---|---:|---:|---:|---:|']
    for key,label in [('all','All'),('depth_3','Depth 3'),('depth_4','Depth 4'),
        ('same_depth','Same-depth condition'),('wording_shift','Changed wording'),('deeper_calls','Deeper calls')]:
        value=d['before_after'][key];summary=d['summaries'][key]
        lines.append(f"| {label} | {value['cas']['attempted_before']} | "
            f"{value['cas']['correct_before']}/{value['cas']['attempted_before']} → "
            f"{value['cas']['correct_after']}/{value['cas']['attempted_after']} | "
            f"{value['generic']['correct_before']}/{value['generic']['attempted_before']} → "
            f"{value['generic']['correct_after']}/{value['generic']['attempted_after']} | "
            f"{summary['rule']['correct']} |")
    lines+=['','## Execution outcomes','',
        '| Selector | Correct | Pre-execution rejection | Complete execution | Post-start failure |',
        '|---|---:|---:|---:|---:|']
    for arm,row in result['outcomes']['results'].items():
        lines.append(f"| {arm} | {row['task_correct']}/{row['total']} | {row['model_rejections']} | "
                     f"{row['native_executed']} | {row['post_admission_runtime_failures']} |")
    lines+=['','Post-start failures remain incorrect attempts, not pre-execution rejections. '
        'Their exact failure files and committed database prefixes are preserved. Missing failed-tick compute '
        'is unknown. Partial prefixes never acquire complete execution traces or successful answers.','',
        '## Binding and recorded-mistake diagnostics','',
        '| Trained selector | Verifier binding correct / unknown / attempted | Literal observation binding | '
        'Named input sites | Named child sites |',
        '|---|---:|---:|---:|---:|']
    for family in ('cas','generic'):
        row=d['summaries']['all'][family+'_trained'];m=row['verifier_metrics']['binding_correct'];n=row['named_site_counts']
        lines.append(f"| {family} | {m['correct']} / {m['unknown']} / {m['attempted']} | "
            f"{n['observation_binding_correct']}/{n['observation_binding_expected']} | "
            f"{n['named_input_sites_correct']}/{n['named_input_sites_expected']} | "
            f"{n['named_child_sites_correct']}/{n['named_child_sites_expected']} |")
    for family in ('cas','generic'):
        row=d['summaries']['all'][family+'_trained']
        lines+=['',family+' first complete-trace difference categories: '+
            str(row['complete_trace_first_difference_categories'])+'.',
            family+' first committed-prefix difference fields: '+str(row['committed_run_first_difference_fields'])+'.']
    lines+=['','Category counts can overlap. Literal names can penalize equivalent renaming. Site order is not '
        'execution order. The first recorded disagreement is not proof of the earliest causal neural token. '
        'A shorter matching committed prefix does not prove early return.','',
        '## Checked training and compute','',
        'Both families must complete 200 epochs and 11,200 optimizer steps under the same registered conditions. '
        'Selection is recomputed from validation only; the test does not choose the checkpoint.','',
        '| Family | Checkpoint | Epoch | Optimizer steps | SHA256 |',
        '|---|---|---:|---:|---|']
    for family,items in result['training_gate']['checkpoints'].items():
        for kind in ('initial','selected','final'):
            row=items[kind]
            lines.append(f"| {family} | {kind} | {row['epoch']} | {row['optimizer_steps']} | "
                         f"`{row['sha256']}` |")
    lines+=['','| Selector | Committed native runs | Reserved policy units | Compute complete |',
            '|---|---:|---:|---|']
    for arm,row in result['outcomes']['results'].items():
        lines.append(f"| {arm} | {row['committed_native_runs_lower_bound']} | "
                     f"{row['reserved_policy_units_lower_bound']} | {row['compute_complete']} |")
    lines+=['','Counts with a post-start failure are lower bounds. Reserved policy units are not measured FLOPs '
        'or an AWS invoice. Phase commands, raw outputs and exact elapsed times remain in the receipt.','',
        '## Known-fixture GPU gate and limits','',
        'The separate GPU smoke check uses the saved seed926603 fixture: 352 training, 24 validation and 9 test records. '
        'It checks one epoch / 22 optimizer steps per family and 9 reference / 45 candidate outcomes. '
        'It is not fresh learning evidence and is not added to the main72 result. The outer GPU phase is capped '
        'at 450 seconds; its inner900-second smoke setting is not extra time.','',
        'Smoke receipts, commands, process exits, checkpoint bytes, case coverage and reported aggregates were checked. '
        'The smoke’s tensors and native SQLite/verifier semantics were not independently replayed. '
        'Changed tensors remain a byte-bound GPU-authored claim. The original four execution-contract GPU tests are '
        'also bound. The main72 stored executions use the unchanged independent stored verifier.','',
        'No local neural execution, provider calls, generated tasks, checkpoint selection or training occurred during '
        'this audit. A consistent stored record does not independently reproduce neural arithmetic. '
        'No automatic promotion, general reasoning, AGI, production readiness or CAS-specific advantage claim follows.','',
        '## Identity','',
        'Job: '+result['job'], 'Source: '+result['source_sha'],
        'Source archive SHA256: '+result['source_archive_sha256'],
        'Packet SHA256: '+result['packet_sha256'],
        'Prerequisite recovery review SHA256: '+result['prerequisite_review_sha256'],
        'All 603 closed source files, 316 protected files, and all extracted packet bytes were checked before/after.','',
        'Full per-case diagnostics, independent verdicts, unknown values, checkpoint identities and exact source '
        'maps are in prototype_stored_review.json beside this summary.','']
    return '\n'.join(lines)
