"""Stable variable-projection fits for the conditional camera-angle experiment.

Image scale, roll and two translations are solved linearly. Inverse distance
is stable at the orthographic limit, avoiding a divergent focal length/center.
No render or measurement is modified.
"""
import math

import numpy as np

import analyze_volume_camera as camera


def unit(angles):
    a,e=angles
    return np.array([np.sin(a)*np.cos(e),-np.sin(e),np.cos(a)*np.cos(e)])


def evaluate(q,xyz,uv,restricted,scale):
    azel=np.radians([35.,35.]) if restricted else q[3:5]
    rot=camera.basis(q[0],q[1],0)
    v=rot@(-unit(azel))
    r=xyz@rot.T/scale
    den=v[2]+q[2]*r[:,2]
    if v[2]<=0 or np.min(den)<=0:
        return None
    # Difference from projection of the origin divided by inverse distance.
    xy=(v[2]*r[:,:2]-v[:2]*r[:,2,None])/(v[2]*den[:,None])
    design=np.zeros((2*len(xyz),4))
    design[0::2]=np.c_[xy[:,0],xy[:,1],np.ones(len(xyz)),np.zeros(len(xyz))]
    design[1::2]=np.c_[xy[:,1],-xy[:,0],np.zeros(len(xyz)),np.ones(len(xyz))]
    linear=np.linalg.lstsq(design,uv.ravel(),rcond=None)[0]
    prediction=(design@linear).reshape(-1,2)
    return prediction,linear


def fit(uv,xyz,initial,restricted=False,maxiter=250):
    scale=float(np.ptp(xyz,axis=0).max())
    if isinstance(initial,dict) and 'reduced' in initial:
        q=np.array(initial['reduced'],float)
        if len(q)==3 and not restricted:q=np.r_[q,np.radians([35.,35.])]
        if len(q)==5 and restricted:q=q[:3]
    else:
        p=np.array(initial)
        view=camera.local_view(dict(parameters=p))
        distance=np.linalg.norm(view['eye_relative_to_brick_center_ldu'])
        q=np.r_[p[:2],scale/distance]
        if not restricted:q=np.r_[q,np.radians([view['azimuth'],view['elevation']])]
    bounds=np.array([[-.1,math.pi/2+.1],[-.1,math.pi/2-.02],[0,scale/90]]+([] if restricted else [[-.1,math.pi/2+.1],[-.1,math.pi/2-.02]]))
    lam=.001
    for iteration in range(maxiter):
        value=evaluate(q,xyz,uv,restricted,scale)
        if value is None:raise ValueError('Invalid initial camera')
        residual=(value[0]-uv).ravel();cost=residual@residual;columns=[]
        for k in range(len(q)):
            step=1e-6
            hi,lo=q.copy(),q.copy();hi[k]+=step;lo[k]-=step
            vh=evaluate(hi,xyz,uv,restricted,scale);vl=evaluate(lo,xyz,uv,restricted,scale)
            columns.append(((vh[0]-vl[0])/(2*step)).ravel())
        jac=np.array(columns).T;norm=np.maximum(np.linalg.norm(jac,axis=0),1e-10);j=jac/norm
        grad=j.T@residual
        active=[k for k in range(len(q)) if not ((q[k]<=bounds[k,0]+1e-14 and grad[k]>0) or (q[k]>=bounds[k,1]-1e-14 and grad[k]<0))]
        projected=np.zeros_like(grad);projected[active]=grad[active]
        if np.max(abs(projected))<1e-8:break
        sub=j[:,active];delta=np.zeros(len(q))
        delta[active]=np.linalg.solve(sub.T@sub+lam*np.eye(len(active)),-grad[active])/norm[active]
        candidate=np.clip(q+delta,bounds[:,0],bounds[:,1])
        if np.linalg.norm(jac@(candidate-q))<1e-10:break
        new=evaluate(candidate,xyz,uv,restricted,scale)
        if new is None:lam*=10;continue
        diff=(new[0]-uv).ravel();newcost=diff@diff
        if newcost<cost:
            q=candidate;lam=max(lam/3,1e-10)
            if cost-newcost<1e-12:break
        else:
            lam=min(lam*8,1e12)
            if lam>=1e10:break
    value,linear=evaluate(q,xyz,uv,restricted,scale)
    rss=float(np.sum((value-uv)**2))
    angles=np.radians([35.,35.]) if restricted else q[3:5]
    return dict(reduced=q.tolist(),linear=linear.tolist(),scale=scale,
                local_angles=np.degrees(angles).tolist(),rss=rss,prediction=value.tolist(),
                inverse_distance=float(q[2]/scale),iterations=iteration+1,
                max_scaled_gradient=float(np.max(abs(grad))))


def refine_pair(uv,xyz,initial,initial_free=None):
    h0=fit(uv,xyz,initial,True)
    h1=fit(uv,xyz,h0 if initial_free is None else initial_free,False)
    if h1['rss']>h0['rss']:
        h1=fit(uv,xyz,h0,False)
    for cycle in range(6):
        h0b=fit(uv,xyz,h0,True,maxiter=1000)
        h1b=fit(uv,xyz,h1,False,maxiter=1000)
        change=max(abs(h0['rss']-h0b['rss']),abs(h1['rss']-h1b['rss']))
        h0,h1=h0b,h1b
        if change<1e-10:break
    if change>=1e-10:raise RuntimeError('Camera RSS did not stabilize')
    for item in [h0,h1]:item['restart_RSS_change']=change;item['restart_cycles']=cycle+1
    # The camera reduced spaces are nested exactly.
    if h1['rss']>h0['rss']+1e-8:raise ValueError('Nested camera residual increased')
    return h0,h1


def legacy_parameters(fit):
    """Equivalent finite pinhole parameters; None at inverse distance zero."""
    q=np.array(fit['reduced']);v=np.array(fit['linear'])
    if q[2]<=1e-12:return None
    angles=np.radians([35.,35.]) if len(q)==3 else q[3:5]
    eye=fit['scale']/q[2]*unit(angles)
    roll=math.atan2(v[1],v[0]);rot=camera.basis(q[0],q[1],roll)
    t=-rot@eye;focal=np.hypot(v[0],v[1])/q[2]
    principal=v[2:]-focal*t[:2]/t[2]
    return np.r_[q[:2],roll,np.log(t[2]),np.log(focal),t[:2],principal].tolist()
