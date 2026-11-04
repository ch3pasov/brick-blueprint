"""Export a deterministic, checked source candidate; never publish anything.

The archive is a review artifact. Passing these checks is not a license grant,
an exhaustive secrets scan, or approval of the depicted designs.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import stat
import struct
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib

ROOT_FILES = {'.gitattributes', '.gitignore', 'README.md', 'CONTRIBUTING.md',
              'THIRD_PARTY_NOTICES.md', 'pyproject.toml', 'LICENSE', 'NOTICE'}
ROOT_DIRS = {'brick_blueprint', 'docs', 'examples', 'tests', 'tools', '.github'}
SKIP_ROOT = {'.git', '.brickblueprint-cache', '.venv', 'build', 'dist',
             'output', 'artifacts'}
SKIP_NAMES = {'__pycache__', '.DS_Store'}
SUFFIXES = {
    'brick_blueprint': {'.py', '.json', '.cpp', '.h'},
    'docs': {'.md', '.json', '.svg', '.png'},
    'examples': {'.py', '.json', '.ldr', '.mpd', '.dat'},
    'tests': {'.py'}, 'tools': {'.py', '.json'}, '.github': {'.yml', '.yaml'},
}
MANIFEST_NAME = 'CANDIDATE-MANIFEST.json'
PREFIX = 'brick-blueprint/'
MAX_BYTES = 100 * 1024 * 1024

DEFAULT_MAX = 2_000_000
# This research record keeps all 3,998 bootstrap fits in one replay file.
SIMULATIONS = 'docs/research/CAMERA-PVALUES.json'
SIMULATION_SIZE = 7_938_675
SIMULATION_HASH = '828a6fcc0d0a3621be7f4206f2acb82bc7bdd3829110f5d91d17bc09125a7a82'


# Only these specific, independently reviewed bytes may exceed the standard size.
PINNED_FILES = {
    SIMULATIONS: (SIMULATION_SIZE, SIMULATION_HASH, 'Bootstrap measurement file'),
    'docs/images/lighthouse-point.svg': (3_123_712, 'a5418d95b0fa52ef1f62963dc12f0ca74005bbb0313112aaef80665b738ff885', 'Lighthouse vector plate'),
}


def maximum_size(name):
    return PINNED_FILES[name][0] if name in PINNED_FILES else DEFAULT_MAX


def check_size(name, content):
    if len(content) > maximum_size(name):
        raise ValueError('Unexpected large file: ' + name)
    if name in PINNED_FILES:
        _, expected, label = PINNED_FILES[name]
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(label + ' differs from the reviewed bytes')


SVG_TAGS = {'svg', 'title', 'desc', 'g', 'defs', 'path', 'rect', 'circle',
            'ellipse', 'line', 'polyline', 'polygon', 'text', 'tspan',
            'use', 'clipPath'}
REQUIRED = {'README.md', 'pyproject.toml', 'docs/LICENSING.md',
            'THIRD_PARTY_NOTICES.md', 'docs/gallery/images.json',
            'brick_blueprint/native/vendor/Clipper2/PROVENANCE.json'}
SECRET_PATTERNS = (
    r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE ' + r'KEY-----',
    r'gh[pousr]_[A-Za-z0-9]{30,}',
    r'github_pat_[A-Za-z0-9_]{40,}',
    r'AKIA[A-Z0-9]{16}',
    r'xox[baprs]-[A-Za-z0-9-]{20,}',
    r'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}',
    r'/' + r'Users/[^/\s]+', r'/' + r'home/[^/\s]+',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or '\\' in name or ':' in name
            or any(p in {'', '.', '..'} for p in name.split('/'))):
        raise ValueError('Unsafe candidate path')
    return name


def allowed_file(name):
    parts = PurePosixPath(safe_name(name)).parts
    if any(p in SKIP_NAMES for p in parts):
        return False
    if any(p.startswith('.') and p not in {'.github', '.gitignore', '.gitattributes'} for p in parts):
        return False
    if len(parts) == 1:
        return name in ROOT_FILES
    if parts[0] not in ROOT_DIRS:
        return False
    if name == 'docs/research/face-colors.csv':
        return True
    return (PurePosixPath(name).suffix.lower() in SUFFIXES[parts[0]]
            or name == 'brick_blueprint/native/vendor/Clipper2/LICENSE')


def _collect(root):
    """Read only explicit source areas; never traverse skipped directories."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Source must be a directory')
    files = {}
    total = 0
    for folder, dirs, names in os.walk(root, followlinks=False):
        base = Path(folder).relative_to(root)
        keep = []
        for name in sorted(dirs):
            rel = base / name
            if name in SKIP_NAMES or (not base.parts and
                    (name in SKIP_ROOT or name.endswith('.egg-info'))):
                continue
            if (root / rel).is_symlink():
                raise ValueError('Symlink in candidate: ' + rel.as_posix())
            if not base.parts and name not in ROOT_DIRS:
                raise ValueError('Unreviewed source directory: ' + name)
            keep.append(name)
        dirs[:] = keep
        for name in sorted(names):
            rel = base / name
            if name in SKIP_NAMES or (not base.parts and name == MANIFEST_NAME):
                continue
            key = safe_name(rel.as_posix())
            path = root / rel
            if path.is_symlink() or not path.is_file():
                raise ValueError('Non-regular candidate file: ' + key)
            if not allowed_file(key):
                raise ValueError('Unreviewed distribution file: ' + key)
            if path.stat().st_size > maximum_size(key):
                raise ValueError('Candidate file exceeds its size limit: ' + key)
            data = path.read_bytes()
            total += len(data)
            if total > MAX_BYTES:
                raise ValueError('Candidate exceeds 100 MiB')
            files[key] = data
    if REQUIRED - files.keys():
        raise ValueError('Missing required candidate files: ' + ', '.join(sorted(REQUIRED-files.keys())))
    return files


def _png_metadata(data, name):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Invalid PNG: ' + name)
    offset = 8
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError('Truncated PNG: ' + name)
        length = struct.unpack('>I', data[offset:offset+4])[0]
        kind = data[offset+4:offset+8]
        if offset + length + 12 > len(data):
            raise ValueError('Truncated PNG chunk: ' + name)
        payload=data[offset+8:offset+8+length]
        expected=struct.unpack('>I',data[offset+8+length:offset+12+length])[0]
        if zlib.crc32(kind+payload) != expected:
            raise ValueError('PNG chunk checksum differs: ' + name)
        if kind in {b'tEXt', b'zTXt', b'iTXt', b'eXIf'}:
            raise ValueError('Unreviewed PNG metadata: ' + name)
        offset += length + 12
        if kind == b'IEND':
            if offset != len(data):
                raise ValueError('Trailing PNG payload: ' + name)
            return
    raise ValueError('Missing PNG end: ' + name)


def validate(files):
    """Validate the exact bytes being exported, with bounded privacy checks."""
    if REQUIRED - files.keys():
        raise ValueError('Missing required candidate files')
    if sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError('Candidate exceeds 100 MiB')
    links = 0
    for name, data in files.items():
        if not allowed_file(name):
            raise ValueError('Unreviewed distribution file: ' + name)
        check_size(name, data)
        if name.endswith('.png'):
            _png_metadata(data, name)
            continue
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError as error:
            raise ValueError('Unexpected non-UTF8 source: ' + name) from error
        language_text = json.dumps(json.loads(text), ensure_ascii=False) if name.endswith('.json') else text
        if re.search(r'[\u0400-\u052f]', name + language_text):
            raise ValueError('Non-English text in publication source: ' + name)
        if name.endswith('.dat') and not text.startswith('0 Original synthetic rendering fixture\n'):
            raise ValueError('Unexpected external DAT geometry: ' + name)
        # The existing bounded scanner declares these exact regex literals.
        # Remove only the patterns themselves, never actual matched values.
        scanned = text.replace("r'" + SECRET_PATTERNS[-2] + "'", '')
        scanned = scanned.replace("r'" + SECRET_PATTERNS[-1] + "'", '')
        if any(re.search(pattern, scanned) for pattern in SECRET_PATTERNS):
            raise ValueError('Private path or credential-like content in ' + name)
        if name.endswith('.svg'):
            if b'<!doctype' in data.lower() or b'<!entity' in data.lower():
                raise ValueError('Unreviewed SVG declarations: ' + name)
            root = ET.fromstring(data)
            if root.tag != '{http://www.w3.org/2000/svg}svg':
                raise ValueError('Expected namespaced SVG: ' + name)
            for element in root.iter():
                if element.tag.rsplit('}', 1)[-1] not in SVG_TAGS:
                    raise ValueError('Unreviewed SVG element: ' + name)
                for key, value in element.attrib.items():
                    if key.rsplit('}', 1)[-1].lower() in {'style','base'}:
                        raise ValueError('Unreviewed SVG styling/base: ' + name)
                    if key.rsplit('}', 1)[-1] == 'href' and not value.startswith('#'):
                        raise ValueError('External SVG reference: ' + name)
                    if 'url(' in value.lower() and not re.fullmatch(r'''url\(\s*['"]?\#[^()\s'"]+['"]?\s*\)''',value,re.I):
                        raise ValueError('External SVG paint/reference: ' + name)
                    if key.lower().startswith('on'):
                        raise ValueError('SVG event handler: ' + name)
        if name.endswith('.md'):
            for target in re.findall(r'\]\(([^)]+)\)', text):
                if '://' in target or target.startswith(('#', 'mailto:')):
                    continue
                target = urllib.parse.unquote(target.split('#', 1)[0]).strip('<>')
                if not target:
                    continue
                if target.startswith('/') or '\\' in target:
                    raise ValueError('Absolute or nonportable local link: ' + name)
                # Normalize relative references without touching the filesystem.
                parts = list(PurePosixPath(name).parent.parts)
                for piece in target.split('/'):
                    if piece == '..':
                        if not parts:
                            raise ValueError('Link leaves candidate: ' + name)
                        parts.pop()
                    elif piece not in {'', '.'}:
                        parts.append(piece)
                joined = '/'.join(parts)
                if joined not in files and not any(p.startswith(joined+'/') for p in files):
                    raise ValueError('Broken local link in ' + name + ': ' + target)
                links += 1
    portfolio_file = 'docs/portfolio/sources.json'
    if portfolio_file in files:
        portfolio = json.loads(files[portfolio_file])
        vectors = {'docs/portfolio/cover.svg': portfolio['cover_sha256']}
        for model in portfolio['models']:
            vectors['docs/portfolio/' + safe_name(model['id']) + '.svg'] = model['svg_sha256']
            if sha(files[safe_name(model['model'])]) != model['model_sha256']:
                raise ValueError('Portfolio model hash differs: ' + model['id'])
        tray_index = json.loads(files['docs/portfolio/trays.json'])
        for tray in tray_index:
            manifest = safe_name(tray['manifest'])
            items = json.loads(files[manifest])['items']
            wrappers = [str(PurePosixPath(manifest).parent / safe_name(item['model'])) for item in items]
            if [sha(files[path]) for path in wrappers] != tray['model_sha256']:
                raise ValueError('Portfolio tray input differs: ' + manifest)
            vectors['docs/portfolio/' + safe_name(tray['preset']) + '.svg'] = tray['svg_sha256']
        if set(vectors) != {p for p in files if p.startswith('docs/portfolio/') and p.endswith('.svg')}:
            raise ValueError('Portfolio SVG inventory differs')
        for path, expected in vectors.items():
            if path not in files or sha(files[path]) != expected:
                raise ValueError('Portfolio vector hash differs: ' + path)
    if 'docs/gallery/crossing-gate.json' in files:
        for pose in json.loads(files['docs/gallery/crossing-gate.json'])['poses']:
            for field in ('model', 'drawing'):
                name = safe_name(pose[field])
                if sha(files[name]) != pose[field + '_sha256']:
                    raise ValueError('Crossing gate ' + field + ' differs from its pose record: ' + name)
    if 'docs/gallery/kiosk-showcase.json' in files:
        for stage in ('01', '04', '08'):
            name = 'kiosk-stage-' + stage
            receipt = json.loads(files['docs/gallery/' + name + '.json'])
            if sha(files['docs/images/' + name + '.svg']) != receipt['pdf']['SVG_sha256']:
                raise ValueError('Kiosk stage illustration differs from its native render: ' + name)
    vendor = 'brick_blueprint/native/vendor/Clipper2/'
    provenance = json.loads(files[vendor+'PROVENANCE.json'])
    for name, expected in provenance['files'].items():
        key = vendor + safe_name(name)
        if key not in files or sha(files[key]) != expected:
            raise ValueError('Pinned vendor file differs: ' + name)
    assets = json.loads(files['docs/gallery/images.json'])['assets']
    names = set()
    for asset in assets:
        name = safe_name(asset['file'])
        if name in names:
            raise ValueError('Duplicate gallery asset: ' + name)
        names.add(name)
        if name not in files or sha(files[name]) != asset['sha256']:
            raise ValueError('Gallery image hash differs: ' + name)
        for receipt in asset['renders'] + asset.get('print_exports', []):
            key = 'docs/gallery/' + safe_name(receipt) + '.json'
            if key not in files:
                raise ValueError('Missing gallery receipt: ' + receipt)
    if {name for name in files if name.endswith('.png')} != names:
        raise ValueError('PNG inventory differs from gallery manifest')
    return {'files_checked': len(files), 'local_links_checked': links,
            'gallery_images_checked': len(assets),
            'vendor_files_checked': len(provenance['files']),
            'scope': 'Explicit source areas, file types, known credential/private-path patterns, PNG metadata, SVG references, local links, image provenance and pinned vendor hashes. Not exhaustive security or legal clearance.'}


def manifest(files):
    rows = [{'path': key, 'bytes': len(data), 'sha256': sha(data)}
            for key, data in sorted(files.items())]
    return {'schema_version': 1, 'kind': 'source candidate for owner review',
            'publication_authorized': False,
            'source_tree_sha256': sha(json_bytes(rows)), 'files': rows,
            'checks': validate(files)}


def verify(archive):
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive member')
        if sum(i.file_size for i in infos) > MAX_BYTES:
            raise ValueError('Archive exceeds 100 MiB expanded')
        for item in infos:
            safe_name(item.filename)
            if not item.filename.startswith(PREFIX):
                raise ValueError('Unexpected archive root')
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Archive contains a symlink')
        record = json.loads(z.read(PREFIX+MANIFEST_NAME))
        rows = record['files']
        expected = {PREFIX+safe_name(row['path']) for row in rows}
        if len(expected) != len(rows) or set(names) != expected | {PREFIX+MANIFEST_NAME}:
            raise ValueError('Archive inventory differs from manifest')
        files = {}
        for row in rows:
            data = z.read(PREFIX+row['path'])
            if len(data) != row['bytes'] or sha(data) != row['sha256']:
                raise ValueError('Archive file differs: ' + row['path'])
            files[row['path']] = data
        if manifest(files) != record:
            raise ValueError('Candidate manifest is inconsistent')
    return {'archive_sha256': sha(Path(archive).read_bytes()),
            'source_tree_sha256': record['source_tree_sha256'],
            'files_verified': len(rows), 'publication_authorized': False}


def export(root, output):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output already exists; choose a new directory')
    files = _collect(root)
    record = manifest(files)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.candidate-', dir=output.parent) as temp:
        result = Path(temp)/'result'
        result.mkdir()
        archive = result/'brick-blueprint-source-candidate.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9) as z:
            content = dict(files)
            content[MANIFEST_NAME] = json_bytes(record)
            for name, data in sorted(content.items()):
                info = zipfile.ZipInfo(PREFIX+name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        report = verify(archive)
        (result/'candidate-manifest.json').write_bytes(json_bytes(record))
        (result/'export-report.json').write_bytes(json_bytes(report))
        # Reserve the destination exclusively, including against a racing
        # process creating an empty directory. Each hard link is exclusive too.
        # A filesystem failure can leave an incomplete new output for inspection;
        # an existing directory or file is never replaced.
        output.mkdir()
        for path in sorted(result.iterdir()):
            os.link(path, output/path.name)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path, help='New local directory; never uploaded')
    mode.add_argument('--check', action='store_true', help='Check source without writing')
    mode.add_argument('--verify', type=Path, help='Verify a source-candidate ZIP')
    args = parser.parse_args(argv)
    try:
        result = (verify(args.verify) if args.verify else
                  validate(_collect(args.source)) if args.check else
                  export(args.source, args.output))
    except (ValueError, OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        parser.exit(1, 'Candidate check failed: '+str(error)+'\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
