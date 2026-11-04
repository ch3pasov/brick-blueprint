"""RGB-only instruction-color candidates with nested whole-color validation.

No per-color exceptions, input color codes, artwork or external library. NumPy
is required. Saved candidates are research models, not renderer defaults.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from analyze_color_law import gain_fit,decode,encode
FACES=('left','top','right')
KINDS=('identity','gain','shared_quadratic','matrix','linear_matrix','quadratic','root2')
PENALTIES=(.001,.01,.1,1.,10.)
CANDIDATES=[dict(architecture=a,kind=k,penalty=l)for a in ('direct','chain')for k in KINDS for l in ((0.,)if k in ('identity','gain')else PENALTIES)]

def features(x,kind):
    if kind=='shared_quadratic':return np.c_[x.ravel(),x.ravel()**2,np.ones(x.size)]
    r,g,b=x.T
    columns=[r,g,b]
    if kind=='quadratic':columns += [r*r,g*g,b*b,r*g,r*b,g*b]
    if kind=='root2':columns += [np.sqrt(r*g),np.sqrt(r*b),np.sqrt(g*b)]
    return np.column_stack(columns+[np.ones(len(x))])

def fit(spec,x,y):
    """x: N×3; y: N×3 faces×3 channels, encoded RGB0..255."""
    kind=spec['kind'];targets=y[:,:1,:]if spec['architecture']=='chain'else y
    model=dict(spec);model['coefficients']=[]
    for face in targets.transpose(1,0,2):
        if kind=='identity':coef=[]
        elif kind=='gain':coef=[gain_fit(x/255,face/255)]
        else:
            xx,yy=(decode(x/255),decode(face/255))if kind=='linear_matrix'else (x/255,face/255)
            A=features(xx,kind);delta=(yy-xx).ravel()if kind=='shared_quadratic'else yy-xx
            # Average over input rows, then shrink correction toward identity.
            coef=np.linalg.solve(A.T@A/len(A)+spec['penalty']*np.eye(A.shape[1]),A.T@delta/len(A)).tolist()
        model['coefficients'].append(coef)
    if spec['architecture']=='chain':model['face_gains']=[1.,gain_fit(y[:,0]/255,y[:,1]/255),gain_fit(y[:,0]/255,y[:,2]/255)]
    return model

def predict(model,x):
    x=np.atleast_2d(x).astype(float);kind=model['kind'];result=[]
    for coef in model['coefficients']:
        if kind=='identity':out=x.copy()
        elif kind=='gain':out=x*coef[0]
        else:
            xx=decode(x/255)if kind=='linear_matrix'else x/255
            delta=features(xx,kind)@np.asarray(coef)
            if kind=='shared_quadratic':delta=delta.reshape(xx.shape)
            out=np.clip(xx+delta,0,1)
            if kind=='linear_matrix':out=encode(out)
            out=out*255
        result.append(np.clip(out,0,255))
    if model['architecture']=='chain':result=[np.clip(result[0]*k,0,255)for k in model['face_gains']]
    return np.stack(result,axis=1)

def metrics(pred,y):
    error=np.asarray(pred)-np.asarray(y)
    return dict(MAE=float(abs(error).mean()),max_channel_error=float(abs(error).max()),RMSE=float(np.sqrt(np.mean(error**2))),faces={f:dict(MAE=float(abs(error[:,j,:]).mean()),max_channel_error=float(abs(error[:,j,:]).max()))for j,f in enumerate(FACES)})

def select(x,y):
    scores=[]
    for spec in CANDIDATES:
        preds=[]
        for i in range(len(x)):
            keep=np.arange(len(x))!=i
            preds.append(predict(fit(spec,x[keep],y[keep]),x[i:i+1])[0])
        scores.append(metrics(preds,y)['MAE'])
    return int(np.argmin(scores)),scores

def nested(x,y,verbose=False):
    folds=[];family_preds={a+'/'+k:[]for a in ('direct','chain')for k in KINDS}
    for i in range(len(x)):
        keep=np.arange(len(x))!=i
        best,scores=select(x[keep],y[keep]);m=fit(CANDIDATES[best],x[keep],y[keep]);p=predict(m,x[i:i+1])[0]
        folds.append(dict(index=i,training_indices=np.flatnonzero(keep).tolist(),selected=CANDIDATES[best],model=m,inner_MAE=scores[best],prediction=p.tolist(),observed=y[i].tolist(),residual=(p-y[i]).tolist(),MAE=float(abs(p-y[i]).mean())))
        for key in family_preds:
            a,k=key.split('/');indices=[j for j,c in enumerate(CANDIDATES)if c['architecture']==a and c['kind']==k]
            chosen=min(indices,key=lambda j:scores[j]);fm=fit(CANDIDATES[chosen],x[keep],y[keep]);family_preds[key].append(predict(fm,x[i:i+1])[0])
        if verbose:print('outer color',i+1,'/',len(x),'MAE',folds[-1]['MAE'],flush=True)
    return dict(folds=folds,overall=metrics([f['prediction']for f in folds],y),families={k:metrics(v,y)for k,v in family_preds.items()})

def run(data,sensitivity=True):
    rows=data['colors'];x=np.array([r['input_RGB']for r in rows],float);y=np.array([[r['faces'][f]for f in FACES]for r in rows],float)
    result=nested(x,y,True)
    for row,f in zip(rows,result['folds']):f['color_code']=row['code'];f['label']=row['label']
    best,scores=select(x,y);final=fit(CANDIDATES[best],x,y)
    result.update(candidates=CANDIDATES,final_model=final,final_selection_MAE=scores[best],final_training=metrics(predict(final,x),y),all_candidate_LOCO_scores=[dict(**c,MAE=s)for c,s in zip(CANDIDATES,scores)])
    transfer=[]
    for r in data['transfer']:
        color=next(c for c in rows if c['code']==r['ldraw_code']);p=predict(final,np.array([color['input_RGB']]))[0];obs=np.array([r['faces'][f]['observed']for f in FACES])
        transfer.append(dict(set=r['set'],page=r['page'],image=r['image'],code=color['code'],prediction=p.tolist(),observed=obs.tolist(),MAE=float(abs(p-obs).mean())))
    result['known_color_geometry_transfer']=dict(rows=transfer,**metrics([r['prediction']for r in transfer],[r['observed']for r in transfer]))
    shifts=[]
    if sensitivity:
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                shifted=np.array([[next(s['rgb']for s in r['shifts'][f]if s['dx']==dx and s['dy']==dy)for f in FACES]for r in rows])
                check=result if (dx,dy)==(0,0)else nested(x,shifted)
                shifts.append(dict(dx=dx,dy=dy,overall=check['overall'],selected_models=[f['selected']for f in check['folds']]))
                print('ROI shift',dx,dy,'MAE',check['overall']['MAE'],flush=True)
    result['sensitivity']=shifts
    result['gate_passes']=all(m['MAE']<=3 for m in result['overall']['faces'].values())and result['overall']['max_channel_error']<=10
    result['scope']='Retrospective nested whole-color holdouts on13 colors. Final fit and known-color geometry transfer are not unseen-color tests. No default palette change.'
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--data',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--no-sensitivity',action='store_true');a=ap.parse_args()
    if a.output.exists():ap.error('Choose a new output path')
    d=json.loads(a.data.read_text());out=run(d,not a.no_sensitivity);out.update(data_sha256=hashlib.sha256(a.data.read_bytes()).hexdigest(),protocol_sha256=d['protocol_sha256'],analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ('overall','final_model','final_training','gate_passes')},indent=2))
