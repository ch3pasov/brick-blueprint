"""Re-evaluate the descriptive FOV sweep from saved 3D cameras and source points.
NumPy only. This checks numeric replay, not a new independent calibration.
Use the gallery recipe plus an external DAT library to regenerate the vectors.
"""
from pathlib import Path
import argparse,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def project(camera,xyz):
 if camera['projection']=='orthographic':
  return np.array(camera['offset_points'])+camera['points_per_ldu']*np.c_[xyz@camera['right'],xyz@camera['down']]
 v=xyz-np.array(camera['target_ldu']);q=camera['distance_ldu']-v@camera['direction']
 return np.array(camera['principal_point_points'])+camera['focal_length_points']*np.c_[v@camera['right'],v@camera['down']]/q[:,None]
def centroid(q):
 a=q;b=np.roll(q,-1,axis=0);cross=a[:,0]*b[:,1]-b[:,0]*a[:,1]
 return ((a+b)*cross[:,None]).sum(0)/(3*cross.sum())
def replay():
 data=json.loads((ROOT/'docs/research/CAMERA-STRENGTH.json').read_text());source=json.loads((ROOT/'docs/research/VOLUME-CAMERA-RESULTS.json').read_text());errors=[];count=0;theta=np.linspace(0,2*np.pi,256,endpoint=False);origin=np.array([0,12,0])
 for setting in data['results']:
  row=next(r for r in source['rows']if r['id']==setting['id']);caps=next(r for r in source['stud_validation']['results']if r['id']==setting['id']);body=project(setting['camera'],np.array(row['world_xyz'])+origin)
  predicted=np.array([centroid(project(setting['camera'],np.array(xyz)+origin+np.c_[6*np.cos(theta),np.zeros(256),6*np.sin(theta)]))for xyz in caps['world_stud_centers']])
  for comparison in setting['comparisons']:
   r=next(r for r in source['rows']if r['id']==setting['id'] and r['threshold']==comparison['edge_threshold']);measured=next(m for m in caps['measured']if m['threshold']==comparison['cap_threshold']);uv=np.array(r['points']);x=body-body.mean(0);y=uv-uv.mean(0);scale=(x*y).sum()/(x*x).sum();shift=uv.mean(0)-scale*body.mean(0)
   observed=np.array(measured['centers'])*[1,r['pixel_aspect_y_x']];rms=float(np.sqrt(np.mean(np.sum((scale*predicted+shift-observed)**2,1))));errors.append(abs(rms-comparison['cap_rms_px']));count+=1
 return {'status':'PASS' if max(errors)<1e-8 else'FAIL','comparisons':count,'maximum_numeric_difference_px':max(errors),'interpretation':data['selection'],'scope':'Saved camera and numeric source replay; not independent source validation or universal FOV recovery'}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();r=replay();s=json.dumps(r,indent=2)+'\n'
 if args.output:
  with args.output.open('x')as f:f.write(s)
 else:print(s,end='')
 raise SystemExit(r['status']!='PASS')
