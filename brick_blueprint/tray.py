"""Compose non-overlapping model views at one physical scale into a parts tray."""
from pathlib import Path
import hashlib
import json
import math
import os
import tempfile
import xml.etree.ElementTree as ET
from .pipeline import render
from .project import project
from .presets import get_preset, rgb_hex
from .pdf import export_pdf
from .png import check_png_dpi, export_png
from .presentation import panel_element
from . import __version__
from .camera_presets import resolve_camera

NS='http://www.w3.org/2000/svg'
XL='http://www.w3.org/1999/xlink'
LAYER_IDS={'opaque-visible-faces','depth-composited-ink','ordered-glass-cells',
           'depth-clipped-ink','original-endpoint-round-ink','original-endpoint-caps'}

def render_tray(manifest,library,output,*,preset='modern-blue',width=600,height=450,
                columns=3,gap=18,scale=None,line_width=.32,azimuth=None,elevation=None,
                glass_opacity=None,cache_dir='.brickblueprint-cache',timeout=300,
                projection=None,field_of_view=None,near_clip=None,
                style_path=None,material_profile=None,camera_preset=None,underpaint=False,png_dpi=None):
    check_png_dpi(png_dpi)
    if not isinstance(underpaint, bool):raise ValueError('underpaint must be a boolean')
    settings, _ = resolve_camera(camera_preset,projection=projection,azimuth=azimuth,
                                 elevation=elevation,field_of_view=field_of_view)
    default_az,default_el=settings['azimuth'],settings['elevation']
    source=Path(manifest).resolve();spec=json.loads(source.read_text())
    if not isinstance(spec,dict) or set(spec)!={'items'}:raise ValueError('Tray manifest requires only an items list')
    items=spec['items']
    if not isinstance(items,list) or not 1<=len(items)<=64:raise ValueError('A tray needs 1..64 items')
    if not isinstance(columns,int) or isinstance(columns,bool) or not 1<=columns<=64:raise ValueError('Columns must be between 1 and 64')
    columns=min(columns,len(items))
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (width,height,gap)):raise ValueError('Nonfinite tray dimensions')
    if not 64<=width<=1000 or not 64<=height<=1000 or gap<0:raise ValueError('Invalid tray dimensions or gap')
    if scale is not None and (not math.isfinite(scale) or scale<=0):raise ValueError('Scale must be positive')
    style=get_preset(preset)
    style={**style,**style.get('panel_role_overrides',{}).get('parts',{})}
    fill=style['panels']['parts']
    if fill is None:raise ValueError('This preset has no measured parts tray')
    normalized=[]
    for item in items:
        if not isinstance(item,dict) or set(item)-{'model','quantity','azimuth','elevation'} or 'model' not in item:raise ValueError('Each tray item needs a model and optional quantity/camera')
        count=item.get('quantity',1)
        if not isinstance(count,int) or isinstance(count,bool) or count<1:raise ValueError('Quantity must be a positive integer')
        if not style.get('show_quantity_labels',True) and count!=1:
            raise ValueError('This preset shows one icon per piece; use repeated quantity-1 items')
        if not isinstance(item['model'],str):raise ValueError('Model reference must be a string')
        model=(source.parent/item['model']).resolve()
        if not model.is_file():raise ValueError('Missing tray model: '+item['model'])
        for name in ('azimuth','elevation'):
            value=item.get(name,default_az if name=='azimuth' else default_el)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError('Tray camera angles must be finite numbers')
        normalized.append((model,count,item.get('azimuth',azimuth),item.get('elevation',elevation)))
    rows=math.ceil(len(items)/columns);inset=12;pad=style['panel_padding_pt'];label=style['count_font_pt']+10
    cw=(width-2*(inset+pad)-(columns-1)*gap)/columns
    ch=(height-2*(inset+pad)-(rows-1)*gap)/rows
    if cw<=0 or ch<=label+1:raise ValueError('Tray cells are too small')
    cells=[(inset+pad+(i%columns)*(cw+gap),inset+pad+(i//columns)*(ch+gap),cw,ch-label) for i in range(len(items))]
    target=Path(output).resolve()
    if target.exists():raise FileExistsError('Output directory already exists; choose a new output directory')
    target.parent.mkdir(parents=True,exist_ok=True)
    common=dict(width=width,height=height,line_width=line_width,background=rgb_hex(fill),glass_opacity=glass_opacity,
                projection=projection,field_of_view=field_of_view,near_clip=near_clip,
                style_path=style_path,material_profile=material_profile,camera_preset=camera_preset)
    with tempfile.TemporaryDirectory(prefix='.brick-tray-',dir=target.parent) as temp:
        T=Path(temp);fits=[]
        for i,((model,count,az,el),cell) in enumerate(zip(normalized,cells)):
            measured=project(model,library,T/f'measure-{i}.scene',azimuth=az,elevation=el,viewport=cell,detail_filter=False,**common)
            fits.append(measured['points_per_ldu'])
        shared=min(fits) if scale is None else scale
        if shared>min(fits)+1e-8:raise ValueError('At least one tray item does not fit at requested scale')
        root=ET.Element(f'{{{NS}}}svg',{'width':f'{width}pt','height':f'{height}pt','viewBox':f'0 0 {width*2} {height*2}'})
        ET.SubElement(root,f'{{{NS}}}rect',{'x':'0','y':'0','width':str(width*2),'height':str(height*2),'fill':style['page_background']})
        root.append(panel_element(style,inset*2,inset*2,(width-2*inset)*2,(height-2*inset)*2,fill))
        defs=ET.SubElement(root,f'{{{NS}}}defs');layers={};receipts=[]
        for i,((model,count,az,el),cell) in enumerate(zip(normalized,cells)):
            out=T/f'item-{i}'
            receipt=render(model,library,out,scale=shared,azimuth=az,elevation=el,viewport=cell,cache_dir=cache_dir,timeout=timeout,underpaint=underpaint,**common)
            asset=ET.parse(out/'model.svg').getroot();prefix=f'i{i}-'
            for node in asset.iter():
                if 'id' in node.attrib and node.tag!=f'{{{NS}}}g':node.set('id',prefix+node.get('id'))
                if f'{{{XL}}}href' in node.attrib:node.set(f'{{{XL}}}href','#'+prefix+node.get(f'{{{XL}}}href')[1:])
            for child in asset:
                tag=child.tag.rsplit('}',1)[-1]
                if tag=='defs':defs.extend(list(child))
                elif tag=='g':
                    key=child.get('id')
                    if key not in LAYER_IDS:raise RuntimeError('Unexpected SVG layer in tray composition')
                    if key not in layers:layers[key]=ET.SubElement(root,child.tag,dict(child.attrib))
                    # The views occupy disjoint cells; each shared layer can be concatenated.
                    layers[key].extend(list(child))
            x,y,w,h=cell
            text=ET.SubElement(root,f'{{{NS}}}text',{'x':str(2*(x+w/2)),'y':str(2*(y+h+label-2)),'text-anchor':'middle','fill':style.get('count_color','#181716'),'font-family':'Helvetica, Arial, sans-serif','font-size':str(style['count_font_pt']*2),'font-weight':style.get('count_font_weight','bold')})
            text.text=str(count)+'x' if style.get('show_quantity_labels',True) else ''
            if not style.get('show_quantity_labels',True):root.remove(text)
            receipts.append({'quantity':count,'viewport_pt':cell,'model_sha256':receipt['model_sha256'],'model_structure':receipt['model_structure'],'points_per_ldu':receipt['points_per_ldu'],'camera':receipt['camera'],'parts':receipt['parts'],'dependencies':receipt['dependencies'],'library_config':receipt['library_config'],'style_sha256':receipt['style_sha256'],'materials':receipt['materials']})
            if underpaint:
                receipts[-1]['underpaint']=receipt['underpaint']
        ET.register_namespace('',NS);ET.register_namespace('xlink',XL)
        final=T/'result';final.mkdir();svg=final/'model.svg';ET.ElementTree(root).write(svg,encoding='utf-8',xml_declaration=True)
        pdf=export_pdf(svg,final/'model.pdf')
        report={'version':__version__,'execution':receipt['execution'],'layout':'parts-tray','preset':preset,'sources':style['sources'],'manifest_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'page_points':[width,height],'columns':columns,'rows':rows,'points_per_ldu':shared,'line_width_points':line_width,'items':receipts,'pdf':pdf,'font_substitute':('Helvetica-Bold' if style.get('count_font_weight','bold')=='bold' else 'Helvetica')+' / browser sans-serif','count_color':style.get('count_color','#181716'),'limits':['One shared target-plane scale and perspective distance; per-item orientation/target may differ. Orthographic scale is uniform.','Grid composition only; no automatic part identification or step generation.']}
        report.update(item_count=len(receipts),
                      rendered_parts=sum(i['parts'] for i in receipts),
                      represented_parts=sum(i['parts']*i['quantity'] for i in receipts))
        if png_dpi is not None:
            report['png'] = export_png(final/'model.pdf', png_dpi)
        (final/'render.json').write_text(json.dumps(report,indent=2)+'\n');os.replace(final,target)
    return report
