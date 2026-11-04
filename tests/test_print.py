from pathlib import Path
import hashlib,os,re,tempfile,unittest,zlib
from brick_blueprint.pdf import export_pdf
from brick_blueprint.print_colors import PrintColors
from brick_blueprint.print_export import export_print

SVG='''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="200pt" height="100pt" viewBox="0 0 400 200"><rect x="0" y="0" width="400" height="200" fill="#FFFFFF"/><defs><path id="empty" d=""/><path id="a" d="M0,0L80,0L80,80Z"/></defs><g id="opaque-visible-faces"><path fill="#FF0000" d="M10,10L100,10L100,100Z"/></g><g id="ordered-glass-cells"><g fill="none"><use xlink:href="#a" fill="#00FF00" fill-opacity="0.4"/></g></g><text x="150" y="150" fill="#181716" font-size="16" font-weight="bold" text-anchor="middle">2x</text></svg>'''

def streams(path):
    return [zlib.decompress(s) for s in re.findall(rb'stream\n(.*?)\nendstream',path.read_bytes(),re.S)]

class PrintTests(unittest.TestCase):
    def fixture(self,t):
        p=Path(t)/'model.svg';p.write_text(SVG);return p
    def test_gray_has_gray_operators_and_preserves_page_text_and_alpha(self):
        with tempfile.TemporaryDirectory() as t:
            src=self.fixture(t);before=src.read_bytes();out=Path(t)/'print'
            r=export_print(src,out,mode='gray');pdf=(out/'print.pdf').read_bytes();content=b'\n'.join(streams(out/'print.pdf'))
            self.assertIn(b'/DeviceGray',pdf);self.assertNotIn(b'/DeviceRGB',pdf);self.assertIn(b'0.4 /CA 0.4',pdf)
            self.assertIn(b'(2x) Tj',content);self.assertNotRegex(content,rb'\b(?:rg|RG)\b');self.assertNotIn(b'/Subtype /Image',pdf)
            self.assertEqual(r['page_points'],[200,100]);self.assertFalse(r['scale_changed']);self.assertEqual(src.read_bytes(),before)
            self.assertTrue((out/'print.json').is_file())
    def test_rgb_export_is_identical_to_normal_export(self):
        with tempfile.TemporaryDirectory() as t:
            src=self.fixture(t);normal=Path(t)/'normal.pdf';export_pdf(src,normal)
            out=Path(t)/'print';export_print(src,out,mode='rgb')
            self.assertEqual(normal.read_bytes(),(out/'print.pdf').read_bytes())
    def test_luminance_is_linear_light_not_channel_average(self):
        c=PrintColors('gray')
        self.assertAlmostEqual(c.convert('#000000')[0],0);self.assertAlmostEqual(c.convert('#FFFFFF')[0],1)
        self.assertAlmostEqual(c.convert('#FF0000')[0],.4984399236,places=8)
        self.assertGreater(c.convert('#00FF00')[0],c.convert('#FF0000')[0])
        self.assertGreater(c.convert('#FF0000')[0],c.convert('#0000FF')[0])
    def test_rejects_missing_or_wrong_profile_without_output(self):
        with tempfile.TemporaryDirectory() as t:
            src=self.fixture(t);out=Path(t)/'bad'
            with self.assertRaisesRegex(ValueError,'explicit'):export_print(src,out,mode='cmyk')
            self.assertFalse(out.exists())
            profile=Path(t)/'wrong.icc';profile.write_bytes(b'\0'*128)
            with self.assertRaisesRegex(ValueError,'CMYK output'):export_print(src,out,mode='cmyk',profile=profile)
            self.assertFalse(out.exists())
    def test_rejects_features_that_would_change_or_drop_content(self):
        changes=[('width="200pt"','width="400pt"'),('<rect ','<rect transform="scale(2)" '),('id="opaque-visible-faces"','id="unknown-layer"'),('M10,10L100,10L100,100Z','M10,10C100,10 100,100 10,100Z'),('fill-opacity="0.4"','fill-opacity="nan"')]
        with tempfile.TemporaryDirectory() as t:
            for i,(old,new) in enumerate(changes):
                src=Path(t)/f'{i}.svg';src.write_text(SVG.replace(old,new));out=Path(t)/f'out{i}'
                with self.assertRaises(ValueError):export_print(src,out,mode='gray')
                self.assertFalse(out.exists())
    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            src=self.fixture(t);out=Path(t)/'existing';out.mkdir();sentinel=out/'keep';sentinel.write_text('keep')
            with self.assertRaises(FileExistsError):export_print(src,out,mode='gray')
            self.assertEqual(sentinel.read_text(),'keep')
    @unittest.skipUnless(os.environ.get('BRICK_BLUEPRINT_TEST_CMYK_PROFILE'),'Optional real ICC integration profile not supplied')
    def test_real_icc_is_embedded_and_all_paint_uses_four_channels(self):
        profile=Path(os.environ['BRICK_BLUEPRINT_TEST_CMYK_PROFILE'])
        with tempfile.TemporaryDirectory() as t:
            src=self.fixture(t);out=Path(t)/'cmyk';r=export_print(src,out,mode='cmyk',profile=profile)
            pdf=(out/'print.pdf').read_bytes();data=streams(out/'print.pdf');self.assertIn(profile.read_bytes(),data)
            content=b'\n'.join(s for s in data if s!=profile.read_bytes())
            self.assertIn(b'/ICCBased',pdf);self.assertIn(b'/N 4',pdf);self.assertNotIn(b'/DeviceRGB',pdf)
            self.assertNotRegex(content,rb'\b(?:rg|RG|g|G)\b');self.assertIn(b'/CSPrint cs',content);self.assertIn(b'(2x) Tj',content)
            self.assertEqual(r['pdf']['color_export']['profile_sha256'],hashlib.sha256(profile.read_bytes()).hexdigest())
            self.assertEqual(r['pdf']['image_XObjects'],0)

if __name__=='__main__':unittest.main()
