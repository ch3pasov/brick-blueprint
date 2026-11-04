"""Create a separate print PDF from this renderer's existing vector output."""
from pathlib import Path
import hashlib
import json
import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from . import __version__
from .pdf import export_pdf
from .print_colors import PrintColors, channels

NS='{http://www.w3.org/2000/svg}'
XL='{http://www.w3.org/1999/xlink}href'
LAYERS={'opaque-visible-faces','depth-composited-ink','ordered-glass-cells','depth-clipped-ink','original-endpoint-round-ink','original-endpoint-caps'}
ATTRS={
 'svg':{'viewBox','width','height'},'title':set(),'defs':set(),
 'rect':{'x','y','width','height','rx','fill','stroke','stroke-width','id'},
 'path':{'d','fill','stroke','stroke-width','id'},
 'g':{'id','fill','stroke-width','stroke-linecap','stroke-linejoin'},
 'use':{XL,'fill','fill-opacity'},
 'text':{'x','y','text-anchor','fill','font-family','font-size','font-weight'},
 'circle':{'cx','cy','r','fill'},
}

def validate(source):
    p=Path(source)
    if not p.is_file() or p.stat().st_size>64*1024*1024:raise ValueError('Expected a renderer SVG file no larger than 64 MiB')
    data=p.read_bytes()
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('XML declarations/entities are not supported')
    try:root=ET.fromstring(data)
    except ET.ParseError as error:raise ValueError('Invalid SVG XML') from error
    if root.tag!=NS+'svg':raise ValueError('Expected a namespaced renderer SVG')
    try:
        x,y,w,h=map(float,root.attrib['viewBox'].split())
        if not all(math.isfinite(v) for v in (x,y,w,h)) or (x,y)!=(0,0) or not 0<w<=20000 or not 0<h<=20000:raise ValueError()
        # Our SVG convention is two internal units per PDF point. Never guess it.
        if root.attrib['width']!=f'{w/2:g}pt' or root.attrib['height']!=f'{h/2:g}pt':
            # Some tray outputs retain a decimal suffix.
            if not root.attrib['width'].endswith('pt') or not root.attrib['height'].endswith('pt') or float(root.attrib['width'][:-2])!=w/2 or float(root.attrib['height'][:-2])!=h/2:raise ValueError()
    except (KeyError,ValueError):raise ValueError('SVG must retain the renderer viewBox and matching physical point dimensions')
    for child in root:
        tag=child.tag.removeprefix(NS)
        if tag=='g' and child.get('id') not in LAYERS:raise ValueError('Unknown SVG rendering layer')
        if tag=='path' and child.get('id')!='presentation-panel':raise ValueError('Unsupported root-level SVG path')
        if tag not in {'title','defs','rect','path','text','g'}:raise ValueError('Unsupported root-level SVG element')
    for child in root:
        tag=child.tag.removeprefix(NS)
        if tag=='defs' and any(n.tag!=NS+'path' or set(n.attrib)!={'id','d'} or len(n) for n in child):raise ValueError('Unsupported SVG definitions')
        if tag=='g':
            layer=child.get('id')
            if layer=='ordered-glass-cells':
                if any(g.tag!=NS+'g' or set(g.attrib)-{'fill'} or any(u.tag!=NS+'use' or len(u) for u in g) for g in child):raise ValueError('Unsupported SVG transparency structure')
            else:
                expected='circle' if layer=='original-endpoint-caps' else 'path'
                if any(n.tag!=NS+expected or len(n) for n in child):raise ValueError('Unsupported SVG layer contents')
        elif tag not in ('defs',) and len(child):raise ValueError('Unsupported nested SVG content')
    for n in root.iter():
        tag=n.tag.removeprefix(NS)
        if tag not in ATTRS or set(n.attrib)-ATTRS[tag]:raise ValueError('Unsupported SVG element or attributes: '+tag)
        if tag=='path' and ('d' not in n.attrib or re.search(r'[^MLZmlHVhvz0-9+.,\s-]',n.get('d',''))):raise ValueError('Unsupported SVG path commands')
        for name in ('x','y','width','height','rx','r','cx','cy','stroke-width','font-size','fill-opacity'):
            if name in n.attrib and tag!='svg':
                try:value=float(n.attrib[name])
                except ValueError:raise ValueError('Nonnumeric SVG dimension')
                if not math.isfinite(value):raise ValueError('Nonfinite SVG dimension')
                if name=='fill-opacity' and not 0<=value<=1:raise ValueError('Invalid SVG opacity')
        for name in ('fill','stroke'):
            if name in n.attrib and n.attrib[name]!='none':channels(n.attrib[name])
        if tag=='use' and not n.attrib.get(XL,'').startswith('#'):raise ValueError('Only local SVG form references are supported')
    return root,data

def export_print(source,output,*,mode,profile=None,intent='relative'):
    target=Path(output).resolve()
    if target.exists():raise FileExistsError('Output directory already exists; choose a new output directory')
    root,data=validate(source)
    colors=PrintColors(mode,profile=profile,intent=intent)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.brick-print-',dir=target.parent) as tmp:
        temp=Path(tmp);snapshot=temp/'source.svg';snapshot.write_bytes(data)
        final=temp/'result';final.mkdir()
        try:pdf=export_pdf(snapshot,final/'print.pdf',color_policy=colors)
        except (KeyError,AssertionError,IndexError) as error:raise ValueError('Unsupported or incomplete renderer SVG') from error
        w,h=pdf['page_points'];count_labels=sum(n.tag==NS+'text' for n in root.iter())
        notes=['Physical page size retained; print at 100% when dimensions matter.',
               'No automatic bleed, crop marks, imposition, trapping or PDF/X certification.',
               'Live vector transparency retained; appearance can change with the blending color space.']
        if count_labels:notes.append('Quantity labels use standard unembedded Helvetica; strict press/font requirements need a separate preflight.')
        if mode=='gray':notes.append('DeviceGray is an uncalibrated grayscale export, not a target-printer proof.')
        if mode=='cmyk':notes.append('The selected profile defines the output condition; its suitability for the actual paper/press is not inferred. No profile is distributed with the tool.')
        report={'version':__version__,'operation':'print-export','source_svg_sha256':hashlib.sha256(data).hexdigest(),
                'page_points':[w,h],'page_mm':[w*25.4/72,h*25.4/72],'scale_changed':False,
                'quantity_labels':count_labels,'fonts_embedded':False if count_labels else None,
                'pdf':pdf,'notes':notes}
        (final/'print.json').write_text(json.dumps(report,indent=2)+'\n');os.replace(final,target)
    return report
