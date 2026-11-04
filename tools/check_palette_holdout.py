"""Replay the frozen four-material test without official artwork.

Checks numeric data flow, prior model identity, every held-out color, and all
81 separately varied input/target ROI shifts. Source extraction and identity have
separate private evidence hashes; this tool does not claim to repeat them.
"""
from pathlib import Path
import argparse, itertools, json
import numpy as np
from analyze_ldraw_transfer import FACES, metrics, nested, predict
ROOT=Path(__file__).resolve().parents[1]

def check(rerun_palette=False):
    data=json.loads((ROOT/'docs/research/PALETTE-HOLDOUT-2025.json').read_text())
    old=json.loads((ROOT/'docs/research/LDRAW-TRANSFER-RESULTS.json').read_text())
    train=json.loads((ROOT/'docs/research/LDRAW-TRANSFER-DATA.json').read_text())
    rows=[r for r in data['observations']if r['primary']]; checks=[]
    def ok(name,condition): checks.append((name,bool(condition)))
    def near(name,a,b): ok(name,np.allclose(a,b,rtol=0,atol=1e-10))
    ok('all four materials',{r['identity']['code']for r in rows}=={27,30,353,368})
    ok('none in training',not({r['identity']['code']for r in rows}&{r['code']for r in train['colors']}))
    ok('frozen full-data model',data['models']['current']==old['final_model'])
    ok('input palette matches pinned data',data['palette_inputs']['all17_current_values_equal_pinned'])
    for r in rows:
        x=np.array([r['identity']['input_RGB']]);y=np.array([[r['faces'][f]for f in FACES]])
        p=predict(data['models']['current'],x)
        near('nominal prediction',p[0],r['nominal_current']['prediction'])
        for k in ('MAE','RMSE','max_channel_error'):near('nominal metric '+k,metrics(p,y)[k],r['nominal_current'][k])
        if 'prediction'in r['nominal_2016']:
            p=predict(data['models']['historical'],np.array([r['nominal_2016']['input_RGB']]))
            near('historical prediction',p[0],r['nominal_2016']['prediction'])
        else:ok('missing historical material explicit',r['identity']['code']in(353,368))
    ys=np.array([[r['faces'][f]for f in FACES]for r in rows])
    ps=predict(data['models']['current'],np.array([r['identity']['input_RGB']for r in rows]))
    actual=metrics(ps,ys)
    for k in ('MAE','RMSE','max_channel_error'):near('aggregate '+k,actual[k],data['summary']['nominal_current'][k])
    for f in FACES:
        for k,v in actual['faces'][f].items():near(f+'/'+k,v,data['summary']['nominal_current']['faces'][f][k])
    gates={}
    for j,f in enumerate(FACES):
        if not j:continue
        gain=data['models']['measured_left_gains'][f];p=np.clip(np.array([r['faces']['left']for r in rows])*gain,0,255)
        for i,r in enumerate(rows):near('face law '+f,p[i],r['measured_left_law']['prediction'][j])
        errors=p-ys[:,j];saved=data['summary']['measured_left_law'][f]
        near(f+'/MAE',abs(errors).mean(),saved['MAE']);near(f+'/max',abs(errors).max(),saved['max_channel_error'])
        variants=[]
        for ii,oo in itertools.product(range(9),repeat=2):
            error=np.array([np.clip(np.array(r['shifts']['left'][ii]['rgb'])*gain,0,255)-r['shifts'][f][oo]['rgb']for r in rows])
            variant=dict(input_shift=ii,target_shift=oo,MAE=float(abs(error).mean()),max_channel_error=float(abs(error).max()))
            variants.append(variant)
        for a,b in zip(variants,saved['sensitivity81']):near('shift MAE',a['MAE'],b['MAE']);near('shift maximum',a['max_channel_error'],b['max_channel_error'])
        gates[f]=dict(all81_pass=all(v['MAE']<=3 and v['max_channel_error']<=10 for v in variants),MAE_range=[min(v['MAE']for v in variants),max(v['MAE']for v in variants)],maximum_channel=max(v['max_channel_error']for v in variants))
    if rerun_palette:
        colors={r['code']:r['rgb']for r in data['palette_inputs']['historical_training_inputs']}
        x=np.array([colors[r['code']]for r in train['colors']]);y=np.array([[r['faces'][f]for f in FACES]for r in train['colors']])
        result=nested(x,y)
        for k in ('MAE','max_channel_error','RMSE'):near('historical nested '+k,result['overall'][k],data['palette_control']['historical'][k])
    return dict(status='PASS'if all(v for _,v in checks)else'FAIL',checks=len(checks),failed=[k for k,v in checks if not v],nominal_gate=all(x['MAE']<=3 for x in actual['faces'].values())and actual['max_channel_error']<=10,face_law_gates=gates,historical_nested_recomputed=rerun_palette,scope=__doc__)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path);ap.add_argument('--rerun-palette-control',action='store_true');args=ap.parse_args()
    result=check(args.rerun_palette_control);text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text);raise SystemExit(result['status']!='PASS')
