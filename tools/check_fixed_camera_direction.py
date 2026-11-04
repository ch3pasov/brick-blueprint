"""Replay the predeclared fixed local35/35 direction check from numeric data.
Requires NumPy only; no official pixels, GUI, DAT or network.
"""
from pathlib import Path
import argparse,json,math
import numpy as np
import analyze_volume_camera as f
ROOT=Path(__file__).resolve().parents[1]
def expand(q,az=35,el=35):
    rot=f.basis(*q[:3]);a,e=np.radians([az,el]);eye=np.exp(q[3])*np.array([np.sin(a)*np.cos(e),-np.sin(e),np.cos(a)*np.cos(e)]);t=-rot@eye
    if t[2]<=0:return None
    return np.r_[q[:3],np.log(t[2]),q[4],t[:2],q[5:7]]

def fit(uv,xyz,initial,az=35,el=35):
    p=np.array(initial);eye=-f.basis(*p[:3]).T@np.r_[p[5:7],np.exp(p[3])];q=np.r_[p[:3],np.log(np.linalg.norm(eye)),p[4],p[7:9]];lam=.001
    for iteration in range(200):
        p=expand(q,az,el);residual=(f.predict(p,xyz)-uv).ravel();cost=residual@residual;cols=[]
        for k in range(7):
            step=1e-5*max(1,abs(q[k]));hi=q.copy();lo=q.copy();hi[k]+=step;lo[k]-=step;cols.append(((f.predict(expand(hi,az,el),xyz)-f.predict(expand(lo,az,el),xyz))/(2*step)).ravel())
        jac=np.array(cols).T;scale=np.maximum(np.linalg.norm(jac,axis=0),1e-9);n=jac/scale
        delta=np.linalg.solve(n.T@n+lam*np.eye(7),-n.T@residual)/scale;candidate=q+delta;ep=expand(candidate,az,el)
        if ep is None or not(-.1<candidate[0]<math.pi/2+.1 and -.1<candidate[1]<math.pi/2-.02 and abs(candidate[2])<.5 and math.log(90)<candidate[3]<math.log(1e8) and 0<candidate[4]<math.log(1e10)):
            lam*=10;continue
        new=(f.predict(ep,xyz)-uv).ravel();newcost=new@new
        if newcost<cost:
            q=candidate;lam=max(lam/3,1e-10)
            if abs(cost-newcost)<1e-13:break
        else:lam=min(lam*8,1e12)
    p=expand(q,az,el);return {'parameters':p.tolist(),'fixed_local_angles':[az,el],'free_parameters':7,'rms_px':float(np.sqrt(np.mean(np.sum((f.predict(p,xyz)-uv)**2,axis=1))))}

def centroid(q):
 a=q;b=np.roll(q,-1,axis=0);cross=a[:,0]*b[:,1]-b[:,0]*a[:,1]
 return ((a+b)*cross[:,None]).sum(0)/(3*cross.sum())

def replay():
 source=json.loads((ROOT/'docs/research/VOLUME-CAMERA-RESULTS.json').read_text())
 expected=json.loads((ROOT/'docs/research/FIXED-DIRECTION-VALIDATION.json').read_text())
 theta=np.linspace(0,2*np.pi,256,endpoint=False);rows=[];maximum_difference=0
 for data in source['stud_validation']['results']:
  centers=np.array(data['world_stud_centers']);observations=[]
  for row in [r for r in source['rows']if r['id']==data['id']]:
   fitted=fit(np.array(row['points']),np.array(row['world_xyz']),row['camera']['parameters'])
   predicted=np.array([centroid(f.predict(np.array(fitted['parameters']),xyz+np.c_[6*np.cos(theta),np.zeros(256),6*np.sin(theta)]))for xyz in centers])
   for measured in data['measured']:
    observed=np.array(measured['centers'])*[1,row['pixel_aspect_y_x']]
    rms=float(np.sqrt(np.mean(np.sum((predicted-observed)**2,1))))
    saved=next(c for r in expected['results']if r['id']==row['id'] for c in r['comparisons']if c['edge_threshold']==row['threshold'] and c['cap_threshold']==measured['threshold'])
    maximum_difference=max(maximum_difference,abs(rms-saved['fixed_35_35_rms_px']))
    observations.append({'edge_threshold':row['threshold'],'cap_threshold':measured['threshold'],'rms_px':rms,'within_one_pixel':rms<=1})
  rows.append({'id':data['id'],'comparisons':observations})
 return {'status':'PASS' if maximum_difference<1e-8 and all(c['within_one_pixel']for r in rows for c in r['comparisons'])else'FAIL','maximum_difference_from_saved_rms':maximum_difference,'results':rows,'limits':expected['limits']}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();result=replay();text=json.dumps(result,indent=2)+'\n'
 if args.output:
  with args.output.open('x')as out:out.write(text)
 else:print(text,end='')
 raise SystemExit(result['status']!='PASS')
