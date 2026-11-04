"""Retrospective camera analysis. All stochastic inference is model-conditional."""
from pathlib import Path
import json, hashlib, math
import numpy as np

import argparse
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True, help='New output directory')
args = p.parse_args()
W = args.output.resolve()
W.mkdir(parents=True, exist_ok=False)
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'docs'
def read(name): return json.loads((D/name).read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

# Regularized incomplete beta: continued fraction; no optional scipy dependency.
def betacf(a,b,x):
    qab=a+b; qap=a+1; qam=a-1; c=1.; d=1-qab*x/qap
    d=1/max(d,1e-300); h=d
    for m in range(1,501):
        aa=m*(b-m)*x/((qam+2*m)*(a+2*m))
        d=1+aa*d; d=d if abs(d)>1e-300 else 1e-300
        c=1+aa/c; c=c if abs(c)>1e-300 else 1e-300
        d=1/d; h*=d*c
        aa=-(a+m)*(qab+m)*x/((a+2*m)*(qap+2*m))
        d=1+aa*d; d=d if abs(d)>1e-300 else 1e-300
        c=1+aa/c; c=c if abs(c)>1e-300 else 1e-300
        d=1/d; delta=d*c; h*=delta
        if abs(delta-1)<3e-14: return h
    raise RuntimeError('beta convergence')
def ibeta(a,b,x):
    if x<=0: return 0.
    if x>=1: return 1.
    bt=math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log1p(-x))
    if x<(a+1)/(a+b+2): return bt*betacf(a,b,x)/a
    return 1-bt*betacf(b,a,1-x)/b
def tsf(t,df):
    p=.5*ibeta(df/2,.5,df/(df+t*t))
    return p if t>=0 else 1-p
def tq(p,df):
    lo,hi=-100.,100.
    for _ in range(90):
        mid=(lo+hi)/2
        if 1-tsf(mid,df)<p: lo=mid
        else: hi=mid
    return (lo+hi)/2
def affine(grid, xy):
    X=np.column_stack([np.ones(len(grid)),grid]); b=np.linalg.lstsq(X,xy,rcond=None)[0]
    return X,b,xy-X@b
def angles(b):
    A=b[1:].T; _,s,V=np.linalg.svd(A)
    az=math.degrees(math.atan2(abs(V[0,1]),abs(V[0,0])))
    return np.array([az,math.degrees(math.asin(s[1]/s[0]))])
def shape(az=35.,el=35.):
    a,e=np.radians([az,el]);return np.array([[np.cos(a),np.sin(a)],[-np.sin(e)*np.sin(a),np.sin(e)*np.cos(a)]])
def fixed(grid,xy):
    q=grid@shape().T; X=np.zeros((2*len(grid),4))
    X[0::2]=np.column_stack([q[:,0],-q[:,1],np.ones(len(q)),np.zeros(len(q))])
    X[1::2]=np.column_stack([q[:,1],q[:,0],np.zeros(len(q)),np.ones(len(q))])
    b=np.linalg.lstsq(X,xy.ravel(),rcond=None)[0]
    return (X@b).reshape(-1,2), b
def no_roll(b):
    m=b[1,1]/b[1,0]; n=b[2,1]/b[2,0]
    return [math.degrees(math.atan(math.sqrt(abs(m/n)))),math.degrees(math.asin(math.sqrt(abs(m*n))))]

inventory=read('INVENTORY-GRID-CONTROL.json'); bbox=inventory['source']['placement_bbox_pt'];w,h=inventory['source']['image_pixels']
aspect=((bbox[3]-bbox[1])/h)/((bbox[2]-bbox[0])/w)
rows=[]
for rr in inventory['threshold_results']:
    points=np.array(rr['centers']);grid=points[:,:2];xy=points[:,2:4].copy();xy[:,1]*=aspect
    X,b,res=affine(grid,xy);n=len(grid);df=2*n-6;sse=float((res*res).sum());sigma2=sse/df
    pred0,b0=fixed(grid,xy);sse0=float(((xy-pred0)**2).sum());F=max(0,(sse0-sse)/2/(sse/df));p=(df/(df+2*F))**(df/2)
    theta=angles(b);grad=[]
    for i in range(6):
        d=np.zeros(6);d[i]=1e-5
        grad.append((angles(b+d.reshape(3,2))-angles(b-d.reshape(3,2)))/(2e-5))
    J=np.array(grad).T;cov=sigma2*np.kron(np.linalg.inv(X.T@X),np.eye(2));se=np.sqrt(np.diag(J@cov@J.T))
    ci95=np.column_stack([theta-tq(.975,df)*se,theta+tq(.975,df)*se])
    ci90=np.column_stack([theta-tq(.95,df)*se,theta+tq(.95,df)*se])
    equivalence=[]
    for tol in [1.,.5,.1]:
        ps=[max(tsf((est-(35-tol))/s,df),tsf(((35+tol)-est)/s,df)) for est,s in zip(theta,se)]
        equivalence.append(dict(tolerance_deg=tol,p_by_angle=list(map(float,ps)),p_both=float(max(ps)),pass_both=bool(max(ps)<.05)))
    deletion=[]
    for axis in range(2):
        for level in sorted(set(grid[:,axis])):
            keep=grid[:,axis]!=level;_,bb,_=affine(grid[keep],xy[keep]);deletion.append(dict(axis=axis,level=int(level),angles_deg=angles(bb).tolist()))
    # Gaussian null diagnostic refits each simulation, preserving regression leverage.
    pairs=[(i,j) for i in range(n) for j in range(i+1,n) if abs(grid[i]-grid[j]).sum()==1]
    ii,jj=np.array(pairs).T
    def adjacency(r): return float(np.mean(np.sum(r[ii]*r[jj],axis=1))/np.mean(np.sum(r*r,axis=1)))
    adj=adjacency(res);rng=np.random.default_rng(20261026+int(rr['threshold']))
    H=np.eye(n)-X@np.linalg.pinv(X)
    null=np.array([adjacency(H@rng.normal(size=(n,2))) for _ in range(4999)])
    adjp=(1+int(np.sum(null>=adj)))/5000
    rows.append(dict(threshold=rr['threshold'],n=n,df=df,aspect=aspect,grid=grid.tolist(),xy=xy.tolist(),matrix=b.tolist(),residuals=res.tolist(),fixed_residuals=(xy-pred0).tolist(),angles_deg=theta.tolist(),no_roll_angles_deg=no_roll(b),se_delta_deg=se.tolist(),ci95_delta_t_deg=ci95.tolist(),ci90_delta_t_deg=ci90.tolist(),rms_affine=math.sqrt(sse/n),rms_fixed_35=math.sqrt(sse0/n),F_joint=F,p_joint_exact_shape=p,sse=sse,sse_fixed=sse0,equivalence=equivalence,deletions=deletion,adjacent_residual_alignment=adj,adjacent_residual_iid_refit_mc_p=adjp))

projection=read('PROJECTION-EXPANSION.json');comparisons=[]
for m in projection['measurements']:
    rr=m['threshold_results'][1];ff=rr['fits'];a=ff['affine']['held_out_rms_original_pixels'];p=ff['projective']['held_out_rms_original_pixels']
    ranges=[x['fits']['affine']['held_out_rms_original_pixels']/x['fits']['projective']['held_out_rms_original_pixels'] for x in m['threshold_results']]
    comparisons.append(dict(source=m['source'],n=len(rr['centers']),affine_heldout=a,projective_heldout=p,ratio=a/p,threshold_ratio_range=[min(ranges),max(ranges)]))

# Numerical controls cover the inferential code, not the truth of the source assumptions.
assert abs(tq(.975,10)-2.2281388519649385)<1e-9
assert abs(tsf(1,1)-.25)<1e-12
assert abs(tsf(0,74)-.5)<1e-12
g=np.array([(i,j) for i in range(10) for j in range(4)],float)
for a,e in [(20,15),(35,30),(35,35),(55,50)]:
    for roll in [0,17,-26]:
        r=math.radians(roll);rot=np.array([[math.cos(r),-math.sin(r)],[math.sin(r),math.cos(r)]])
        xy=g@(rot@shape(a,e)).T*22+[80,40];_,b,_=affine(g,xy)
        assert np.max(abs(angles(b)-[a,e]))<1e-9
rng=np.random.default_rng(4973);X=np.column_stack([np.ones(len(g)),g]);pinv=np.linalg.pinv(X)
# Empirical false-rejection control for the exact linear nested F statistic.
reject=0
for _ in range(5000):
    yy=g@shape().T*22+rng.normal(0,.25,(len(g),2));bb=pinv@yy;ss=((yy-X@bb)**2).sum();pr,_=fixed(g,yy);ss0=((yy-pr)**2).sum();f=max(0,(ss0-ss)/2/(ss/74));pp=(74/(74+2*f))**37
    reject+=int(pp<.05)
assert .035<reject/5000<.065
out=dict(schema_version=1,date='2026-10-26',design='Retrospective exploratory reanalysis; no new independent source images.',angle_order=['acute grid-axis azimuth','elevation'],statistical_scope='Conditional iid isotropic Gaussian landmark errors and true affine projection. Delta intervals/TOST approximate. NOT a probability of an exact camera, not population inference; residual diagnostic and model sensitivity can invalidate interpretation.',source=inventory['source'],inventory_results=rows,manual_pilot=read('CAMERA-MEASUREMENTS.json')['measurements'],projection=comparisons,numerical_controls=dict(t_distribution='reference quantile and Cauchy checks passed',angle_recovery_max_error_lt=1e-9,F_null_rejections=reject,F_null_trials=5000),input_hashes={name:sha(D/name) for name in ['INVENTORY-GRID-CONTROL.json','CAMERA-MEASUREMENTS.json','PROJECTION-EXPANSION.json','SHADING-STUDY.json','PAIRED-PARTS.json','PAIRED-THEME-MEASUREMENTS.json']},protocol_sha256=sha(D/'research/CAMERA-STATISTICS-PROTOCOL.md'))
(W/'ANALYSIS.json').write_text(json.dumps(out,indent=2)+'\n')
for r in rows:print(json.dumps({k:r[k] for k in ['threshold','angles_deg','ci95_delta_t_deg','p_joint_exact_shape','equivalence','adjacent_residual_alignment','adjacent_residual_iid_refit_mc_p']},indent=2))
print('Numerical controls',out['numerical_controls'])
