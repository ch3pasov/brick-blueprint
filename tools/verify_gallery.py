"""Read-only byte/provenance comparison of the original kiosk gallery recipes.

No rendering, compilation, package installation or network access. This compares
saved outputs and their declared inputs; it does not authenticate arbitrary
receipts, visually render SVG/PDF, or certify the physical model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]


def matches_vector_source(actual, reference):
    if actual == reference:
        return True
    contract = json.loads((ROOT/'docs/research/RENDER-CONTRACT.json').read_bytes())
    return (actual == contract['active_package_source_sha256'] and
            reference == contract['vector_reference_package_source_sha256'])


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_file(root,name):
    path=Path(root)/name
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing regular file: '+name)
    root=Path(root).resolve()
    if not path.resolve().is_relative_to(root):
        raise ValueError('File escapes selected directory: '+name)
    if path.stat().st_size>20*1024*1024:
        raise ValueError('Gallery verification file is unexpectedly large: '+name)
    return path.read_bytes()


def read_json(root,name):
    value=json.loads(read_file(root,name))
    if not isinstance(value,dict):raise ValueError('Expected a JSON object: '+name)
    return value


def scene_names(values):
    if not isinstance(values,list) or not values or len(values)>100:
        raise ValueError('Invalid gallery scene inventory')
    if any(not isinstance(n,str) or not re.fullmatch('[a-z0-9][a-z0-9_-]*',n) for n in values):
        raise ValueError('Unsafe gallery scene identifier')
    if len(values)!=len(set(values)):raise ValueError('Duplicate gallery scene identifier')
    return values


def library_inputs(receipt):
    """Normalize an optional outer ldraw/ ZIP directory, retaining content hashes."""
    def key(name):
        name=name.replace('\\','/').lower()
        return name.removeprefix('ldraw/')
    def one(value):
        if not isinstance(value,dict):raise ValueError('Invalid gallery item receipt')
        rows={}
        for record in value.get('dependencies',[]):
            name=key(record['file']);hash_=record['sha256']
            if name in rows and rows[name]!=hash_:raise ValueError('Conflicting dependency revisions')
            rows[name]=hash_
        config=value.get('library_config')
        return dict(dependencies=rows,palette=(key(config['file']),config['sha256']) if config else None)
    return [one(item) for item in receipt.get('items',[receipt])]


def compare(*,showcase=None,presets=None,print_proof=None,reference=ROOT/'docs/gallery',previews=False):
    reference=Path(reference)
    if not any((showcase,presets,print_proof)):raise ValueError('Select at least one gallery output group')
    checks=[];notes=[]
    def check(item,actual,expected):
        checks.append(dict(item=item,match=actual==expected,actual=actual,expected=expected))
    def receipt(name,folder,expected_hash,actual_hash):
        # The recipe must bind its own saved raw receipt, including runtime details.
        raw=read_file(folder,'render.json');actual=read_json(folder,'render.json')
        expected=read_json(reference,name+'.json')
        check(name+'/recipe-to-receipt',digest(raw),actual_hash)
        check(name+'/reference-chain',expected['full_render_receipt_sha256'],expected_hash)
        for field in ('model_sha256','model_structure','manifest_sha256','page_points'):
            check(name+'/'+field,actual.get(field),expected.get(field))
        check(name+'/DAT-and-palette',library_inputs(actual),library_inputs(expected))
        source = actual['execution']['package_source_sha256']
        reference_source = expected['execution']['package_source_sha256']
        checks.append(dict(item=name+'/package-sources', actual=source, expected=reference_source,
                           match=matches_vector_source(source,reference_source)))
        if actual['execution']!=expected['execution']:
            notes.append(dict(scene=name,note='Runtime/toolchain details differ; inspect both receipts. Vector byte comparison remains explicit.'))
        for filename,field in (('model.svg','SVG_sha256'),('model.pdf','PDF_sha256')):
            sha=digest(read_file(folder,filename))
            check(name+'/'+filename+'/own-receipt',sha,actual['pdf'][field])
            check(name+'/'+filename+'/reference',sha,expected['pdf'][field])
        return actual

    if showcase:
        base=read_json(reference,'kiosk-showcase.json');current=read_json(showcase,'showcase.json')
        wanted=scene_names(base['scenes']);found=scene_names(current['scenes'])
        check('showcase/scene-inventory',found,wanted)
        for field in ('generator_sha256','recipe_sha256','models'):
            check('showcase/'+field,current[field],base[field])
        for name in found:
            if name not in wanted:continue
            receipt(name,Path(showcase)/name,base['render_receipts'][name],current['render_receipts'][name])
        if previews:
            expected=base['previews']['images'];actual=current.get('previews',{}).get('images',{})
            check('showcase/preview-inventory',sorted(actual),sorted(expected))
            for name in expected:
                if not re.fullmatch('kiosk-[a-z-]+[.]png',name):raise ValueError('Unsafe preview filename')
                sha=digest(read_file(showcase,name))
                check(name+'/own-receipt',sha,actual.get(name))
                check(name+'/reference',sha,expected[name])
    if presets:
        base=read_json(reference,'kiosk-presets.json');current=read_json(presets,'kiosk-presets.json')
        wanted=scene_names([r['preset'] for r in base['scenes']]);found=scene_names([r['preset'] for r in current['scenes']])
        check('presets/scene-inventory',found,wanted)
        for field in ('generator_sha256','recipe_sha256'):
            check('presets/'+field,current[field],base[field])
        by_name={r['preset']:r for r in base['scenes']}
        for row in current['scenes']:
            name=row['preset']
            if name not in by_name:continue
            expected=by_name[name]
            receipt('kiosk-preset-'+name,Path(presets)/name,expected['receipt_sha256'],row['receipt_sha256'])
            if previews:
                sha=digest(read_file(Path(presets)/name,'preview.png'))
                check('preset-'+name+'/preview-own-receipt',sha,row.get('preview_sha256'))
                check('preset-'+name+'/preview-reference',sha,expected.get('preview_sha256'))
        if previews:
            sha=digest(read_file(presets,'kiosk-presets.png'))
            check('presets/board-own-receipt',sha,current['previews']['board_sha256'])
            check('presets/board-reference',sha,base['previews']['board_sha256'])
    if print_proof:
        base=read_json(reference,'kiosk-print-comparison.json');current=read_json(print_proof,'comparison.json')
        wanted=scene_names(list(base['modes']));found=scene_names(list(current['modes']))
        check('print/mode-inventory',found,wanted)
        for field in ('recipe_sha256','source_svg_sha256'):
            check('print/'+field,current[field],base[field])
        for mode in found:
            if mode not in wanted:continue
            raw=read_file(Path(print_proof)/mode,'print.json');actual=read_json(Path(print_proof)/mode,'print.json')
            expected=read_json(reference,'kiosk-print-'+mode+'.json')
            check('print-'+mode+'/receipt',digest(raw),current['modes'][mode]['receipt_sha256'])
            check('print-'+mode+'/reference-chain',digest(read_file(reference,'kiosk-print-'+mode+'.json')),base['modes'][mode]['receipt_sha256'])
            for field in ('source_svg_sha256','page_points','page_mm','quantity_labels'):
                check('print-'+mode+'/'+field,actual[field],expected[field])
            sha=digest(read_file(Path(print_proof)/mode,'print.pdf'))
            check('print-'+mode+'/PDF-own-receipt',sha,actual['pdf']['PDF_sha256'])
            check('print-'+mode+'/PDF-reference',sha,expected['pdf']['PDF_sha256'])
            check('print-'+mode+'/conversion',actual['pdf']['color_export'],expected['pdf']['color_export'])
        if previews:
            sha=digest(read_file(print_proof,'kiosk-print-comparison.png'))
            check('print/board-own-receipt',sha,current['previews']['board_sha256'])
            check('print/board-reference',sha,base['previews']['board_sha256'])
    differences=[row for row in checks if not row['match']]
    return dict(status='MATCH' if not differences else 'MISMATCH',checks=len(checks),
                passed=len(checks)-len(differences),differences=differences,runtime_notes=notes,
                preview_byte_check=previews,read_only=True,
                limits=['Exact vector/optional PNG bytes and declared model/DAT/palette/package sources only.',
                        'Receipt hashes are consistency evidence, not digital signatures or proof of ownership.',
                        'No browser SVG/PDF visual rendering, physical-build acceptance or exhaustive security audit.',
                        'Byte differences across runtimes need separate pixel/geometry review; no tolerance silently clears them.'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--showcase',type=Path)
    p.add_argument('--presets',type=Path)
    p.add_argument('--print-proof',type=Path)
    p.add_argument('--reference',type=Path,default=ROOT/'docs/gallery')
    p.add_argument('--previews',action='store_true',help='Also require exact PNG bytes; no Pillow import')
    args=p.parse_args(argv)
    try:result=compare(**vars(args))
    except (ValueError,OSError,KeyError,TypeError) as error:p.exit(2,'Gallery verification failed: '+str(error)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['status']=='MATCH' else 1


if __name__=='__main__':raise SystemExit(main())
