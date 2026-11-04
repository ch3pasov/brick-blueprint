"""Model -> projected scene -> visible vector paths -> compact SVG/PDF."""
from pathlib import Path
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from . import __version__
from .native import build
from .project import project
from .optimize import optimize
from .compact_paths import compact
from .pdf import export_pdf
from .png import check_png_dpi, export_png
from .presets import get_preset, rgb_hex
from .presentation import decorate

def render(model, library, output, *, cache_dir='.brickblueprint-cache', timeout=300, preset=None, layout='illustration', quantity=1, panel_role=None, underpaint=False, png_dpi=None, **options):
    check_png_dpi(png_dpi)
    if not isinstance(underpaint, bool):raise ValueError('underpaint must be a boolean')
    if layout not in ('illustration','callout'):raise ValueError('Unknown layout')
    if not isinstance(quantity,int) or isinstance(quantity,bool) or quantity<1:raise ValueError('Quantity must be a positive integer')
    presentation=None
    if preset or layout=='callout':
        presentation=get_preset(preset or 'creator-blue')
        if options.get('background') is not None:
            presentation['page_background']='#'+''.join(f'{v:02X}' for v in options['background'])
        options['background']=rgb_hex(presentation['page_background'])
        options.setdefault('line_width',presentation['illustration_line_width_pt'])
        if layout=='callout':
            role=panel_role or presentation['default_panel_role'];fill=presentation['panels'].get(role)
            if fill is None:raise ValueError('No measured '+role+' panel in this preset')
            if role=='parts' and not presentation.get('show_quantity_labels',True) and quantity!=1:
                raise ValueError('This preset shows one icon per piece; use a tray of quantity-1 items')
            options['background']=rgb_hex(fill)
            w,h=options.get('width',600),options.get('height',450)
            inset=12+presentation['panel_padding_pt'];label=presentation['count_font_pt']+10
            options['viewport']=(inset,inset,w-2*inset,h-2*inset-label)
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Output directory already exists; choose a new output directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    binaries,execution=build(cache_dir,with_receipt=True)
    with tempfile.TemporaryDirectory(prefix='.brick-blueprint-',dir=output.parent) as tmp:
        temp=Path(tmp);scene=temp/'model.scene';raw=temp/'raw.svg';union=temp/'union.svg'
        receipt=project(model,library,scene,**options)
        with (temp/'render.log').open('w') as log:
            subprocess.run([str(binaries['vector']),str(scene),str(raw)],check=True,stdout=log,stderr=log,timeout=timeout)
        with (temp/'union.log').open('w') as log:
            completed=subprocess.run([str(binaries['union']),str(raw),str(union),'1000'],check=True,stdout=subprocess.PIPE,stderr=log,text=True,timeout=timeout)
        union_audit=json.loads(completed.stdout)
        if union_audit['probe_mismatches']:raise RuntimeError('Polygon union winding probes failed')
        with redirect_stdout(io.StringIO()):
            optimize('optimized',1000,source=union,output_dir=temp)
        source_svg=temp/'optimized.svg'
        if underpaint:
            masks=temp/'underpaint.svg'
            generated=subprocess.run([str(binaries['union']),'--underpaint',str(scene),str(masks)],
                                     check=True,capture_output=True,text=True,timeout=timeout)
            receipt['underpaint']={'method':'opaque-placement-footprints-v1', **json.loads(generated.stdout)}
            layer=ET.parse(masks).getroot()
            if len(layer):
                document=ET.parse(source_svg)
                faces=document.getroot().find('{*}g[@id="opaque-visible-faces"]')
                faces[:0]=list(layer)
                source_svg=temp/'underpainted.svg'
                document.write(source_svg,encoding='utf-8')
        with redirect_stdout(io.StringIO()):
            compact(source_svg,temp/'model.svg')
        root=ET.parse(temp/'model.svg').getroot()
        if any(n.tag.rsplit('}',1)[-1] in ('image','foreignObject','script') for n in root.iter()):raise RuntimeError('Unexpected non-vector SVG content')
        if presentation:
            receipt['presentation']=decorate(temp/'model.svg',presentation,layout,quantity,panel_role)
            receipt['presentation'].update(preset=preset or 'creator-blue',sources=presentation['sources'])
        pdf_audit=export_pdf(temp/'model.svg',temp/'model.pdf')
        receipt.update(version=__version__,execution=execution,optimization=union_audit,pdf=pdf_audit,
                       limits=['Illustration only; projection is recorded in camera, not physical assembly validation.',
                               'Object-opacity shell approximation; no refraction or light simulation.',
                               'Assembly-only MPD; embedded custom geometry, TEXMAP and model INVERTNEXT are rejected.'])
        final=temp/'result';final.mkdir()
        for name in ('model.svg','model.pdf'):
            os.replace(temp/name,final/name)
        if png_dpi is not None:
            receipt['png'] = export_png(final/'model.pdf', png_dpi)
        # No private input paths in portable receipts. DAT headers retain attribution.
        (final/'render.json').write_text(json.dumps(receipt,indent=2)+'\n')
        os.replace(final,output)
    return receipt
