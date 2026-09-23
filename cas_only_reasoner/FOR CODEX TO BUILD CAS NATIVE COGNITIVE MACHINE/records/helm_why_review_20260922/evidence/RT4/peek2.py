import json
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
pc=json.load(open(ROOT+"/records/typed_course_001/checks_002/public_course.json"))
def shape(o,d=0,maxd=4):
    pad="  "*d
    if isinstance(o,dict):
        for k,v in list(o.items())[:30]:
            if isinstance(v,(dict,list)):
                print(pad+str(k)+": "+type(v).__name__+(" len=%d"%len(v)))
                if d<maxd: shape(v,d+1,maxd)
            else:
                print(pad+str(k)+": "+repr(v)[:120])
    elif isinstance(o,list):
        if o:
            shape(o[0],d+1,maxd)
shape(pc)
