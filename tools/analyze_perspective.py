"""Geometric perspective analysis; NumPy research dependency."""
from pathlib import Path
import json,math
import numpy as np

def predict(H,U):
 z=np.c_[U,np.ones(len(U))]@H.T;return z[:,:2]/z[:,2,None]

def fit(U,Y,projective=True):
 U=np.asarray(U,float);Y=np.asarray(Y,float);uc=U.mean(0);sc=np.sqrt(np.mean((U-uc)**2));yc=Y.mean(0);ys=np.sqrt(np.mean((Y-yc)**2));X=(U-uc)/sc;Z=(Y-yc)/ys;A=np.c_[np.ones(len(X)),X]
 if not projective:
  C=np.linalg.lstsq(A,Z,rcond=None)[0];h=np.r_[C[:,0],C[:,1],0.,0.]
 else:
  Q=np.zeros((2*len(X),8));Q[0::2,:3]=A;Q[1::2,3:6]=A;Q[0::2,6:]=-X*Z[:,0,None];Q[1::2,6:]=-X*Z[:,1,None];h=np.linalg.lstsq(Q,Z.ravel(),rcond=None)[0]
  for it in range(40):
   den=1+X@h[6:];pred=np.c_[A@h[:3],A@h[3:6]]/den[:,None];res=(pred-Z).ravel();J=np.zeros_like(Q);J[0::2,:3]=A/den[:,None];J[1::2,3:6]=A/den[:,None];J[0::2,6:]=-X*pred[:,0,None]/den[:,None];J[1::2,6:]=-X*pred[:,1,None]/den[:,None]
   step=np.linalg.lstsq(J,-res,rcond=None)[0]
   if np.linalg.norm(step)<1e-12:break
   accepted=False
   for f in [1,.5,.25,.125,.0625,.03125]:
    hn=h+f*step;pr=np.c_[A@hn[:3],A@hn[3:6]]/(1+X@hn[6:])[:,None]
    if np.sum((pr-Z)**2)<res@res:h=hn;accepted=True;break
   if not accepted:break
 Hn=np.array([[h[1],h[2],h[0]],[h[4],h[5],h[3]],[h[6],h[7],1]])
 TU=np.array([[1/sc,0,-uc[0]/sc],[0,1/sc,-uc[1]/sc],[0,0,1]]);TY=np.array([[ys,0,yc[0]],[0,ys,yc[1]],[0,0,1]])
 H=TY@Hn@TU;return H/H[2,2]

def az(H):return float(np.degrees(np.arctan2(abs(H[2,0]),abs(H[2,1]))))

def rms(a):return float(np.sqrt(np.mean(np.sum(a*a,axis=1))))

def analyze(centers):
 a=np.array(centers,float);U=a[:,:2];Y=a[:,2:4];ans=dict(n=len(U))
 check=(U[:,0].astype(int)+2*U[:,1].astype(int))%3
 # Four contiguous bands along the longer grid axis, not random points.
 axis=int(np.argmax(np.ptp(U,axis=0)));levels=np.array_split(np.unique(U[:,axis]),4);spatial=np.zeros(len(U),int)
 for k,l in enumerate(levels):spatial[np.isin(U[:,axis],l)]=k
 for pro,name in [(False,'affine'),(True,'projective')]:
  H=fit(U,Y,pro);s=dict(H=H.tolist(),train_rms=rms(predict(H,U)-Y));
  for ids,label in [(check,'checker'),(spatial,'spatial')]:
   err=[];folds=[]
   for k in np.unique(ids):
    train=ids!=k;test=~train;hk=fit(U[train],Y[train],pro);e=predict(hk,U[test])-Y[test];err.extend(e);folds.append(dict(n=int(test.sum()),rms=rms(e),azimuth=az(hk) if pro else None))
   s[label+'_rms']=rms(np.array(err));s[label+'_folds']=folds
  if pro:s['azimuth']=az(H)
  ans[name]=s
 return ans

def camera_family(H,targets=[20,35,50]):
 a,b,p=H[:,0];d,e,q=H[:,1]
 # solve a*x+b*y=c in [cx,cy,S], S=cx^2+cy^2+f^2
 M=np.array([[-(a*q+d*p),-(b*q+e*p),p*q],[-2*(a*p-d*q),-2*(b*p-e*q),p*p-q*q]])
 rhs=-np.array([a*d+b*e,a*a+b*b-d*d-e*e]);base=np.linalg.lstsq(M,rhs,rcond=None)[0];_,_,V=np.linalg.svd(M);direction=V[-1];direction/=np.linalg.norm(direction[:2])
 def calc(t):
  cx,cy,S=base+t*direction;f2=S-cx*cx-cy*cy
  if f2<=0:return None
  f=math.sqrt(f2);K=np.array([[f,0,cx],[0,f,cy],[0,0,1]]);B=np.linalg.solve(K,H);scale=np.linalg.norm(B[:,0]);r1=B[:,0]/scale;r2=B[:,1]/scale;r3=np.cross(r1,r2);rot=np.c_[r1,r2,r3];tr=B[:,2]/scale;el=math.degrees(math.asin(min(1,abs(r3[2]))));recon=K@np.c_[r1,r2,tr];recon/=recon[2,2]
  return dict(elevation=el,focal_px=f,principal_point=[cx,cy],K=K.tolist(),R=rot.tolist(),t=tr.tolist(),camera_center=(-rot.T@tr).tolist(),homography_max_abs_error=float(np.max(abs(recon-H))),orthogonality_error=float(np.max(abs(rot.T@rot-np.eye(3)))))
 # finite interval where f^2 positive
 A=-(direction[0]**2+direction[1]**2);B=direction[2]-2*(base[:2]@direction[:2]);C=base[2]-base[:2]@base[:2];roots=np.sort(np.roots([A,B,C]));lo,hi=roots.real
 # Select the same points on the 30,001-sample interval before constructing
 # three full cameras. For b1 and b2, the first two columns of K^-1 H,
 # the camera normal has z component (b1 x b2)_z / ||b1||^2.
 grid=np.linspace(lo+1e-7*(hi-lo),hi-1e-7*(hi-lo),30001)
 cx,cy,scale_term=base[:,None]+direction[:,None]*grid
 focal_squared=scale_term-cx*cx-cy*cy
 first_x,first_y=a-cx*p,b-cy*p
 second_x,second_y=d-cx*q,e-cy*q
 denominator=first_x**2+first_y**2+focal_squared*p*p
 with np.errstate(divide='ignore',invalid='ignore'):
  normal_z=(first_x*second_y-first_y*second_x)/denominator
 valid=(focal_squared>0)&np.isfinite(normal_z)&(normal_z>0)
 if not np.any(valid):raise ValueError('No positive camera normal on this calibration interval')
 samples=grid[valid]
 angles=np.degrees(np.arcsin(np.clip(normal_z[valid],0,1)))
 return [calc(samples[np.argmin(np.abs(angles-target))]) for target in targets]

def controls():
 rng=np.random.default_rng(48);U=np.array([(u,v) for u in range(12) for v in range(8)],float);runs=[]
 for az0 in [20,35,55]:
  for el0 in [20,35,55]:
   azr,elr=np.radians([az0,el0]);forward=np.array([np.cos(elr)*np.sin(azr),np.cos(elr)*np.cos(azr),np.sin(elr)]);right=np.array([np.cos(azr),-np.sin(azr),0]);up=np.cross(forward,right);rot=np.array([right,up,forward]);K=np.array([[1800,0,1100],[0,1800,-300],[0,0,1]]);H=K@np.c_[rot[:,:2],[-4,-2,110]];H/=H[2,2];Y=predict(H,U);h=fit(U,Y);family=camera_family(h);err=max(x['homography_max_abs_error'] for x in family);runs.append(dict(azimuth=az0,elevation=el0,recovered_azimuth=az(h),reprojection_rms=rms(predict(h,U)-Y),family_error=err))
 if not all(abs(x['recovered_azimuth']-x['azimuth']) < 1e-8 and x['reprojection_rms'] < 1e-8 and x['family_error'] < 1e-8 for x in runs):
  raise ValueError('Known perspective camera does not reproduce the synthetic grid')
 # affine control, all-zero denominator, prediction within precision
 Y=U@np.array([[20,10],[-12,15]])+np.array([80,40])
 if not rms(predict(fit(U,Y,False),U)-Y) < 1e-9:
  raise ValueError('Affine control does not reproduce the synthetic grid')
 return runs

PIXEL_TOLERANCE = 1e-6
ANGLE_TOLERANCE = 1e-4


def match_rows(observed, expected, key, label):
    reference = {row[key]: row for row in expected}
    keys = {row[key] for row in observed}
    if len(reference) != len(expected) or len(keys) != len(observed) or keys != reference.keys():
        raise ValueError(f'{label}: missing, duplicate or unexpected {key}')
    return [(row, reference[row[key]]) for row in observed]


def replay(data, expected):
    maxima = {'px': 0.0, 'deg': 0.0}
    totals = {'trials': 0, 'common_trials': 0}

    def compare(value, reference, unit, label):
        error = abs(value - reference)
        limit = PIXEL_TOLERANCE if unit == 'px' else ANGLE_TOLERANCE
        if not math.isfinite(error) or error > limit:
            raise ValueError(f'{label}: {value} vs {reference}, difference {error:.6g} {unit}')
        maxima[unit] = max(maxima[unit], error)

    for record, saved in match_rows(data['records'], expected['measurements'], 'id', 'Study'):
        name = record['id']
        if (record['group'], record['source']) != (saved['group'], saved['source']):
            raise ValueError(f'{name}: source identity differs')
        observations = record['threshold_results']
        grids = [{tuple(center[:2]) for center in row['centers']} for row in observations]
        if any(len(grid) != len(row['centers']) for grid, row in zip(grids, observations)):
            raise ValueError(f'{name}: duplicate grid coordinate')
        common = set.intersection(*grids)
        if len(common) != saved['common_center_count']:
            raise ValueError(f'{name}: common grid size differs')

        for series in totals:
            for row, reference in match_rows(observations, saved[series], 'threshold', name):
                centers = row['centers']
                if series == 'common_trials':
                    centers = [center for center in centers if tuple(center[:2]) in common]
                label = f"{name}/{series}/{row['threshold']}"
                if len(centers) != reference['n']:
                    raise ValueError(f'{label}: center count differs')
                result = analyze(centers)
                for model in ('affine', 'projective'):
                    actual, target = result[model], reference[model]
                    for metric in ('train_rms', 'checker_rms', 'spatial_rms'):
                        compare(actual[metric], target[metric], 'px', f'{label}/{model}/{metric}')
                    for split in ('checker_folds', 'spatial_folds'):
                        folds = actual[split]
                        if [f['n'] for f in folds] != [f['n'] for f in target[split]]:
                            raise ValueError(f'{label}/{model}/{split}: fold sizes differ')
                        for i, (a, b) in enumerate(zip(folds, target[split])):
                            compare(a['rms'], b['rms'], 'px', f'{label}/{model}/{split}/{i}')
                            if model == 'projective':
                                compare(a['azimuth'], b['azimuth'], 'deg', f'{label}/{split}/{i}/azimuth')
                compare(result['projective']['azimuth'], reference['projective']['azimuth'],
                        'deg', f'{label}/azimuth')
                for split in ('checker_rms', 'spatial_rms'):
                    if not result['projective'][split] < result['affine'][split]:
                        raise ValueError(f'{label}: held-out comparison changed in {split}')
                totals[series] += 1

    check = controls()
    return {
        **totals,
        'max_rms_difference_px': maxima['px'],
        'max_azimuth_difference_deg': maxima['deg'],
        'rms_tolerance_px': PIXEL_TOLERANCE,
        'azimuth_tolerance_deg': ANGLE_TOLERANCE,
        'max_absolute_numeric_difference': max(maxima.values()),
        'synthetic_camera_controls': len(check),
        'max_synthetic_azimuth_error': max(abs(t['azimuth'] - t['recovered_azimuth']) for t in check),
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Repeat the measured projection fits and synthetic controls.')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    records = Path(__file__).resolve().parents[1] / 'docs' / 'research'
    data = json.loads((records / 'PERSPECTIVE-DATA.json').read_text())
    expected = json.loads((records / 'PERSPECTIVE-RESULTS.json').read_text())
    report = replay(data, expected)
    args.output.mkdir(parents=True, exist_ok=False)
    text = json.dumps(report, indent=2)
    (args.output / 'REPLAY.json').write_text(text + '\n')
    print(text)
