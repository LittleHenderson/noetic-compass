import sys, os, random, collections, importlib.util
sys.argv=[sys.argv[0],sys.argv[1]]
spec=importlib.util.spec_from_file_location('gp',os.path.join(os.path.dirname(__file__),'g_parse.py'))
import io,contextlib
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    gp=importlib.util.module_from_spec(spec); spec.loader.exec_module(gp)
tr=gp.out['train'][1]
order=list(range(2048)); random.Random(20260921).shuffle(order); seen=[tr[i] for i in order[:128]]
print('seen128 distinct', len(set(order[:128])))
for name,ps in (('train2048',tr),('seen128',seen)):
    root_left_state=sum(p['left']['node']=='StateLiteral' for p in ps); root_right_state=sum(p['right']['node']=='StateLiteral' for p in ps)
    ops=collections.Counter(); fields=collections.defaultdict(collections.Counter)
    def walk(t):
        if t['node']=='BinaryExpr': ops[t['op']]+=1; walk(t['left']); walk(t['right'])
        else:
            fields['N'][t['operator']]+=1; fields['D'][t['domain']]+=1; fields['F'][t['drive']]+=1; fields['R'][t.get('register','ABSENT')]+=1
    for p in ps: walk(p)
    print(name,'rootop',collections.Counter(p['op'] for p in ps),'root left STATE',root_left_state,'root right STATE',root_right_state,'n',len(ps))
    print('  ops',dict(ops),'F None',fields['F'][None],'/',sum(fields['F'].values()),'R ABSENT',fields['R']['ABSENT'],'/',sum(fields['R'].values()))
    print('  N',fields['N'].most_common(3),'D',fields['D'].most_common(4))
# check R5 used_rows if exists
import json
p=os.path.join(os.path.dirname(os.path.dirname(__file__)),'R5','used_rows.json')
if os.path.exists(p):
    u=json.load(open(p)); print('R5 used_rows type',type(u).__name__, (list(u)[:3] if isinstance(u,dict) else u[:5]))
    ids=[gp.out['train'][0][i]['record_id'] for i in order[:128]]
    print('my first5 ids',ids[:5])
print('--- position-specific (root-left leaf / root-right leaf), rows where that child is a leaf')
for name,ps in (('train2048',tr),('seen128',seen)):
    for side in ('left','right'):
        leaves=[p[side] for p in ps if p[side]['node']=='StateLiteral']
        c=collections.Counter(x['drive'] for x in leaves); r=collections.Counter(x.get('register','ABSENT') for x in leaves)
        print(name,side,'n',len(leaves),'F_NONE',c[None],'REG_ABSENT',r['ABSENT'],'N',collections.Counter(x['operator'] for x in leaves).most_common(2),'D',collections.Counter(x['domain'] for x in leaves).most_common(2))
