from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from brick_blueprint.doctor import diagnose

ROOT = Path(__file__).resolve().parents[1]


class DoctorTests(unittest.TestCase):
    def test_default_and_preflight_do_not_compile_or_create_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)/'absent'
            with patch('brick_blueprint.doctor.build') as build:
                report = diagnose(library=ROOT/'examples/library',
                                  model=ROOT/'examples/demo.ldr', cache_dir=cache)
            build.assert_not_called()
            self.assertFalse(cache.exists())
            self.assertTrue(report['ready'])
            self.assertEqual(next(c for c in report['checks'] if c['name']=='model')['parts'], 13)

    def test_missing_compiler_and_invalid_libraries_are_structured_failures(self):
        with patch.dict(os.environ, {'CXX':'/missing/brick-blueprint-compiler'}):
            report = diagnose()
        self.assertFalse(report['ready'])
        self.assertFalse(next(c for c in report['checks'] if c['name']=='compiler')['ok'])
        with tempfile.TemporaryDirectory() as tmp:
            invalid = Path(tmp)/'bad.zip'
            invalid.write_text('This is not a library archive.')
            for library in (invalid, Path(tmp)/'missing'):
                report = diagnose(library=library, model=ROOT/'examples/demo.ldr')
                self.assertFalse(report['ready'])
                self.assertFalse(next(c for c in report['checks'] if c['name']=='library')['ok'])
                self.assertFalse(next(c for c in report['checks'] if c['name']=='model')['ok'])

    def test_cli_failure_exits_nonzero_without_traceback(self):
        run = subprocess.run([sys.executable,'-m','brick_blueprint','doctor',
                              '--library','missing-library.zip'],cwd=ROOT,
                             capture_output=True,text=True)
        self.assertEqual(run.returncode,1)
        self.assertFalse(json.loads(run.stdout)['ready'])
        self.assertNotIn('Traceback',run.stderr)
        run = subprocess.run([sys.executable,'-m','brick_blueprint','doctor',
                              '--model','examples/demo.ldr'],cwd=ROOT,
                             capture_output=True,text=True)
        self.assertEqual(run.returncode,1)
        self.assertIn('--model requires --library',run.stderr)

    def test_explicit_compile_builds_both_native_tools(self):
        # Real native compilation is exercised by rendering and installed-wheel
        # checks. This isolates opt-in dispatch and failure reporting.
        with patch('brick_blueprint.doctor.build',return_value={'vector':Path('v'),'union':Path('u')}) as build:
            report=diagnose(compile_native=True,cache_dir='chosen-cache')
        build.assert_called_once_with('chosen-cache')
        self.assertEqual(next(c for c in report['checks'] if c['name']=='native_build')['programs'],['union','vector'])
        with patch('brick_blueprint.doctor.build',side_effect=RuntimeError('C++17 rejected')):
            report=diagnose(compile_native=True)
        self.assertFalse(report['ready'])

    def test_optional_version_policy_does_not_change_core_readiness(self):
        for version,expected in [('12.3.0',False),('13.0.0',sys.version_info>=(3,11)),('13.0.0rc1',None)]:
            with patch('brick_blueprint.doctor.importlib.util.find_spec',return_value=object()), \
                 patch('brick_blueprint.doctor.metadata.version',return_value=version):
                report=diagnose()
            self.assertTrue(report['ready'])
            self.assertEqual(report['optional']['pillow_distribution_version'],version)
            self.assertIs(report['optional']['meets_declared_print_extra'],expected)


if __name__=='__main__':unittest.main()
