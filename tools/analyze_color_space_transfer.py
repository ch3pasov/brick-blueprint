"""Retrospective17-color comparison; no untouched test or renderer promotion."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys
import numpy as np
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P/'tools'))
import analyze_ldraw_transfer as base
from analyze_color_law import decode,encode
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
# D65 RGB/XYZ and XYZ/LMS/Oklab matrices from CSS Color4, section19.
RGB_XYZ=np.array([[506752/1228815,87881/245763,12673/70218],[87098/409605,175762/245763,12673/175545],[7918/409605,87881/737289,1001167/1053270]])
XYZ_LMS=np.array([[.8190224379967030,.3619062600528904,-.1288737815209879],[.0329836539323885,.9292868615863434,.0361446663506424],[.0481771893596242,.2642395317527308,.6335478284694309]])
LMS_LAB=np.array([[.2104542683093140,.7936177747023054,-.0040720430116193],[1.9779985324311684,-2.4285922420485799,.4505937096174110],[.0259040424655478,.7827717124575296,-.8086757549230774]])
def to_lab(rgb):return np.cbrt(decode(rgb)@RGB_XYZ.T@XYZ_LMS.T)@LMS_LAB.T
def from_lab(lab):return encode(((lab@np.linalg.inv(LMS_LAB).T)**3)@np.linalg.inv(XYZ_LMS).T@np.linalg.inv(RGB_XYZ).T)
old_fit,old_predict=base.fit,base.predict
def fit(spec,x,y):
    if spec['kind']not in('channel_affine','oklab_matrix'):return old_fit(spec,x,y)
    kind=spec['kind'];target=y[:,:1]if spec['architecture']=='chain'else y;coefs=[]
    for face in target.transpose(1,0,2):
        if kind=='channel_affine':
            xx,yy=x/255,face/255;coef=[]
            for c in range(3):
                A=np.c_[xx[:,c],np.ones(len(x))];d=yy[:,c]-xx[:,c]
                coef.append(np.linalg.solve(A.T@A/len(A)+spec['penalty']*np.eye(2),A.T@d/len(A)).tolist())
        else:
            xx=to_lab(x/255)/[1,.4,.4];yy=to_lab(face/255)/[1,.4,.4];A=np.c_[xx,np.ones(len(x))];d=yy-xx
            coef=np.linalg.solve(A.T@A/len(A)+spec['penalty']*np.eye(4),A.T@d/len(A)).tolist()
        coefs.append(coef)
    model=dict(spec,coefficients=coefs)
    if spec['architecture']=='chain':model['face_gains']=[1.,base.gain_fit(y[:,0]/255,y[:,1]/255),base.gain_fit(y[:,0]/255,y[:,2]/255)]
    return model
def predict(model,x):
    if model['kind']not in('channel_affine','oklab_matrix'):return old_predict(model,x)
    x=np.atleast_2d(x);out=[]
    for coef in model['coefficients']:
        coef=np.array(coef)
        if model['kind']=='channel_affine':
            xx=x/255;y=xx+xx*coef[:,0]+coef[:,1]
        else:
            xx=to_lab(x/255)/[1,.4,.4];y=from_lab((xx+np.c_[xx,np.ones(len(x))]@coef)*[1,.4,.4])
        out.append(np.clip(y*255,0,255))
    if model['architecture']=='chain':out=[np.clip(out[0]*g,0,255)for g in model['face_gains']]
    return np.stack(out,axis=1)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    W=args.output
    if W.exists():parser.error('Choose a new output directory')
    W.mkdir(parents=True)
    prior=json.loads((P/'docs/research/LDRAW-TRANSFER-DATA.json').read_text());hold=json.loads((P/'docs/research/PALETTE-HOLDOUT-2025.json').read_text())
    rows=[dict(code=r['code'],input_RGB=r['input_RGB'],faces=r['faces'])for r in prior['colors']]
    rows +=[dict(code=r['identity']['code'],input_RGB=r['identity']['input_RGB'],faces=r['faces'])for r in hold['observations']if r['primary']]
    assert len(rows)==len({r['code']for r in rows})==17
    extra=[dict(architecture=a,kind=k,penalty=p)for a in('direct','chain')for k in('channel_affine','oklab_matrix')for p in base.PENALTIES]
    protocol=dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='Retrospective: all17 outcomes were known when this candidate extension was designed.',question='Do channel-specific affine correction or Oklab affine correction improve general RGB-only transfer?',fixed_candidates=base.CANDIDATES+extra,comparison='Original54 and expanded74 candidates, same17 outer colors; every family and penalty selected only inside the remaining16 colors.',oklab='D65 matrices from CSS Color4; Oklab L,a,b divided by1,.4,.4; penalized affine residual, all coefficients shrunk toward identity; invert and clip RGB at output. No chroma gamut mapping.',source='https://www.w3.org/TR/2026/CRD-css-color-4-20261027/#color-conversion-code',precision_gate='Each face MAE<=3 and maximum channel<=10, as before. No promotion from training fit.',rows=rows)
    dump(W/'PROTOCOL.json',protocol)
    # A deterministic conversion roundtrip checks the implementation before fitting.
    controls=np.array(list(np.ndindex(5,5,5)),float)/4
    assert abs(from_lab(to_lab(controls))-controls).max()<1e-12
    x=np.array([r['input_RGB']for r in rows]);y=np.array([[r['faces'][f]for f in base.FACES]for r in rows])
    baseline=base.nested(x,y,True);dump(W/'BASELINE-54.json',baseline)
    base.KINDS+=('channel_affine','oklab_matrix');base.CANDIDATES+=extra;base.fit=fit;base.predict=predict
    expanded=base.nested(x,y,True);dump(W/'EXPANDED-74.json',expanded)
    best,scores=base.select(x,y);model=fit(base.CANDIDATES[best],x,y)
    result=dict(protocol_sha256=sha(W/'PROTOCOL.json'),analysis_sha256=sha(Path(__file__)),conversion_roundtrip_max=float(abs(from_lab(to_lab(controls))-controls).max()),baseline54=baseline['overall'],expanded74=expanded['overall'],new_families={k:v for k,v in expanded['families'].items()if 'oklab' in k or 'channel_affine'in k},fold_codes=[r['code']for r in rows],final_model=model,final_training=base.metrics(predict(model,x),y),prospective_validation='None for this extension; the frozen four-color test remains separate.')
    dump(W/'RESULTS.json',result);print(json.dumps(result,indent=2))
