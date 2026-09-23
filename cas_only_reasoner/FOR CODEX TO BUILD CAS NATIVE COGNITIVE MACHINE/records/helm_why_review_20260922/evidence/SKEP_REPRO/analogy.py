import json, os, sys, collections
R=sys.argv[1]; T=os.path.join(R,'records','typed_pointer_001')
for tag,pref in (('1.0','receipt_helm1_certified_'),('2.0','receipt_')):
  for s in ('20260917','20260918','20260919'):
    d=os.path.join(T,pref+s,'checkpoints')
    P=json.load(open(os.path.join(d,'course_p10_predictions.json')))['predictions']
    Sc={r['prediction_id']:r for r in json.load(open(os.path.join(d,'course_p10_scoring.json')))['rows']}
    an=[p for p in P if p['answer']['kind']=='analogy']
    vals=collections.Counter(json.dumps(p['answer']['value'],sort_keys=True) for p in an)
    corr=sum(Sc[p['prediction_id']]['correct'] for p in an if p['prediction_id'] in Sc) if an and 'prediction_id' in an[0] else 'NA'
    print(tag,s,'analogy records',len(an),'distinct answers',len(vals),[v[:90] for v in vals][:2],'correct',corr)
