"""Typeset the English research edition and its measurement tables from public source files."""
import argparse
import os
import tempfile
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image as PILImage
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, LongTable,
                                TableStyle, Flowable, Image, CondPageBreak, PageBreak, KeepTogether)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brick_blueprint.pdf import export_pdf

docs = ROOT / 'docs'
edition = json.loads((docs/'research/RENDER-CONTRACT.json').read_text())['preprint_version']
width, height = A4
measure = width - 102
overlays = []

def col(x):
    return colors.HexColor(x)

ink, blue, muted = '#193947', '#096986', '#4d6874'
def load_typefaces(font_dir):
    for family in ['Sans', 'Serif', 'Mono']:
        for weight in ['Regular','Bold','Italic','BoldItalic']:
            pdfmetrics.registerFont(TTFont(family + weight, str(font_dir / f'Liberation{family}-{weight}.ttf')))
        pdfmetrics.registerFontFamily(family+'Regular', normal=family+'Regular', bold=family+'Bold',
                                      italic=family+'Italic', boldItalic=family+'BoldItalic')


styles = {
    'title': ('SansBold', 29, 33, 12),
    'edition': ('SansRegular', 9.5, 13, 10),
    'h2': ('SansBold', 18.5, 23, 8),
    'h3': ('SansBold', 13, 17, 6),
    'p': ('SerifRegular', 11.6, 15, 7),
    'table': ('SansRegular', 8.7, 11.3, 0),
    'thead': ('SansBold', 8.7, 11.3, 0),
    'code': ('MonoRegular', 9, 12, 2),
    'note': ('SansRegular', 8.5, 11.6, 7),
}
styles = {key:ParagraphStyle(key,fontName=font,fontSize=sz,leading=leading,spaceAfter=after,
    textColor=col(ink),spaceBefore=8 if key in ('h2','h3') else 0, keepWithNext=key in ('h2','h3'),
    allowWidows=0, allowOrphans=0) for key,(font,sz,leading,after) in styles.items()}

def fmt(text):
    text = html.escape(text).replace('10⁻¹²','10<super>−12</super>')
    def link(match):
        label,url=match.groups()
        if url.startswith('https://'):
            return f'<link href="{url}" color="{blue}">{label}</link>'
        return f'<font color="{muted}">{label}</font>'
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    return re.sub(r'`([^`]+)`',r'<font name="MonoRegular">\1</font>',text)

def para(text, kind='p'):
    return Paragraph(fmt(text),styles[kind])


class Plot(Flowable):
    """The five research charts consist of text, rectangles, dots and straight paths."""
    def __init__(self,path,maxwidth):
        super().__init__()
        self.svg=ET.parse(path).getroot()
        _,_,self.vw,self.vh=map(float,self.svg.attrib['viewBox'].split())
        self.width=maxwidth
        self.height=self.width*self.vh/self.vw

    def draw(self):
        c=self.canv
        c.saveState()
        c.scale(self.width/self.vw,self.height/self.vh)
        for e in self.svg:
            a = e.attrib
            tag = e.tag.rsplit('}', 1)[-1]
            if tag in ('desc', 'title'):
                continue
            if 'fill' in a and a['fill']!='none':c.setFillColor(col(a['fill']))
            if 'stroke'in a:c.setStrokeColor(col(a['stroke']))
            c.setLineWidth(float(a.get('stroke-width',1)))
            if tag=='rect':
                x,y,w,h=[float(a[k]) for k in ('x','y','width','height')]
                c.rect(x,self.vh-y-h,w,h,stroke=0,fill=1)
            elif tag=='circle':
                c.circle(float(a['cx']),self.vh-float(a['cy']),float(a['r']),stroke=0,fill=1)
            elif tag=='line':
                c.line(float(a['x1']),self.vh-float(a['y1']),float(a['x2']),self.vh-float(a['y2']))
            elif tag=='text':
                c.setFont('SansRegular',float(a['font-size']))
                c.drawString(float(a['x']),self.vh-float(a['y']),e.text.replace('●','•'))
            elif tag=='polyline':
                path=c.beginPath()
                for i,point in enumerate(a['points'].split()):
                    x,y=map(float,point.split(','))
                    (path.lineTo if i else path.moveTo)(x,self.vh-y)
                c.drawPath(path,stroke=1,fill=0)
            else:
                raise ValueError('Unsupported chart element: ' + tag)
        c.restoreState()


class Comparison(Flowable):
    def __init__(self):
        super().__init__()
        self.width = measure
        self.height = 176
    def draw(self):
        c = self.canv
        w = 199
        h = w * 0.75
        c.setFont('SansBold',10);c.setFillColor(col(ink))
        c.drawString(0,h+10,'LDView 4.7')
        c.drawString(self.width-w,h+10,'Brick Blueprint')
        c.drawImage(ImageReader(str(docs/'images/plate-ldview.png')),0,0,w,h)
        x,y=c.absolutePosition(self.width-w,0)
        overlays.append(('images/plate-blueprint.svg', c.getPageNumber()-1, x, y, w))
        c.setFillColor(col(blue)); c.setFont('SansRegular',9)
        c.drawCentredString(self.width/2,h/2+6,'Official page')
        c.drawCentredString(self.width/2,h/2-8,'31051, step 8')
        c.linkURL('https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6167581.pdf#page=18',
                  (w+2,h/2-14,self.width-w-2,h/2+18),relative=1,thickness=0)

class TrayComparison(Flowable):
    """Three native paper styles, with the source labels from the Markdown table."""
    def __init__(self, block):
        super().__init__()
        self.width = measure
        self.gap = 7
        self.panel_width = (self.width - 2 * self.gap) / 3
        self.height = self.panel_width * 180 / 320 + 44
        lines = block.splitlines()
        self.titles = [s.strip() for s in lines[0].strip('|').split('|')]
        self.sources = [s.strip() for s in lines[-1].strip('|').split('|')]
        self.images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', lines[2])
        if len(self.images) != 3:
            raise ValueError('Expected three native parts panels')

    def draw(self):
        c = self.canv
        c.setFillColor(col(ink))
        for i, (image, title, source) in enumerate(zip(self.images, self.titles, self.sources)):
            left = i * (self.panel_width + self.gap)
            c.setFont('SansBold', 9)
            c.drawString(left, self.height - 12, title)
            x, y = c.absolutePosition(left, 18)
            overlays.append((image, c.getPageNumber()-1, x, y, self.panel_width))
            c.setFont('SansRegular', 8)
            c.drawString(left, 5, source)


def table(block):
    lines=[x.strip('|').split('|') for x in block.splitlines() if not re.fullmatch(r'[\s|:\-]+',x)]
    n=len(lines[0])
    weights={3:[.20,.31,.49],4:[.20,.38,.21,.21],5:[.15,.22,.21,.21,.21],
             6:([.23,.14,.12,.15,.18,.18] if 'Grid' in block.splitlines()[0] else [.24,.10,.16,.17,.16,.17])}[n]
    rows=[[para(cell.strip(),'thead' if i==0 else 'table') for cell in cells] for i,cells in enumerate(lines)]
    result=LongTable(rows,colWidths=[measure*v for v in weights],repeatRows=1,hAlign='LEFT')
    result.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),col('#dfedef')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,col('#f5f9fa')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),
            ('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),3.6),
            ('BOTTOMPADDING',(0,0),(-1,-1),3.6)]))
    return result

def blocks(text):
    text=re.sub(r'(?m)^(#{1,3} .+)$',r'\n\1\n',text)
    return [s.strip() for s in re.split(r'\n\s*\n',text) if s.strip()]

def story_for(source, appendix=False):
    result=[]
    for block in blocks(source):
        if block.startswith('# '):
            if appendix:
                result.append(PageBreak())
            result.append(para(block[2:],'h2' if appendix else 'title'))
        elif block.startswith('## '):
            heading = block[3:]
            if heading == '6. Comparison with LDView' or (appendix and heading in ('Inventory illustrations','Nominal RGB and measured faces')):
                result.append(PageBreak())
            if heading == '1. Perspective':
                result.append(Spacer(0, 8))
                result.append(para('Matched plate control', 'h3'))
                result.append(Comparison())
                result.append(para('Two views of DAT 3034 with the same 2° field of view and the same camera position. The study uses the official illustration as a visual reference.', 'note'))
                result.append(para('Reading the measurements', 'h3'))
                result.append(para('Start with the long chassis in section 1 to see the effect of depth. Section 2 uses the height of a brick to constrain camera direction. Section 3 separates palette conversion from measured face-to-face color transfer.', 'p'))
                result.append(PageBreak())
            result.extend([CondPageBreak(106),para(heading,'h2')])
        elif block.startswith('### '):
            result.extend([CondPageBreak(79),para(block[4:],'h3')])
        elif block.startswith('!['):
            m=re.fullmatch(r'!\[([^\]]+)\]\(([^)]+)\)',block)
            if m is None:
                raise ValueError('Expected a standalone Markdown figure: ' + block)
            img = docs / m[2]
            if img.suffix == '.svg':
                fig = Plot(img, measure)
            else:
                with PILImage.open(img) as bitmap:
                    ww, hh = bitmap.size
                fig=Image(str(img),width=measure,height=measure*hh/ww)
            result.append(KeepTogether([fig,Spacer(0,4),para(m[1]+'.','note')]))
        elif block.startswith('| Rounded panel |'):
            result.append(TrayComparison(block))
        elif block.startswith('| LDView 4.7'):
            result.append(Comparison())
        elif block.startswith('|'):
            result.extend([table(block),Spacer(0,8)])
        elif block.startswith('```'):
            for ln in block.splitlines()[1:-1]:result.append(para(ln,'code'))
            result.append(Spacer(0,7))
        else:
            kind='edition' if block.startswith('**Research preprint') else 'p'
            paragraph = para(' '.join(block.splitlines()), kind)
            if block.startswith('The table gives stud-center RMS'):
                paragraph.keepWithNext = True
            result.append(paragraph)
    return result

def page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(col(muted));canvas.setFont('SansRegular',8)
    canvas.drawString(51,height-34,'BRICK BLUEPRINT   /   RESEARCH EDITION '+edition)
    canvas.drawRightString(width-51,height-34,'METHODS AND MEASUREMENTS')
    canvas.setStrokeColor(col('#bbd0d8'));canvas.setLineWidth(.5)
    canvas.line(51,height-43,width-51,height-43)
    canvas.line(51,39,width-51,39)
    canvas.drawString(51,25,'Brick Blueprint   ·   English edition')
    canvas.drawRightString(width-51,25,str(doc.page))
    canvas.restoreState()

class Paper(SimpleDocTemplate):
    def afterFlowable(self, item):
        if isinstance(item, Paragraph) and item.style.name in ('h2','h3'):
            title = item.getPlainText()
            key = 'section-' + hashlib.sha256(title.encode()).hexdigest()[:20]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=int(item.style.name=='h3'), closed=False)

def build(directory):
    from reportlab import rl_config
    rl_config.invariant = True
    overlays.clear()
    layout = directory / 'layout.pdf'
    final = directory / 'paper.pdf'
    doc=Paper(str(layout),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=53,bottomMargin=50,
                          title='Perspective, viewing direction and surface color in brick instructions',
                          author='Brick Blueprint')
    manuscript=(docs/'RESEARCH-PREPRINT.md').read_text()
    appendix=(docs/'research/MEASUREMENT-TABLES.md').read_text()
    story = story_for(manuscript) + story_for(appendix, True)
    story.append(Spacer(0, 12))
    story.append(para('Typeset in Liberation Serif, Sans and Mono. The embedded typefaces are distributed under the SIL Open Font License 1.1. The tables accompany the machine-readable evidence in the source distribution.', 'note'))
    doc.build(story,onFirstPage=page,onLaterPages=page)
    if len(overlays) != 5:
        raise ValueError(f'Unexpected vector placements: {overlays}')
    # ReportLab typesets the page. The renderer provides original PDF paths for the plates.
    writer = PdfWriter(clone_from=PdfReader(layout))
    plates = {}
    for image, index, x, y, target_width in overlays:
        if image not in plates:
            native_file = directory / (Path(image).stem + '.pdf')
            export_pdf(docs / image, native_file)
            plates[image] = PdfReader(native_file).pages[0]
        native = plates[image]
        placement = Transformation().scale(target_width / float(native.mediabox.width)).translate(x, y)
        writer.pages[index].merge_transformed_page(native, placement, expand=False)
    with final.open('wb') as file:
        writer.write(file)
    return final


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-dir', required=True, type=Path,
                        help='Folder containing the Liberation Sans, Serif and Mono TrueType families')
    parser.add_argument('--output', required=True, type=Path, help='New PDF filename')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new PDF filename')
    load_typefaces(args.font_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as scratch:
        result = build(Path(scratch))
        os.link(result, args.output)
    print(args.output)

