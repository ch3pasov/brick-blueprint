"""Read-only readiness checks; native compilation happens only when requested."""
import importlib.util
from importlib import metadata
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from . import __version__
from .ldraw import Library
from .native import build


def optional_status():
    available=importlib.util.find_spec('PIL') is not None
    version=None
    if available:
        try:version=metadata.version('Pillow')
        except metadata.PackageNotFoundError:pass
    stable=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:\.post\d+)?(?:\+[A-Za-z0-9_.-]+)?',version or '')
    meets=(sys.version_info>=(3,11) and tuple(map(int,stable.groups()))>=(13,0,0)) if stable else (False if not available else None)
    return dict(cmyk_pillow_available=available,pillow_distribution_version=version,
                declared_print_extra='Python 3.11+ and Pillow>=13.0',
                meets_declared_print_extra=meets)


def diagnose(*, library=None, model=None, compile_native=False,
             cache_dir='.brickblueprint-cache'):
    if model is not None and library is None:
        raise ValueError('--model requires --library')
    checks = []

    def add(name, ok, detail, **extra):
        checks.append(dict(name=name, ok=ok, detail=detail, **extra))

    add('python', sys.version_info >= (3, 10), platform.python_version(),
        required='3.10 or newer')
    compiler = os.environ.get('CXX') or shutil.which('clang++') or shutil.which('g++')
    if compiler:
        try:
            run = subprocess.run([compiler, '--version'], capture_output=True,
                                 text=True, timeout=30, check=True)
            lines = run.stdout.splitlines()
            add('compiler', True, lines[0] if lines else Path(compiler).name,
                cxx17_verified=False)
        except (OSError, subprocess.SubprocessError) as error:
            add('compiler', False, str(error))
    else:
        add('compiler', False, 'Install clang++ or g++ with C++17 support, or set CXX to its executable.')
    if library is not None:
        try:
            with Library(library) as lib:
                add('library', True, 'Readable directory or ZIP with LDConfig.ldr.',
                    colors=len(lib.colors), palette_sha256=lib.config_receipt['sha256'])
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
            add('library', False, str(error))
    if model is not None and all(c['ok'] for c in checks if c['name'] == 'library'):
        try:
            from .project import project
            with tempfile.TemporaryDirectory(prefix='brick-blueprint-doctor-') as tmp:
                receipt = project(model, library, Path(tmp)/'check.scene')
            add('model', True, 'Assembly and recursive geometry preflight passed.',
                parts=receipt['parts'], model_sha256=receipt['model_sha256'],
                dependencies=len(receipt['dependencies']))
        except (OSError, ValueError, RuntimeError, RecursionError) as error:
            add('model', False, str(error))
    elif model is not None:
        add('model', False, 'Not checked because the supplied library could not be read.')
    if compile_native:
        try:
            binaries = build(cache_dir)
            add('native_build', True, 'Both bundled C++17 programs compiled or matched the source cache.',
                programs=sorted(binaries))
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            add('native_build', False, str(error))
    return dict(version=__version__, ready=all(c['ok'] for c in checks), checks=checks,
                optional=optional_status(),
                limits=['Compiler version detection alone does not test C++17; use --compile.',
                        'Preflight does not validate physical connections, stability or source instructions.',
                        'No downloads or application launches; --compile writes only the selected native cache.'])
