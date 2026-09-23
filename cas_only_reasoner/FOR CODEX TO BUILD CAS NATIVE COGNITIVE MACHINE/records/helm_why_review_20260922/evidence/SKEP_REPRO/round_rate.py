# Read round_rate from final.pt WITHOUT importing torch: stub unpickler over the zip.
import zipfile, pickle, struct, math, sys, os, hashlib
R=sys.argv[1]; T=os.path.join(R,'records','typed_pointer_001')
class Stor:
    def __init__(s,key,dtype): s.key=key; s.dtype=dtype
class DT:
    def __init__(s,name): s.name=name
class Tens:
    def __init__(s,stor,off,size,stride): s.stor=stor; s.off=off; s.size=size; s.stride=stride
def rebuild(stor,off,size,stride,*a): return Tens(stor,off,size,stride)
class U(pickle.Unpickler):
    def find_class(self,mod,name):
        if name=='_rebuild_tensor_v2': return rebuild
        if mod=='torch' and name.endswith('Storage'): return DT(name)
        if mod=='collections' and name=='OrderedDict':
            import collections; return collections.OrderedDict
        return lambda *a,**k: ('OBJ',mod,name,a)
    def persistent_load(self,pid):
        return Stor(pid[2],pid[1])
def walk(o,pre=''):
    if isinstance(o,dict):
        for k,v in o.items(): yield from walk(v,pre+'/'+str(k))
    elif isinstance(o,(list,tuple)):
        for i,v in enumerate(o): yield from walk(v,pre+'/'+str(i))
    elif isinstance(o,Tens): yield pre,o
for tag,pref in (('1.0','receipt_helm1_certified_'),('2.0','receipt_')):
    for seed in ('20260917','20260918','20260919'):
        for ck in ('initial.pt','final.pt'):
            p=os.path.join(T,pref+seed,'checkpoints',ck)
            z=zipfile.ZipFile(p); names=z.namelist(); root=names[0].split('/')[0]
            obj=U(z.open(root+'/data.pkl')).load()
            hits=[(k,t) for k,t in walk(obj) if 'round_rate' in k]
            for k,t in hits:
                raw=z.read(root+'/data/'+t.stor.key)
                v=struct.unpack_from('<f',raw,4*t.off)[0]
                print(tag,seed,ck,k,'round_rate',repr(v),'g=0.01*tanh',repr(0.01*math.tanh(v)), 'sha256(final.pt)' if ck=='final.pt' else '', hashlib.sha256(open(p,'rb').read()).hexdigest()[:16] if ck=='final.pt' else '')
