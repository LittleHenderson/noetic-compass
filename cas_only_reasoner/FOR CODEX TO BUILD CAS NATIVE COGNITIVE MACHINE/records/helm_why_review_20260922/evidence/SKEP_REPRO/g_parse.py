# Independent parser for visible G observations (no sealed files read).
import json, sys, os, re, collections
R=sys.argv[1]; D=os.path.join(R,'research','helm_cas_expression_lab','data','q3_v0_7')
def load(split): return [json.loads(l) for l in open(os.path.join(D,'visible_G_%s.jsonl'%split),encoding='utf-8')]
LEAF=re.compile(r"\^(\d)\^([PCEO])(?:_\{F(\d)\})?(?:\|([AfET]))?")
def parse(s):
    i=0
    def expr():
        nonlocal i
        if s[i]=='(':
            i+=1; l=expr(); 
            assert s[i]==' '; i+=1
            op={'+':'PLUS','×':'TIMES'}[s[i]]; i+=1; assert s[i]==' '; i+=1
            r=expr(); assert s[i]==')'; i+=1
            return {'node':'BinaryExpr','op':op,'left':l,'right':r}
        m=LEAF.match(s,i); assert m, s[i:]
        i=m.end()
        n={'node':'StateLiteral','operator':'^'+m.group(1),'domain':m.group(2),'drive':('F'+m.group(3)) if m.group(3) else None}
        if m.group(4): n['register']=m.group(4)
        return n
    t=expr(); assert i==len(s),(s,i); return t
def render(t):
    if t['node']=='BinaryExpr': return '(%s %s %s)'%(render(t['left']),{'PLUS':'+','TIMES':'×'}[t['op']],render(t['right']))
    s=t['operator']+'^'+t['domain']
    if t['drive']: s+='_{'+t['drive']+'}'
    if t.get('register'): s+='|'+t['register']
    return s
def depth(t): return 0 if t['node']=='StateLiteral' else 1+max(depth(t['left']),depth(t['right']))
def shape(t): return 'L' if t['node']=='StateLiteral' else '(%s%s)'%(shape(t['left']),shape(t['right']))
def toks(t):
    if t['node']=='BinaryExpr': return ['BINARY',t['op']]+toks(t['left'])+toks(t['right'])
    return ['STATE','N'+t['operator'][1:],'D_'+t['domain'] if t['domain'] else 'D_NONE',t['drive'] or 'F_NONE',('REG_'+t['register']) if 'register' in t else 'REG_ABSENT']
tr=load('train'); dv=load('dev')
out={}
for name,rows in (('train',tr),('dev',dv)):
    ps=[parse(r['observation']) for r in rows]
    rb=sum(render(p)==r['observation'] for p,r in zip(ps,rows))
    out[name]=(rows,ps)
    print(name,'n',len(rows),'renderback',rb,'depths',collections.Counter(depth(p) for p in ps),'bare shapes',len({shape(p) for p in ps}))
    print('  max bytes',max(len(r['observation'].encode()) for r in rows),'max toks(+EOS)',max(len(toks(p))+1 for p in ps))
trs={shape(p) for p in out['train'][1]}; dvs={shape(p) for p in out['dev'][1]}
print('shared shapes',len(trs&dvs))
mb=max(len(r['observation'].encode()) for r in tr); mt=max(len(toks(p))+1 for p in out['train'][1])
print('dev longer bytes than train max',sum(len(r['observation'].encode())>mb for r in dv),'dev longer tokens',sum(len(toks(p))+1>mt for p in out['dev'][1]))
allt=[t for p in out['train'][1]+out['dev'][1] for t in toks(p)]
print('D_NONE count',allt.count('D_NONE'),'REG_NULL count',allt.count('REG_NULL'),'REG_T count train',sum(toks(p).count('REG_T')>0 for p in out['train'][1]),'rows with |T train/dev',sum('|T' in r['observation'] for r in tr),sum('|T' in r['observation'] for r in dv))
pred={"left":{"domain":"E","drive":None,"node":"StateLiteral","operator":"^7"},"node":"BinaryExpr","op":"PLUS","right":{"domain":"C","drive":None,"node":"StateLiteral","operator":"^7"}}
first16=out['dev'][1][:16]
print('first16 depth',collections.Counter(depth(p) for p in first16),'pred equals parse',sum(p==pred for p in first16))
# check predictions record ids align with first 16 dev
preds=[json.loads(l) for l in open(os.path.join(R,'records','q4_authorized_20260922','run_001','dev_predictions.jsonl'))]
print('pred ids == first16 dev ids', [p['record_id'] for p in preds]==[r['record_id'] for r in dv[:16]])
# gold steps total tokens incl EOS over visible
print('total gold steps (tokens incl EOS) train+dev', sum(len(toks(p))+1 for p in out['train'][1]+out['dev'][1]))
json.dump({'pred':pred},open(os.path.join(os.path.dirname(__file__),'pred.json'),'w'))
