"""Add native-vector presentation around an already projected illustration."""
import xml.etree.ElementTree as ET
NS='http://www.w3.org/2000/svg'

def panel_element(style,x,y,w,h,fill):
    """Coordinates are SVG units (two units per PDF point)."""
    attrs={'id':'presentation-panel','fill':fill,'stroke':style['panel_border'],'stroke-width':str(style['panel_stroke_pt']*2)}
    shape=style.get('panel_shape','rounded')
    if shape in ('rounded','square'):
        attrs.update(x=str(x),y=str(y),width=str(w),height=str(h),rx=str(0 if shape=='square' else style['panel_radius_pt']*2))
        return ET.Element(f'{{{NS}}}rect',attrs)
    c=min(style.get('panel_chamfer_pt',7.087)*2,w/2,h/2)
    if shape=='chamfer':points=[(x+c,y),(x+w-c,y),(x+w,y+c),(x+w,y+h-c),(x+w-c,y+h),(x+c,y+h),(x,y+h-c),(x,y+c)]
    elif shape=='opposite-chamfer':points=[(x+c,y),(x+w,y),(x+w,y+h-c),(x+w-c,y+h),(x,y+h),(x,y+c)]
    else:raise ValueError('Unknown panel shape')
    attrs['d']='M'+('L'.join(f'{a},{b}' for a,b in points))+'Z'
    return ET.Element(f'{{{NS}}}path',attrs)

def decorate(path,preset,layout,quantity=1,panel_role=None):
    root=ET.parse(path).getroot();_,_,w,h=map(float,root.attrib['viewBox'].split())
    background=next(n for n in root if n.tag==f'{{{NS}}}rect')
    background.set('fill',preset['page_background'])
    receipt={'layout':layout,'font_substitute':'Helvetica / browser sans-serif; not LEGOChalet60 or CeraPro'}
    if layout=='callout':
        role=panel_role or preset['default_panel_role'];color=preset['panels'].get(role)
        if color is None:raise ValueError('No measured '+role+' panel in this preset; choose a supported panel role')
        role_style={**preset,**preset.get('panel_role_overrides',{}).get(role,{})}
        inset=12.;padding=preset['panel_padding_pt'];stroke=role_style['panel_stroke_pt']
        panel=panel_element(role_style,inset*2,inset*2,w-inset*4,h-inset*4,color)
        root.insert(list(root).index(background)+1,panel)
        text=ET.SubElement(root,f'{{{NS}}}text',{'x':str(w/2),'y':str(h-2*(inset+padding)),
                  'text-anchor':'middle','fill':role_style.get('count_color','#181716'),'font-family':'Helvetica, Arial, sans-serif',
                  'font-size':str(preset['count_font_pt']*2),'font-weight':preset.get('count_font_weight','bold')})
        text.text=str(quantity)+'x' if role!='parts' or preset.get('show_quantity_labels',True) else ''
        if role=='parts' and not preset.get('show_quantity_labels',True):root.remove(text)
        receipt.update(panel_role=role,quantity=quantity,panel_fill=color,panel_radius_pt=preset['panel_radius_pt'],
                       panel_stroke_pt=stroke,panel_border=role_style['panel_border'],panel_shape=role_style.get('panel_shape','rounded'),count_font_pt=preset['count_font_pt'],count_color=role_style.get('count_color','#181716'))
    ET.register_namespace('',NS);ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return receipt
