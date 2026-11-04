"""Replay Oklab conversion and every17-color outer fold from saved numeric data."""
from pathlib import Path
import json,hashlib
import numpy as np
from analyze_color_space_transfer import to_lab,from_lab,fit,predict,base
W=Path(__file__).resolve().parents[1];data=json.loads((W/'docs/research/COLOR-SPACE-TRANSFER.json').read_text());proto=data['protocol'];out=data['summary'];checks=[]
def ok(n,v):checks.append((n,bool(v)))
def near(n,a,b,tol=1e-10):ok(n,np.allclose(a,b,rtol=0,atol=tol))
x=np.array(list(np.ndindex(5,5,5)),float)/4
# Independent direct linear-sRGB implementation from Ottosson's public-domain
# reference. It uses separately published matrices rather than our XYZ route.
M=np.array([[.4122214708,.5363325363,.0514459929],[.2119034982,.6806995451,.1073969566],[.0883024619,.2817188376,.6299787005]])
N=np.array([[.2104542553,.7936177850,-.0040720468],[1.9779984951,-2.4285922050,.4505937099],[.0259040371,.7827717662,-.8086757660]])
ref=np.cbrt(base.decode(x)@M.T)@N.T
near('independent forward conversion',to_lab(x),ref,1e-7);near('roundtrip',from_lab(to_lab(x)),x,1e-12)
near('D65 white',to_lab(np.ones((1,3))),[[1,0,0]],1e-12)
for kind in('channel_affine','oklab_matrix'):
 for arch in('direct','chain'):
  xx=x*255;yy=np.repeat(xx[:,None],3,axis=1);m=fit(dict(kind=kind,architecture=arch,penalty=.1),xx,yy)
  near('identity target '+kind+'/'+arch,predict(m,xx),yy,1e-9)
rows=proto['rows'];xx=np.array([r['input_RGB']for r in rows]);yy=np.array([[r['faces'][f]for f in base.FACES]for r in rows])
for filename,key in [('BASELINE-54.json','baseline54'),('EXPANDED-74.json','expanded74')]:
 r=data['baseline' if key=='baseline54' else 'expanded'];pred=[]
 for i,fold in enumerate(r['folds']):
  ok('outer excluded',i not in fold['training_indices']);ok('exact remaining16',fold['training_indices']==[j for j in range(17)if j!=i])
  model=fit(fold['selected'],xx[fold['training_indices']],yy[fold['training_indices']]);p=predict(model,xx[i:i+1])[0];near('replay prediction',p,fold['prediction']);pred.append(p)
 for k in('MAE','max_channel_error','RMSE'):near('aggregate '+k,base.metrics(pred,yy)[k],out[key][k])
ok('no claimed prospective validation','None'in out['prospective_validation'])
result=dict(status='PASS'if all(v for _,v in checks)else'FAIL',checks=len(checks),failed=[n for n,v in checks if not v],independent_conversion_max=float(abs(to_lab(x)-ref).max()),scope='Independent forward-conversion formula and exact outer-fold replay; no extra independent colors.')
print(json.dumps(result,indent=2));raise SystemExit(result['status']!='PASS')
