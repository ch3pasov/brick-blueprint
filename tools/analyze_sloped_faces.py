"""Replay bounded slope-color predictions from numeric evidence, using stdlib only.

This replays arithmetic, not source extraction. Official pixels are not bundled.
"""
from pathlib import Path
import argparse,hashlib,json,statistics

def analyze(root):
 path=root/'docs/research/SLOPED-FACE-STUDY.json';data=json.loads(path.read_text());palette_path=root/'brick_blueprint/default-style.json';palette=json.loads(palette_path.read_text())['palette'];count=0
 def check(condition,label):
  nonlocal count
  count+=1
  if not condition:raise ValueError(label)
 def near(a,b):return abs(a-b)<1e-9
 def clip(x):return min(255,max(0,x))
 check(hashlib.sha256(palette_path.read_bytes()).hexdigest()==data['palette_sha256'],'palette differs from measured study')
 for kind in ['neutral_affine','dark_anchor_affine']:
  for group,c in data['coefficients'][kind].items():
   x=c['x']if kind=='neutral_affine'else c['dark_face_RGB'];y=c['y']if kind=='neutral_affine'else c['slope_RGB'];xm=statistics.mean(x);ym=statistics.mean(y);gain=sum((a-xm)*(b-ym)for a,b in zip(x,y))/sum((a-xm)**2 for a in x);bias=ym-gain*xm
   check(near(gain,c['gain'])and near(bias,c['bias']),kind+'/'+group+' neutral fit')
 seen={};scores={}
 for r in data['rows']:
  prior=seen.setdefault(r['decoded_sha256'],[]);check(prior==r['prior_exact_pixels'],r['key']+' duplicates');prior.append(r['key']);g=r['group'];co=data['coefficients'];a=co['neutral_affine'][g];d=co['dark_anchor_affine'][g]
  for q in r['measurements']:
   v=q['vertical_RGB'];target=q['slope_RGB'];predictions={'neutral_affine':[clip(a['gain']*x+a['bias'])for x in v],'black_gain':[clip(co['black_gain'][g]['same_image_vertical_gain']*x)for x in v]}
   if r['palette_available']:
    p=palette[str(r['palette_code'])];n=list(map(abs,r['normal']));predictions['current_convex']=[sum(n[i]*p[k][j]for i,k in enumerate(['side','top','front']))/sum(n)for j in range(3)];predictions['dark_anchor_affine']=[clip(d['gain']*x+d['bias'])for x in p['side']]
   check(set(predictions)==set(q['evaluations']),r['key']+' method set')
   for name,pred in predictions.items():
    ev=q['evaluations'][name];err=[x-y for x,y in zip(pred,target)];mae=sum(map(abs,err))/3;mx=max(map(abs,err))
    check(all(near(x,y)for x,y in zip(pred,ev['prediction_RGB'])),r['key']+'/'+name+' prediction')
    check(near(mae,ev['MAE'])and near(mx,ev['max_channel_error']),r['key']+'/'+name+' metric')
    check(ev['pass']==(mae<=3 and mx<=10),r['key']+'/'+name+' gate')
  for name,passed in r['all_shifts_pass'].items():check(passed==all(q['evaluations'][name]['pass']for q in r['measurements']),r['key']+' all shifts')
  if not r['prior_exact_pixels']:
   for name,ev in r['measurements'][4]['evaluations'].items():scores.setdefault(name,[]).append((ev['MAE'],r['all_shifts_pass'][name]))
 for name,vals in scores.items():
  saved=data['stats']['unique_pixels_scores'][name];check(len(vals)==saved['n'],'score size');check(near(statistics.mean(v[0]for v in vals),saved['central_mean_MAE']),'score MAE');check(sum(v[1]for v in vals)==saved['all_shifts_pass'],'score gates')
 return {'status':'PASS','checks':count,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'Arithmetic replay only; source-pixel measurements require separately downloaded official PDFs. No continuous-normal shader claim.','stats':data['stats']}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args();report=analyze(Path(__file__).resolve().parents[1]);text=json.dumps(report,indent=2)+'\n'
 if args.output:args.output.write_text(text)
 print(text)
