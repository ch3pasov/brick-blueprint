"""Independent controls for the research-only RGB conversion experiment."""
import sys,unittest
from pathlib import Path
try:
 import numpy as np
except ImportError:
 np=None
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
if np is not None:
 import analyze_ldraw_transfer as law

@unittest.skipIf(np is None,'Optional NumPy research dependency')
class RGBTransferTests(unittest.TestCase):
 def test_known_gains_recover_three_faces(self):
  x=np.array([[20,40,60],[30,50,80],[40,90,120]],float)
  y=np.stack([x*.8,x*1.1,x*1.2],axis=1)
  for architecture in ('direct','chain'):
   m=law.fit(dict(architecture=architecture,kind='gain',penalty=0),x,y)
   unseen=np.array([[25,55,110]],float)
   self.assertTrue(np.allclose(law.predict(m,unseen),np.stack([unseen*.8,unseen*1.1,unseen*1.2],axis=1),atol=1e-10))
 def test_identity_target_needs_no_residual_correction(self):
  x=np.array([[0,0,0],[255,255,255],[100,20,230],[0,200,100]],float);y=np.repeat(x[:,None,:],3,axis=1)
  for kind in law.KINDS:
   m=law.fit(dict(architecture='direct',kind=kind,penalty=.01),x,y)
   self.assertTrue(np.allclose(law.predict(m,x),y,atol=1e-10),kind)
 def test_clipping_is_on_output_channels(self):
  m=dict(architecture='direct',kind='gain',penalty=0,coefficients=[[2.],[.5],[1.]])
  self.assertEqual(law.predict(m,[[200,0,50]]).tolist(),[[[255.,0.,100.],[100.,0.,25.],[200.,0.,50.]]])
 def test_linear_light_roundtrip(self):
  x=np.array([0,.01,.04045,.18,.5,1.]);self.assertTrue(np.allclose(law.encode(law.decode(x)),x,atol=3e-8))
 def test_root_features_known_values(self):
  self.assertTrue(np.allclose(law.features(np.array([[.25,.64,.81]]),'root2'),[[.25,.64,.81,.4,.45,.72,1.]]))
 def test_outer_target_cannot_change_inner_model_selection(self):
  x=np.array([[20,40,60],[30,50,80],[40,90,120],[100,110,120],[220,230,210]],float)
  y=np.stack([x*.8,x*1.0,x*1.1],axis=1);changed=y.copy();changed[2]=255-y[2]
  a=law.nested(x,y)['folds'][2];b=law.nested(x,changed)['folds'][2]
  self.assertNotIn(2,a['training_indices']);self.assertEqual(a['selected'],b['selected']);self.assertEqual(a['model'],b['model']);self.assertEqual(a['prediction'],b['prediction']);self.assertNotEqual(a['observed'],b['observed'])
