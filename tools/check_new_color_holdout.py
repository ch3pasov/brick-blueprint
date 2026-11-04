"""Replay frozen holdouts from measured RGB numbers, without official artwork.

This checks arithmetic, fixed model identity, processing sensitivity, and stated
promotion gates. It does not repeat the original pixel extraction or visual
material identification; those have a separate private evidence receipt.
"""
from pathlib import Path
import argparse,itertools,json,hashlib,sys
from statistics import mean
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_color_law import predict
ROOT=Path(__file__).resolve().parents[1]

def check():
 h=json.loads((ROOT/'docs/research/NEW-COLOR-HOLDOUT.json').read_text());m=h['measurements'];g=json.loads((ROOT/'docs/research/NEW-COLOR-GEOMETRY-TRANSFER.json').read_text());rows=[r for r in m['observations']if r['primary_new_color']];checks=[]
 def ok(name,value):checks.append((name,bool(value)))
 def near(name,a,b):ok(name,abs(a-b)<1e-10)
 def metrics(values):return {'MAE':mean(abs(x)for x in values),'max_channel_error':max(abs(x)for x in values)}
 ok('three distinct new materials',{r['identity']['LDraw_code']for r in rows}=={2,19,322})
 for target in ['right','top']:
  gain=m['frozen_coefficients'][target+'_from_left'];error=[];variants=[]
  for r in rows:
   predicted=[min(255,max(0,x*gain))for x in r['faces']['left']]
   for c in range(3):near(r['id']+'/prediction/'+target,predicted[c],r['prediction'][target][c]);error.append(predicted[c]-r['faces'][target][c])
  actual=metrics(error);saved=m['primary_summary'][target]
  for key in actual:near(target+'/'+key,actual[key],saved[key])
  for i,j in itertools.product(range(9),repeat=2):
   e=[min(255,max(0,r['shifts']['left'][i]['rgb'][c]*gain))-r['shifts'][target][j]['rgb'][c]for r in rows for c in range(3)];variants.append(metrics(e))
  s=saved['ROI_sensitivity'];near(target+'/min MAE',min(v['MAE']for v in variants),s['MAE_range'][0]);near(target+'/max MAE',max(v['MAE']for v in variants),s['MAE_range'][1]);near(target+'/maximum channel',max(v['max_channel_error']for v in variants),s['max_channel_error']);ok(target+'/gate',all(v['MAE']<=3 and v['max_channel_error']<=10 for v in variants)==s['all81_engineering_screen_pass'])
 # Every tested nominal-library family must be the frozen full-data model, not
 # a new fit or a selected fold that benefited from the three new materials.
 prior_path=ROOT/'docs/research/COLOR-LAW-RESULTS.json';prior=json.loads(prior_path.read_text());audit=h['secondary_frozen_ldraw_models'];ok('prior fit hash',hashlib.sha256(prior_path.read_bytes()).hexdigest()==audit['prior_results_sha256']);ok('all nominal families',len(audit['rows'])==21)
 for row in audit['rows']:
  eq=next(q for q in prior['equations']if q['source']=='ldraw'and q['target']==row['target']and q['model']['model']==row['model']['model']);ok('unchanged coefficients',eq['model']==row['model']);pred=predict(row['model'],np.array([r['identity']['nominal_RGB']for r in rows]));obs=np.array([r['faces'][row['target']]for r in rows]);err=(pred-obs).flatten();actual=metrics(err)
  for key in actual:near('nominal '+row['model']['model']+'/'+row['target']+'/'+key,actual[key],row[key])
  for i,record in enumerate(row['records']):ok('stored nominal predictions',np.allclose(pred[i],record['prediction'],rtol=0,atol=1e-10))
 anchors={r['identity']['LDraw_code']:r for r in rows};gr=g['results'];bycode={}
 for row in gr['observations']:
  code=row['ldraw_code'];bycode.setdefault(code,[]).append(row)
  for face,v in row['faces'].items():
   ok('frozen2x2 anchor',v['anchor_prediction']==anchors[code]['faces'][face])
   for c in range(3):near('geometry residual',v['anchor_error'][c],v['anchor_prediction'][c]-v['observed'][c])
   for shift in v['shifted']:
    for c in range(3):near('shifted geometry residual',shift['anchor_error'][c],v['anchor_prediction'][c]-shift['rgb'][c])
 for code,group in bycode.items():
  actual=metrics([e for r in group for f in r['faces'].values()for e in f['anchor_error']]);saved=gr['summary'][str(code)]
  for key in actual:near(str(code)+'/'+key,actual[key],saved[key])
  shifted=[metrics([e for r in group for f in r['faces'].values()for e in f['shifted'][i]['anchor_error']])for i in range(9)]
  ok(str(code)+'/all nine gate',all(q['MAE']<=3 and q['max_channel_error']<=10 for q in shifted)==saved['all_nine_shifts_pass'])
 ok('tan eligible',gr['summary']['19']['all_nine_shifts_pass']);ok('azure not eligible',not gr['summary']['322']['all_nine_shifts_pass']);ok('green not tested','2'in gr['unresolved'])
 return {'status':'PASS'if all(x[1]for x in checks)else'FAIL','checks':len(checks),'failed':[x[0]for x in checks if not x[1]],'face_law_primary':m['primary_summary'],'geometry_gate':{k:v['all_nine_shifts_pass']for k,v in gr['summary'].items()},'scope':__doc__}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();result=check();text=json.dumps(result,indent=2)+'\n'
 if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
 print(text);raise SystemExit(result['status']!='PASS')
