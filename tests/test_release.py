"""Distribution boundaries: verify exported bytes, not ignored working files."""
from pathlib import Path
import importlib.util
import json
import os
import struct
import tempfile
import unittest
import zipfile
import zlib

SPEC = importlib.util.spec_from_file_location(
    'export_candidate', Path(__file__).resolve().parents[1]/'tools/export_candidate.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base/'source'
        self.root.mkdir()
        self.put('README.md', '# Example\n[Rights](docs/LICENSING.md)\n')
        self.put('pyproject.toml', '[project]\nname="example"\n')
        self.put('THIRD_PARTY_NOTICES.md', 'Test fixture\n')
        self.put('docs/LICENSING.md', 'Owner review pending.\n')
        self.put('docs/gallery/images.json', '{"assets": []}\n')
        self.put('brick_blueprint/native/vendor/Clipper2/PROVENANCE.json', '{"files": {}}\n')

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, data):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)
        return path

    def exported(self, name='one'):
        output = self.base/name
        report = release.export(self.root, output)
        return output/'brick-blueprint-source-candidate.zip', report

    def test_exact_source_archive_is_deterministic_after_mtime_change(self):
        first, a = self.exported()
        for path in self.root.rglob('*'):
            if path.is_file():
                os.utime(path, (1_000_000_000, 1_000_000_000))
        second, b = self.exported('two')
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(a, b)
        self.assertEqual(a['files_verified'], 6)
        self.assertFalse(a['publication_authorized'])
        self.assertEqual(release.verify(first), a)
        with zipfile.ZipFile(first) as z:
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in z.infolist()))

    def test_dev_caches_and_git_are_excluded_without_reading(self):
        token = 'gh' + 'p_' + 'A'*36
        for folder in ['.git', '.brickblueprint-cache', 'dist', 'build', 'output',
                       'artifacts', '.venv', 'example.egg-info', 'tests/__pycache__']:
            self.put(folder+'/private.txt', token)
        self.put('.DS_Store', b'private metadata')
        archive, report = self.exported()
        self.assertEqual(report['files_verified'], 6)
        with zipfile.ZipFile(archive) as z:
            self.assertNotIn(token.encode(), b''.join(z.read(n) for n in z.namelist()))

    def test_exported_checkout_reexports_with_identical_source_bytes(self):
        first, _ = self.exported()
        unpacked=self.base/'unpacked'
        with zipfile.ZipFile(first) as z:
            z.extractall(unpacked)
        target=self.base/'reexport'
        release.export(unpacked/'brick-blueprint', target)
        self.assertEqual(first.read_bytes(), (target/'brick-blueprint-source-candidate.zip').read_bytes())

    def test_existing_empty_or_nonempty_output_is_never_overwritten(self):
        output = self.base/'existing'
        output.mkdir()
        with self.assertRaises(FileExistsError):
            release.export(self.root, output)
        (output/'keep').write_bytes(b'preserve')
        with self.assertRaises(FileExistsError):
            release.export(self.root, output)
        self.assertEqual((output/'keep').read_bytes(), b'preserve')

    def test_unreviewed_files_directories_and_external_geometry_fail_before_output(self):
        for name, data in [('notes.txt', 'private'), ('.env', 'private'),
                           ('docs/source.pdf', 'private'), ('private/data.json', '{}'),
                           ('examples/library/parts/foreign.dat', '0 External geometry\n')]:
            path = self.put(name, data)
            with self.subTest(name=name), self.assertRaises(ValueError):
                release.export(self.root, self.base/'failed')
            self.assertFalse((self.base/'failed').exists())
            path.unlink()
            if name.startswith('private/'):
                path.parent.rmdir()

    def test_secret_patterns_do_not_print_matched_values(self):
        for value in ['gh'+'p_'+'A'*36, '/'+'Users/'+'private-owner/file',
                      '-----BEGIN '+'PRIVATE '+'KEY-----']:
            self.put('README.md', value)
            with self.assertRaises(ValueError) as error:
                release.export(self.root, self.base/'failed')
            self.assertNotIn(value, str(error.exception))
            self.assertFalse((self.base/'failed').exists())

    def test_symlink_file_and_directory_are_rejected(self):
        outside = self.base/'outside'
        outside.mkdir()
        (outside/'private.md').write_text('private')
        for name, target in [('docs/link.md', outside/'private.md'), ('docs/link', outside)]:
            path = self.root/name
            path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'Symlink|Non-regular'):
                release.export(self.root, self.base/'failed')
            path.unlink()

    def test_local_links_must_resolve_inside_exact_export(self):
        for target in ['docs/missing.md', '../outside.md', '/absolute.md', '/README.md']:
            self.put('README.md', '[link]('+target+')\n')
            with self.subTest(target=target), self.assertRaises(ValueError):
                release.export(self.root, self.base/'failed')

    def test_vendor_hash_is_checked_against_exported_bytes(self):
        self.put('brick_blueprint/native/vendor/Clipper2/LICENSE', 'original notice')
        self.put('brick_blueprint/native/vendor/Clipper2/PROVENANCE.json',
                 json.dumps({'files': {'LICENSE': release.sha(b'original notice')}}))
        self.exported()
        self.put('brick_blueprint/native/vendor/Clipper2/LICENSE', 'changed notice')
        with self.assertRaisesRegex(ValueError, 'vendor'):
            self.exported('changed')

    def png(self, metadata=False):
        def chunk(kind, data):
            return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
        image = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        if metadata:
            image += chunk(b'tEXt', b'Comment\0private metadata')
        return image+chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00'))+chunk(b'IEND', b'')

    def test_gallery_hash_and_png_metadata_are_separate_gates(self):
        data = self.png()
        path = self.put('docs/images/sample.png', data)
        def image_manifest(payload):
            self.put('docs/gallery/images.json', json.dumps({'assets': [
                {'file': 'docs/images/sample.png', 'sha256': release.sha(payload), 'renders': []}]}))
        image_manifest(data)
        self.exported()
        path.write_bytes(self.png(metadata=True))
        image_manifest(path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'PNG metadata'):
            self.exported('metadata')
        path.write_bytes(data)
        image_manifest(b'wrong')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.exported('wrong')

    def test_escaped_non_english_json_is_checked_before_export(self):
        self.put('docs/sample.json', json.dumps({'label': chr(0x0410) * 4}))
        with self.assertRaisesRegex(ValueError, 'Non-English text'):
            self.exported()

    def test_size_exception_is_bound_to_reviewed_measurement_bytes(self):
        self.put(release.SIMULATIONS, '{}')
        with self.assertRaisesRegex(ValueError, 'Bootstrap measurement'):
            self.exported()
        with self.assertRaisesRegex(ValueError, 'Lighthouse vector plate'):
            release.check_size('docs/images/lighthouse-point.svg', b'replacement bytes')

    def test_svg_external_content_is_rejected(self):
        for content in ['<image href="https://example.com/a.png"/>',
                        '<use href="https://example.com/a.svg"/>',
                        '<script/>', '<style>@import "https://example.com/a.css";</style>',
                        '<animate/>', '<path onload="alert(1)"/>',
                        '<path fill="url(https://example.com/a.svg)"/>',
                        '<path style="fill:red"/>',
                        '<g xml:base="https://example.com/"><use href="#a"/></g>']:
            self.put('docs/images/specimen.svg', '<svg xmlns="http://www.w3.org/2000/svg">'+content+'</svg>')
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.exported()

    def test_png_checksum_failure_is_independent_of_manifest_hash(self):
        data=bytearray(self.png())
        data[29] ^= 1  # Corrupt the IHDR CRC, then record the changed file hash.
        self.put('docs/images/sample.png', bytes(data))
        self.put('docs/gallery/images.json', json.dumps({'assets': [
            {'file':'docs/images/sample.png','sha256':release.sha(data),'renders':[]}]}))
        with self.assertRaisesRegex(ValueError,'checksum'):
            self.exported()

    def test_archive_tampering_extra_members_and_duplicates_are_rejected(self):
        archive, _ = self.exported()
        with zipfile.ZipFile(archive) as z:
            entries = {name: z.read(name) for name in z.namelist()}
        for mode in ['changed', 'extra', 'duplicate']:
            path = self.base/(mode+'.zip')
            with zipfile.ZipFile(path, 'w') as z:
                for name, data in entries.items():
                    z.writestr(name, b'tampered' if mode == 'changed' and name.endswith('/README.md') else data)
                if mode == 'extra':
                    z.writestr(release.PREFIX+'private.txt', 'private')
                if mode == 'duplicate':
                    # Append a duplicate directly; suppress zipfile's expected warning.
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore', UserWarning)
                        z.writestr(next(iter(entries)), b'duplicate')
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                release.verify(path)

    def test_unsafe_manifest_references_cannot_escape_candidate(self):
        self.put('brick_blueprint/native/vendor/Clipper2/PROVENANCE.json',
                 json.dumps({'files': {'../outside': '0'*64}}))
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.exported()

    def test_handmade_manifest_cannot_authorize_unreviewed_archive_paths(self):
        files = release._collect(self.root)
        files['.env'] = b''
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            release.manifest(files)


if __name__ == '__main__':
    unittest.main()
