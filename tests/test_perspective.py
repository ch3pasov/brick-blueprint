"""Pinhole geometry and independent ray/plane checks of vector visibility."""
from pathlib import Path
import json, re, subprocess, tempfile, unittest
import xml.etree.ElementTree as ET
from brick_blueprint.camera import PerspectiveCamera
from brick_blueprint.project import project
from brick_blueprint.native import build
from brick_blueprint.tray import render_tray
ROOT=Path(__file__).resolve().parents[1]
NS='{http://www.w3.org/2000/svg}';XL='{http://www.w3.org/1999/xlink}href'

def camera(vertices, **options):
    settings=dict(field_of_view=90,camera_distance=100,camera_target=(0,0,0));settings.update(options)
    return PerspectiveCamera(vertices,(1,0,0),(0,1,0),(0,0,1),200,200,(0,0,200,200),**settings)

def sample(root,x,y):
    def inside(d):
        poly=[]
        for m in re.finditer(r'([MLZ])([^MLZ]*)',d):
            op,value=m.groups()
            if op!='Z':poly.append(tuple(map(float,value.split(','))));continue
            if all((poly[(i+1)%len(poly)][0]-a[0])*(y-a[1])-(poly[(i+1)%len(poly)][1]-a[1])*(x-a[0])>=-1e-7 for i,a in enumerate(poly)):return True
            poly=[]
        return False
    def rgb(text):return tuple(int(text[i:i+2],16) for i in (1,3,5))
    result=[255.]*3;defs={p.get('id'):p.get('d') for p in root.findall(NS+'defs/'+NS+'path')}
    for g in root:
        if g.tag!=NS+'g':continue
        if g.get('id') in ('opaque-visible-faces','depth-composited-ink'):
            for p in g:
                if inside(p.get('d')):result=list(rgb(p.get('fill')))
        elif g.get('id')=='ordered-glass-cells':
            for group in g:
                for p in group:
                    if inside(defs[p.get(XL)[1:]]):
                        alpha=float(p.get('fill-opacity'));result=[(1-alpha)*a+alpha*b for a,b in zip(result,rgb(p.get('fill')))]
    return result

class PerspectiveTests(unittest.TestCase):
    def test_true_pinhole_magnification(self):
        c=camera([(-10,-20,0),(10,20,50)])
        self.assertEqual(c.project((0,0,0)),(100.,100.,0.))
        for a,b in zip(c.project((10,20,50)),(120.,140.,100.)):self.assertAlmostEqual(a,b)
        self.assertEqual(c.receipt()['projection'],'perspective');self.assertAlmostEqual(c.points_per_ldu,1)
        self.assertAlmostEqual(c.project((10,0,50))[0]-c.project((-10,0,50))[0],40)
    def test_depth_is_affine_on_projected_triangle(self):
        vs=[(-20,-20,0),(20,-20,40),(0,20,-20)];c=camera(vs);qs=[c.project(v) for v in vs];weights=(.2,.3,.5)
        world=tuple(sum(w*v[k] for w,v in zip(weights,vs)) for k in range(3));p=c.project(world)
        sw=[w*(100-v[2])/(100-world[2]) for w,v in zip(weights,vs)]
        for k in range(3):self.assertAlmostEqual(p[k],sum(w*q[k] for w,q in zip(sw,qs)),places=10)
        self.assertGreater(abs(sum(w*v[2] for w,v in zip(sw,vs))-world[2]),5)
    def test_conditional_controls(self):
        c=camera([(-10,-10,0),(10,10,0)]);edge=[(-10,0,0),(10,0,0)]
        self.assertFalse(c.conditional_visible(edge+[(0,2,20),(0,-2,-20)]))
        self.assertTrue(c.conditional_visible(edge+[(0,2,20),(0,2,-20)]))
        self.assertTrue(c.conditional_visible(edge+[(0,2,101),(0,-2,-20)]))
    def test_validation_no_silent_clipping(self):
        for opt in ({'field_of_view':0},{'field_of_view':float('nan')},{'camera_distance':0},{'near_clip':0},{'camera_distance':10},{'camera_target':(0,float('nan'),0)},{'scale':1}):
            with self.subTest(opt=opt), self.assertRaises(ValueError):camera([(-20,-20,0),(20,20,10)],**opt)
        with self.assertRaisesRegex(ValueError,'near plane'):camera([(0,0,100)])
        with self.assertRaisesRegex(ValueError,'does not fit'):camera([(200,0,0)])
    def test_fit_and_reference_scale(self):
        vs=[(-80,-20,0),(10,30,15)];c=camera(vs,camera_distance=None);d=camera(vs,camera_distance=None,scale=c.points_per_ldu)
        self.assertAlmostEqual(c.distance,d.distance)
        for v in vs:
            for p in c.project(v)[:2]:self.assertTrue(-1e-8<=p<=200+1e-8)
        for a,b in zip(c.project(vs[0]),d.project(vs[0])):self.assertAlmostEqual(a,b)
    def test_legacy_scene_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=project(ROOT/'examples/demo.ldr',ROOT/'examples/library',Path(tmp)/'old.scene',projection='orthographic',material_profile='legacy',elevation=30)
            self.assertEqual(r['scene_sha256'],'c0d8b62ef738ee3f70c664313a0f1f088e66a1221b5a67fa080fef12a6eb457e')
            with self.assertRaisesRegex(ValueError,'require perspective'):project(ROOT/'examples/demo.ldr',ROOT/'examples/library',Path(tmp)/'bad',projection='orthographic',field_of_view=30)
    def test_shared_tray_camera_distance(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);m=d/'tray.json';m.write_text(json.dumps({'items':[{'model':str(ROOT/'examples/demo.ldr')},{'model':str(ROOT/'examples/demo.ldr'),'azimuth':110}]}))
            r=render_tray(m,ROOT/'examples/library',d/'out',width=400,height=220,columns=2,cache_dir=ROOT/'.brickblueprint-cache');cams=[i['camera'] for i in r['items']]
            self.assertTrue(all(c['projection']=='perspective' for c in cams));self.assertEqual(cams[0]['distance_ldu'],cams[1]['distance_ldu']);self.assertEqual(r['pdf']['image_XObjects'],0)

class PerspectiveVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.exe=build(ROOT/'.brickblueprint-cache')['vector']
    def render_planes(self,planes,lines=(),reverse=False):
        faces=[]
        for owner,(a,b,c,rgb,alpha) in enumerate(planes):
            vs=[(x,y,a*x+b*y+c) for x,y in [(-30,-30),(30,-30),(30,30),(-30,30)]]
            for ids in ((0,1,2),(0,2,3)):faces.append((owner,rgb,alpha,[vs[i] for i in ids]))
        c=camera([p for *_,vs in faces for p in vs])
        if reverse:faces.reverse()
        rows=['800 800 255 255 255 '+str(len(faces))]
        for owner,rgb,alpha,vs in faces:
            qs=[c.project(p) for p in vs];rows.append(' '.join(map(str,[owner,*rgb,alpha,*(v for x,y,z in qs for v in (4*x,4*y,z))])))
        rows.append(str(len(lines))+' 1.2')
        for owner,rgb,vs in lines:
            qs=[c.project(p) for p in vs];rows.append(' '.join(map(str,[owner,*rgb,*(v for x,y,z in qs for v in (4*x,4*y,z))])))
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp);(t/'s').write_text('\n'.join(rows)+'\n');subprocess.run([str(self.exe),str(t/'s'),str(t/'o')],check=True,capture_output=True);return ET.parse(t/'o').getroot()
    def test_intersecting_surfaces_against_rays(self):
        planes=[(.7,.1,0,(220,0,0),1),(-.6,-.1,3,(0,30,220),1)]
        for reverse in (False,True):
            root=self.render_planes(planes,reverse=reverse)
            for u,v in [(-15,-9),(-8,7),(0,0),(7,4),(14,-7)]:
                q=[(100-c)/(1+a*u/100+b*v/100) for a,b,c,*_ in planes];expected=planes[min(range(2),key=lambda i:q[i])][3]
                self.assertEqual(sample(root,2*(100+u),2*(100+v)),list(expected))
    def test_glass_order_against_rays(self):
        planes=[(0,0,-35,(100,100,100),1),(.7,0,0,(250,250,250),.4),(-.6,0,3,(240,200,40),.6)]
        for reverse in (False,True):
            root=self.render_planes(planes,reverse=reverse)
            for u in (-15,-8,7,14):
                q=[(100-c)/(1+a*u/100) for a,b,c,*_ in planes];expected=[255.]*3
                for i in sorted(range(3),key=lambda i:q[i],reverse=True):
                    alpha=planes[i][4];expected=[(1-alpha)*x+alpha*y for x,y in zip(expected,planes[i][3])]
                actual=sample(root,2*(100+u),201.3);self.assertLess(max(abs(a-b) for a,b in zip(actual,expected)),.51)
    def test_slanted_surface_clips_line(self):
        r=self.render_planes([(.7,0,0,(220,0,0),1)],[(1,(0,0,0),[(-20,0,0),(20,0,0)])])
        self.assertEqual(sample(r,170,200),[0,0,0]);self.assertEqual(sample(r,230,200),[220,0,0])
if __name__=='__main__':unittest.main()
