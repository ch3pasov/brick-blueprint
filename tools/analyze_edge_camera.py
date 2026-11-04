"""Verify/recompute the exploratory cross-theme small-image camera study.

Uses only numerical measurements and provenance, no official artwork or fonts.
The known-camera raster calibration limits angle inference; see the report.
"""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from research_camera_lines import residual, multistart, projection, predict

def polygon_centroid(points):
    x,y=points.T;nx,ny=np.roll(x,-1),np.roll(y,-1)
    cross=x*ny-nx*y
    return np.array([((x+nx)*cross).sum(),((y+ny)*cross).sum()])/(3*cross.sum())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--refit',action='store_true',help='Repeat all source camera optimizations, not just prediction arithmetic')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    source=root/'docs/research/CAMERA-EDGE-STUDY.json';data=json.loads(source.read_text());checks=[];refits=[]
    def check(name,ok):
        checks.append({'name':name,'pass':bool(ok)})
        if not ok:raise AssertionError(name)
    theta=np.linspace(0,2*np.pi,256,endpoint=False);circle=np.c_[6*np.cos(theta),np.zeros(256),6*np.sin(theta)]
    for row in data['fit_rows']:
        xyz=np.array(row['world_corners'])
        for mode,values in row['modes'].items():
            best=values['best'];p=np.array(best['optimization_parameters'])
            errors=residual(p,xyz,row['observed_edges'],mode)
            check(row['key']+mode+' body RMS',abs(np.sqrt(np.mean(errors**2))-best['line_rms_px'])<1e-9)
            if args.refit:
                fitted,starts=multistart(xyz,row['observed_edges'],mode)
                check(row['key']+mode+' refit RMS',abs(fitted['line_rms_px']-best['line_rms_px'])<1e-6)
                check(row['key']+mode+' refit projected corners',np.max(abs(np.array(fitted['predicted_corners'])-best['predicted_corners']))<.01)
                refits.append({'key':row['key'],'threshold':row['threshold'],'mode':mode,'best':fitted})
            caps=next(c for c in data['caps']if c['key']==row['key'])
            predicted=np.array([polygon_centroid(projection(p,np.array(c)+circle,mode))for c in caps['world_cap_centers']])
            comparisons=next(c for c in data['cap_predictions']if c['key']==row['key'])['trials']
            for comparison in [c for c in comparisons if c['body_threshold']==row['threshold']]:
                measured=next(c for c in caps['trials']if c['threshold']==comparison['cap_threshold'])
                centers={c['index']:c['center']for c in measured['caps']if c['status']=='measured'}
                ids=comparison['indices'];observed=np.array([centers[i]for i in ids])*[1,caps['factor']]
                rms=np.sqrt(np.mean(np.sum((predicted[ids]-observed)**2,1)))
                check(row['key']+mode+' heldout caps',abs(rms-comparison['metrics'][mode]['rms_px'])<1e-8)
    check('seven unique source assets',len({s['decoded_rgb_sha256']for s in data['sources']})==7)
    check('native controls expose inference limitation',any(c['within_one_degree']<c['fits']for c in data['native_camera_controls']))
    result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':len(checks),'failed':0,'refit':args.refit,'checks':checks,'refits':refits,
            'scope':'Numerical reproducibility, not proof of exact official camera angles. Raster controls retain substantial bias.'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['passed','failed','refit']}))
if __name__=='__main__':main()
