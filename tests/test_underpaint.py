"""Base paint stays inside an opaque frame and leaves the original vector layers intact."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from xml.etree import ElementTree as ET

from brick_blueprint.compact_paths import expand
from brick_blueprint.pipeline import render
from brick_blueprint.tray import render_tray


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.brickblueprint-cache'


class UnderpaintTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.library = self.work / 'library'
        shutil.copytree(ROOT / 'examples/library', self.library)
        # Four coplanar quads around a real, through-opening.
        vertices = [
            (-20,-20,20,-20,10,-10,-10,-10), (20,-20,20,20,10,10,10,-10),
            (20,20,-20,20,-10,10,10,10), (-20,20,-20,-20,-10,-10,-10,10),
        ]
        lines = ['0 Frame with a square opening', '0 BFC CERTIFY CCW']
        for quad in vertices:
            points = ' '.join(f'{x} {y} 0' for x,y in zip(quad[::2],quad[1::2]))
            lines.append('4 16 '+points)
        (self.library/'parts/frame.dat').write_text('\n'.join(lines)+'\n')

    def model(self, color, part):
        path = self.work / (part+'.ldr')
        path.write_text(f'0 Surface fixture\n1 {color} 0 0 0 1 0 0 0 1 0 0 0 1 {part}.dat\n')
        return path

    def draw(self, model, output, **kwargs):
        return render(model, self.library, self.work/output, cache_dir=CACHE,
                      width=160, height=160, azimuth=0, elevation=0, **kwargs)

    def test_opaque_frame_retains_its_actual_opening(self):
        model = self.model(4,'frame')
        plain = self.draw(model,'plain')
        painted = self.draw(model,'painted',underpaint=True)
        self.assertEqual(plain['scene_sha256'],painted['scene_sha256'])
        self.assertEqual(painted['underpaint']['placement_masks'],1)
        self.assertEqual(painted['pdf']['image_XObjects'],0)
        xml = lambda folder: ET.parse(self.work/folder/'model.svg').getroot()
        faces = lambda root: root.find('{*}g[@id="opaque-visible-faces"]')
        first, second = faces(xml('plain')), faces(xml('painted'))
        self.assertEqual([p.attrib for p in first], [p.attrib for p in second][1:])
        # The two rectangular contours of the base must enclose the center
        # with opposite signed winding, so its hole transmits the page color.
        paths = []
        for cmd in expand(second[0].attrib['d']):
            if cmd[0]=='M': paths.append([])
            if cmd[0]!='Z': paths[-1].append(cmd[1:])
        self.assertEqual(len(paths),2)
        windings = []
        center = 160_000_000
        for pts in paths:
            winding = 0
            for (x,y),(u,v) in zip(pts,pts[1:]+pts[:1]):
                cross = (u-x)*(center-y)-(v-y)*(center-x)
                if y <= center < v and cross > 0: winding += 1
                if v <= center < y and cross < 0: winding -= 1
            windings.append(winding)
        self.assertEqual(sorted(windings),[-1,1])

    def test_glass_only_export_has_no_extra_paint(self):
        model = self.model(47,'unit-box')
        self.draw(model,'plain')
        under = self.draw(model,'painted',underpaint=True)
        self.assertEqual(under['underpaint']['placement_masks'],0)
        for name in ('model.svg','model.pdf'):
            self.assertEqual((self.work/'plain'/name).read_bytes(),(self.work/'painted'/name).read_bytes())

    def test_tray_records_each_items_underpaint(self):
        model = self.model(4,'frame')
        manifest = self.work/'parts.json'
        manifest.write_text(json.dumps({'items':[{'model':model.name,'quantity':2}]}))
        receipt = render_tray(manifest,self.library,self.work/'tray',cache_dir=CACHE,
                              underpaint=True,width=200,height=160,azimuth=0,elevation=0)
        self.assertEqual(receipt['items'][0]['underpaint']['placement_masks'],1)
        self.assertEqual(receipt['represented_parts'],2)
        self.assertEqual(receipt['pdf']['image_XObjects'],0)
