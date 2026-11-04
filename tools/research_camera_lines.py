"""Camera calibration from visible edge segments; cropped right edge excluded."""
from pathlib import Path
import datetime
import hashlib
import json
import math
import sys
import numpy as np

def basis(az,el,roll):
    back=np.array([np.sin(az)*np.cos(el),-np.sin(el),np.cos(az)*np.cos(el)])
    right=np.array([-np.cos(az),0,np.sin(az)])
    down=np.cross(-back,right)
    return np.array([np.cos(roll)*right+np.sin(roll)*down,-np.sin(roll)*right+np.cos(roll)*down,-back])

def predict(p,xyz):
    az,el,roll,ld,lf,tx,ty,cx,cy=p
    q=xyz@basis(az,el,roll).T+np.array([tx,ty,np.exp(ld)])
    return np.array([cx,cy])+np.exp(lf)*q[:,:2]/q[:,2,None]

EDGES = ['AB', 'BC', 'CD', 'DA', 'AE', 'BF', 'EF', 'EG']

def geometry(nx, nz=2, height=24):
    x, z = nx*10, nz*10
    points = np.array([[x,0,z],[x,0,-z],[-x,0,-z],[-x,0,z],
                       [x,height,z],[x,height,-z],[-x,height,z]], float)
    points[:,1] -= height/2
    return points

def expanded_fixed(q):
    rotation = basis(*q[:3])
    az, el = np.radians([35,35])
    eye = np.exp(q[3]) * np.array([np.sin(az)*np.cos(el), -np.sin(el), np.cos(az)*np.cos(el)])
    t = -rotation @ eye
    if t[2] <= 0:
        return None
    return np.r_[q[:3], np.log(t[2]), q[4], t[:2], q[5:7]]

def projection(parameters, xyz, mode):
    if mode == 'orthographic':
        return xyz @ basis(*parameters[:3])[:2].T * np.exp(parameters[3]) + parameters[4:6]
    p = expanded_fixed(parameters) if mode == 'fixed35' else parameters
    return predict(p, xyz)

def residual(parameters, xyz, observations, mode):
    projected = projection(parameters, xyz, mode)
    output = []
    for edge in observations:
        a, b = projected[[ord(c)-65 for c in edge['edge']]]
        direction = b-a
        normal = np.array([-direction[1], direction[0]]) / np.linalg.norm(direction)
        output.extend((np.array(edge['line_samples'])-a) @ normal)
    return np.array(output)

def allowed(p, mode):
    if not np.all(np.isfinite(p)):
        return False
    if not (-.1 < p[0] < math.pi/2+.1 and -.1 < p[1] < math.pi/2-.02 and abs(p[2]) < .5):
        return False
    if mode == 'orthographic':
        return -8 < p[3] < 8
    return math.log(90) < p[3] < math.log(1e8) and 0 < p[4] < math.log(1e10) and (mode != 'fixed35' or expanded_fixed(p) is not None)

def jacobian(p, xyz, observations, mode):
    columns = []
    for k in range(len(p)):
        step = 1e-5 * max(1,abs(p[k]))
        high, low = p.copy(), p.copy()
        high[k] += step
        low[k] -= step
        columns.append((residual(high,xyz,observations,mode)-residual(low,xyz,observations,mode))/(2*step))
    return np.array(columns).T

def local_direction(p):
    eye = -basis(*p[:3]).T @ np.r_[p[5:7], np.exp(p[3])]
    return {'azimuth_deg':float(np.degrees(np.arctan2(eye[0],eye[2]))),
            'elevation_deg':float(np.degrees(np.arctan2(-eye[1],np.hypot(eye[0],eye[2])))),
            'eye_relative_body_center_ldu':eye.tolist()}

def optimize(initial, xyz, observations, mode, maxiter=350):
    p = np.array(initial, float)
    damping = .001
    iterations = 0
    for iteration in range(maxiter):
        r = residual(p,xyz,observations,mode)
        cost = r @ r
        jac = jacobian(p,xyz,observations,mode)
        scale = np.maximum(np.linalg.norm(jac,axis=0),1e-9)
        normalized = jac / scale
        change = np.linalg.solve(normalized.T @ normalized + damping*np.eye(len(p)), -normalized.T @ r) / scale
        candidate = p + change
        if not allowed(candidate,mode):
            damping = min(damping*10,1e12)
            continue
        rr = residual(candidate,xyz,observations,mode)
        new_cost = rr @ rr
        if new_cost < cost:
            p = candidate
            damping = max(damping/3,1e-10)
            iterations = iteration+1
            if abs(cost-new_cost) < 1e-13:
                break
        else:
            damping = min(damping*8,1e12)
    final = residual(p,xyz,observations,mode)
    jac = jacobian(p,xyz,observations,mode)
    normjac = jac / np.maximum(np.linalg.norm(jac,axis=0),1e-9)
    singular = np.linalg.svd(normjac,compute_uv=False)
    out = {'mode':mode,'optimization_parameters':p.tolist(),'iterations':iterations,
           'line_rms_px':float(np.sqrt(np.mean(final**2))),'line_residuals_px':final.tolist(),
           'normalized_jacobian_singular_values':singular.tolist(),
           'normalized_jacobian_condition':float(singular[0]/singular[-1]),
           'jacobian_rank_at_1e_7':int(np.sum(singular > singular[0]*1e-7)),
           'free_parameters':len(p),'predicted_corners':projection(p,xyz,mode).tolist()}
    if mode == 'orthographic':
        out['local_camera'] = {'azimuth_deg':float(np.degrees(p[0])), 'elevation_deg':float(np.degrees(p[1]))}
    else:
        expanded = expanded_fixed(p) if mode == 'fixed35' else p
        out.update(parameters=expanded.tolist(),local_camera=local_direction(expanded),
                   optical_axis_azimuth_deg=float(np.degrees(expanded[0])),optical_axis_elevation_deg=float(np.degrees(expanded[1])),
                   distance_ldu=float(np.exp(expanded[3])),focal_pixels=float(np.exp(expanded[4])),
                   principal_point=expanded[7:9].tolist(),near_distance_bound=bool(np.exp(expanded[3])>1e7))
    return out

def multistart(xyz, observations, mode):
    center = np.mean([p for e in observations for p in e['line_samples']],axis=0)
    starts = []
    if mode == 'orthographic':
        for az,el in [(35,35),(30,40),(40,30)]:
            initial = np.r_[np.radians([az,el]),0,np.log(.8),center]
            starts.append(optimize(initial,xyz,observations,mode))
    else:
        for distance in [300,1000,4000,20000]:
            initial = np.r_[np.radians([35,35]),0,np.log(distance),np.log(distance*.8)]
            initial = np.r_[initial,center] if mode == 'fixed35' else np.r_[initial,0,0,center]
            starts.append(optimize(initial,xyz,observations,mode))
    return min(starts,key=lambda s:s['line_rms_px']),starts

def samples_from_pixels(edge, factor):
    pixels = np.array(edge['pixels']) * [1,factor]
    center = pixels.mean(0)
    _,_,vt = np.linalg.svd(pixels-center)
    t = vt[0]
    coordinate = (pixels-center) @ t
    # Two representative positions on each observed TLS line. Equal weight per
    # edge; more raster pixels do not count as independent camera measurements.
    lo, hi = np.quantile(coordinate,[.1,.9])
    return {'edge':edge['edge'],'line_samples':(center+np.array([lo,hi])[:,None]*t).tolist(),
            'native_pixel_count':len(pixels),'observed_span_px':float(hi-lo)}

def synthetic_controls():
    results = []
    for nx in [6,10]:
        g = geometry(nx)
        for distance in [500,4000]:
            truth = np.r_[np.radians([35,35]),.01,np.log(distance),np.log(distance*.8),0,0,80,50]
            uv = predict(truth,g)
            observations = []
            for edge in EDGES:
                a,b = uv[[ord(c)-65 for c in edge]]
                observations.append({'edge':edge,'line_samples':[ (.2*a+.8*b).tolist(),(.8*a+.2*b).tolist()]})
            modes = {}
            for mode in ['perspective','fixed35','orthographic']:
                best,starts = multistart(g,observations,mode)
                modes[mode] = {'best':best,'starts':starts}
            assert modes['perspective']['best']['line_rms_px'] < 1e-5
            for key in ['azimuth_deg','elevation_deg']:
                assert abs(modes['perspective']['best']['local_camera'][key]-35) < .01
            assert modes['fixed35']['best']['line_rms_px'] < 1e-5
            assert modes['orthographic']['best']['line_rms_px'] > .01
            results.append({'nx':nx,'distance':distance,'truth':truth.tolist(),'observations':observations,'modes':modes})
            print('synthetic',nx,distance,'PASS',flush=True)
    return results

