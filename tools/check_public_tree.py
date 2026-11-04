"""Check the candidate source tree; not a general secrets scanner or legal audit."""
from pathlib import Path
import hashlib
import json
import re
from export_candidate import check_size

ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','__pycache__','.brickblueprint-cache','.venv','output','build','dist','artifacts'}
errors=[];files=[]
gallery=json.loads((ROOT/'docs/gallery/images.json').read_text())
image_manifest={a['file']:a for a in gallery['assets']}
for p in sorted(ROOT.rglob('*')):
    rel=p.relative_to(ROOT)
    if any(part in SKIP or part.endswith('.egg-info') for part in rel.parts):continue
    if p.is_symlink():errors.append(f'Symlink in candidate tree: {rel}');continue
    if not p.is_file():continue
    files.append(rel.as_posix())
    if p.suffix.lower() in ('.pdf','.zip','.ttf','.otf','.ttc','.icc','.icm','.pem','.key','.bin') or p.name.startswith('.env'):
        errors.append(f'Unexpected distribution asset: {rel}')
    try: check_size(rel.as_posix(), p.read_bytes())
    except ValueError as error: errors.append(str(error))
    if p.suffix.lower()=='.png':
        asset=image_manifest.get(rel.as_posix())
        if asset is None:errors.append(f'Image missing provenance: {rel}')
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=asset['sha256']:errors.append(f'Gallery image hash changed: {rel}')
        continue
    text=p.read_text(errors='replace')
    if p==Path(__file__).resolve():continue
    for pattern in (r'/Users/[^/\s]+',r'/home/[^/\s]+',r'PRIVATE KEY-----',r'gh[pousr]_[A-Za-z0-9]{30,}',r'AKIA[A-Z0-9]{16}'):
        if re.search(pattern,text):errors.append(f'Private path or credential-like content in {rel}')
    if p.suffix in ('.svg','.html') and re.search(r'<(?:\w+:)?(?:script|foreignObject|image)\b',text):
        errors.append(f'Unexpected active/raster content in {rel}')
vendor=ROOT/'brick_blueprint/native/vendor/Clipper2';provenance=json.loads((vendor/'PROVENANCE.json').read_text())
for rel,asset in image_manifest.items():
    if not (ROOT/rel).is_file():errors.append('Missing gallery image: '+rel)
    for name in asset['renders']+asset.get('print_exports',[]):
        if not (ROOT/'docs/gallery'/f'{name}.json').is_file():errors.append('Missing render receipt: '+name)
for name,expected in provenance['files'].items():
    if hashlib.sha256((vendor/name).read_bytes()).hexdigest()!=expected:errors.append('Vendor hash changed: '+name)
print(json.dumps({'files_checked':len(files),'vendor_files_verified':len(provenance['files']),
                  'errors':errors,'scope':'Known private-path/credential patterns, excluded asset types, SVG content and pinned vendor hashes only'},indent=2))
raise SystemExit(bool(errors))
