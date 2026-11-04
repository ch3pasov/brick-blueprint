"""Replay prospective angular-color controls from numeric data, using stdlib.

This verifies formula arithmetic and aggregate accounting, not source extraction.
Official PDF pixels are deliberately not bundled with this project.
"""
from pathlib import Path
import argparse,hashlib,json,math,statistics

def predict(p,theta,side):
    left,top,right=(p[k] for k in ('side','top','front'))
    clip=lambda x:max(0,min(255,x))
    if side=='left':
        knots=[0,math.degrees(math.atan(.5)),45,90]
        colors=[top,[clip(1.0825688073394497*x-.5504587155963689)for x in left],
                [clip(1.0166342681639444*x-.7151300438319507)for x in left],left]
        vertical=left
    else:
        knots=[0,45,90]
        colors=[top,[clip(1.119266055045872*x+4.8715596330274655)for x in left],right]
        vertical=right
    s,c=math.sin(math.radians(theta)),math.cos(math.radians(theta))
    result={'baseline':[(s*x+c*y)/(s+c)for x,y in zip(vertical,top)]}
    j=next(i for i in range(len(knots)-1)if knots[i]<=theta<=knots[i+1])
    a,b=knots[j:j+2];u=(theta-a)/(b-a)
    result['piecewise_angle']=[(1-u)*x+u*y for x,y in zip(colors[j],colors[j+1])]
    wa,wb=math.sin(math.radians(b-theta)),math.sin(math.radians(theta-a))
    result['piecewise_cone']=[(wa*x+wb*y)/(wa+wb)for x,y in zip(colors[j],colors[j+1])]
    result['global_polynomial']=[clip(sum(colors[i][channel]*math.prod(
        (theta-knots[k])/(knots[i]-knots[k])for k in range(len(knots))if k!=i)
        for i in range(len(knots))))for channel in range(3)]
    return result

def analyze(root):
    path=root/'docs/research/ANGULAR-SHADING-STUDY.json';data=json.loads(path.read_text())
    palette_path=root/'brick_blueprint/default-style.json';palette=json.loads(palette_path.read_text())['palette']
    checks=0
    def ck(ok,label):
        nonlocal checks
        checks+=1
        if not ok:raise ValueError(label)
    near=lambda a,b:abs(a-b)<1e-9
    ck(hashlib.sha256(palette_path.read_bytes()).hexdigest()==data['palette_sha256'],'palette hash')
    seen={};unique=[];known=[];batches={}
    for r in data['rows']:
        prior=seen.setdefault(r['decoded_sha256'],[]);ck(prior==r['prior_exact_pixels'],r['key']+' duplicate accounting')
        if not prior:unique.append(r)
        prior.append(r['key']);p=palette.get(str(r['palette_code']))
        predictions=predict(p,r['inclination'],r['side'])if p else{}
        if p and not r['prior_exact_pixels']:known.append(r)
        ck(len(r['measurements'])==9,r['key']+' nine shifts')
        ck({(q['dx'],q['dy'])for q in r['measurements']}=={(x,y)for x in [-1,0,1]for y in [-1,0,1]},r['key']+' complete shifts')
        for q in r['measurements']:
            ck(set(predictions)==set(q['evaluations']),r['key']+' model set')
            for name,pred in predictions.items():
                ev=q['evaluations'][name];err=[abs(x-y)for x,y in zip(pred,q['slope_RGB'])];mae=sum(err)/3;mx=max(err)
                ck(all(near(a,b)for a,b in zip(pred,ev['prediction_RGB'])),r['key']+name+' prediction')
                ck(near(mae,ev['MAE'])and near(mx,ev['max_channel_error']),r['key']+name+' metrics')
                ck(ev['pass']==(mae<=3 and mx<=10),r['key']+name+' gate')
        for name,value in r['all_shifts_pass'].items():ck(value==all(q['evaluations'][name]['pass']for q in r['measurements']),r['key']+name+' all shifts')
        batches.setdefault(r['batch'],[]).append(r)
    ck(len(data['rows'])==data['counts']['occurrences'],'occurrences')
    ck(len(unique)==data['counts']['unique_pixel_images'],'unique images')
    ck(len(known)==data['counts']['known_palette_unique'],'known unique')
    ck(len({r['set']for r in data['rows']})==data['counts']['sets'],'sets')
    summary={}
    for batch,rows in batches.items():
        selected=[r for r in rows if not r['prior_exact_pixels']and r['all_shifts_pass']]
        methods={}
        for name in ['baseline','piecewise_angle','piecewise_cone','global_polynomial']:
            mean=statistics.mean(r['measurements'][4]['evaluations'][name]['MAE']for r in selected)
            passes=sum(r['all_shifts_pass'][name]for r in selected)
            methods[name]={'n':len(selected),'mean_MAE':mean,'all_shifts_pass':passes}
            saved=data['batches'][batch].get('scores',{}).get(name)
            if saved:
                ck(saved['n']==len(selected)and near(mean,saved['central_mean_MAE']),'aggregate mean '+batch+name)
                ck(saved['all_shifts_pass']==passes,'aggregate gate '+batch+name)
        summary[batch]=methods
    return {'status':'PASS','checks':checks,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'counts':data['counts'],'scores':summary,'scope':'Numeric arithmetic and accounting only; no claim that checks are independent source observations.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=analyze(Path(__file__).resolve().parents[1]);text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text)
