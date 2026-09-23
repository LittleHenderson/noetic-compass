import json, re
exec(open('analyse2.py').read().split("print('\n=== (2)")[0])
print('=== (9) retention records vs course_p10 correctness, and interference damage by kind ===')
for v in VER:
    for s in SEEDS:
        d = data[(v,s)]; art = d['art']; ret = d['pm']['retention_record_ids']
        rb = {r['record_id']: bool(r['correct']) for r in J(art/'retention_before_scoring.json')['rows']}
        ra = {r['record_id']: bool(r['correct']) for r in J(art/'retention_after_scoring.json')['rows']}
        p10 = d['at'][10]
        same = sum(1 for r in ret if rb[r]==p10[r])
        lost = [r for r in ret if rb[r] and not ra[r]]; won = [r for r in ret if not rb[r] and ra[r]]
        bk = {}
        for r in ret:
            k = rec_kind[r]; bk.setdefault(k,[0,0,0]); bk[k][0]+=1; bk[k][1]+=rb[r]; bk[k][2]+=ra[r]
        print('Helm', v, s, 'ret n', len(ret), 'before==course_p10 on', same, '| before', sum(rb.values()), 'after', sum(ra.values()), '| lost', len(lost), 'won', len(won), '| by kind n/before/after', bk)
wr = data[('2.0','20260918')]['wr']
print('\n2.0 worker_report keys of interest:', {k: wr.get(k) for k in ['learning_on_held_back_established','report_only_status','degraded_checks','ablation_status','checkpoint_check_phase_a_status','checkpoint_check_phase_b_status','completed_main_updates','schedule_plan_mode','claim_bearing']})
print('pass_summaries 2.0/18 first/last', json.dumps(wr['pass_summaries'][0])[:400], '...', json.dumps(wr['pass_summaries'][-1])[:400])
wr1 = data[('1.0','20260918')]['wr']
print('pass_summaries 1.0/18 first/last', json.dumps(wr1['pass_summaries'][0])[:400], '...', json.dumps(wr1['pass_summaries'][-1])[:400])
