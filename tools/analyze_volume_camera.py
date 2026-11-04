"""Replay noncoplanar body-corner camera fitting from numerical measurements.
Requires NumPy; no official source pixels, network, GUI or external DAT.
"""
from pathlib import Path
import argparse,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def basis(az,el,roll):
 back=np.array([np.sin(az)*np.cos(el),-np.sin(el),np.cos(az)*np.cos(el)]);right=np.array([-np.cos(az),0,np.sin(az)]);down=np.cross(-back,right);return np.array([np.cos(roll)*right+np.sin(roll)*down,-np.sin(roll)*right+np.cos(roll)*down,-back])

def predict(p,xyz=None):
 if xyz is None:raise ValueError('Explicit world coordinates are required')
 az,el,roll,ld,lf,tx,ty,cx,cy=p;d,f=np.exp(ld),np.exp(lf);q=xyz@basis(az,el,roll).T+np.array([tx,ty,d]);return np.array([cx,cy])+f*q[:,:2]/q[:,2,None]

def fit(uv,xyz=None,init=None,fixed_elevation=None,maxiter=160):
 if init is None:init=np.array([math.radians(35),math.radians(35),0,math.log(1500),math.log(2200),0,0,*np.mean(uv,axis=0)])
 p=init.copy();active=list(range(9))
 if fixed_elevation is not None:p[1]=math.radians(fixed_elevation);active.remove(1)
 lam=.001;best=float('inf');iters=0
 for it in range(maxiter):
  residual=(predict(p,xyz)-uv).ravel();cost=residual@residual
  if not np.isfinite(cost):break
  J=[]
  for k in active:
   step=1e-5*max(1,abs(p[k]));q=p.copy();q[k]+=step;qq=p.copy();qq[k]-=step;J.append(((predict(q,xyz)-predict(qq,xyz))/(2*step)).ravel())
  J=np.array(J).T;scale=np.linalg.norm(J,axis=0);scale=np.maximum(scale,1e-9);N=J/scale
  delta=np.linalg.solve(N.T@N+lam*np.eye(len(active)),-N.T@residual)/scale;q=p.copy();q[active]+=delta
  if not (-.1<q[0]<math.pi/2+.1 and -.1<q[1]<math.pi/2-.02 and abs(q[2])<.5 and math.log(90)<q[3]<math.log(1e8) and 0<q[4]<math.log(1e10)):
   lam*=10;continue
  new=(predict(q,xyz)-uv).ravel();newcost=new@new
  if newcost<cost:
   p=q;lam=max(lam/3,1e-10);iters=it+1
   if abs(cost-newcost)<1e-13:break
  else:lam=min(lam*8,1e12)
 return {'parameters':p.tolist(),'azimuth':float(np.degrees(p[0])),'elevation':float(np.degrees(p[1])),'roll':float(np.degrees(p[2])),'distance_ldu':float(np.exp(p[3])),'focal_pixels':float(np.exp(p[4])),'principal_point':p[7:9].tolist(),'translation_xy_ldu':p[5:7].tolist(),'rms_px':float(np.sqrt(np.mean(np.sum((predict(p,xyz)-uv)**2,axis=1)))),'predicted':predict(p,xyz).tolist(),'iterations':iters}

def multistart(uv,xyz=None,fixed=None):
 results=[]
 for dist in [300,1000,4000,20000]:
  init=np.array([math.radians(35),math.radians(35),0,math.log(dist),math.log(dist*1.6),0,0,*np.mean(uv,axis=0)])
  results.append(fit(uv,xyz,init,fixed_elevation=fixed))
 return min(results,key=lambda r:r['rms_px']),results


def local_view(fit):
 p=np.array(fit['parameters']);eye=-basis(*p[:3]).T@np.array([p[5],p[6],np.exp(p[3])]);v=eye/np.linalg.norm(eye)
 return {'azimuth':float(np.degrees(np.arctan2(v[0],v[2]))),'elevation':float(np.degrees(np.arcsin(-v[1]))),'eye_relative_to_brick_center_ldu':eye.tolist()}


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,default=ROOT/'docs/research/VOLUME-CAMERA-DATA.json');parser.add_argument('--output',type=Path);args=parser.parse_args();data=json.loads(args.data.read_text());rows=[]
 for r in data['measurements']:
  result,starts=multistart(np.array(r['points']),np.array(r['world_xyz']));rows.append({'id':r['id'],'threshold':r['threshold'],'camera':result,'local_view':local_view(result),'initializations':len(starts)})
 text=json.dumps({'method':data['method'],'rows':rows},indent=2)+'\n'
 if args.output:
  with args.output.open('x')as stream:stream.write(text)
 else:print(text,end='')
