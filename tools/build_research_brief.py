"""Build the paired one-page brief; reject stale evidence or generated Markdown."""
from pathlib import Path
import argparse
import hashlib
import html
import json
from io import BytesIO
import os
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/research/RESEARCH-BRIEF.json'
MARKDOWN = ROOT / 'docs/RESEARCH-BRIEF.md'
SECTIONS = ROOT / 'docs/research/PREPRINT-SECTIONS.json'


def reference(q, sections=None):
    """Resolve page numbers from the full PDF's actual heading placements."""
    if not q.get('preprint_sections'):
        return q['reference'], None
    sections = sections or json.loads(SECTIONS.read_text())
    by_number = {}
    for entry in sections['sections']:
        by_number.setdefault(entry['number'], set()).add(entry['page'])
    pages = set()
    for number in q['preprint_sections']:
        if number not in by_number:
            raise ValueError(q['id'] + ': missing full-preprint section ' + number)
        pages.update(by_number[number])
    groups = []
    for page in sorted(pages):
        if groups and page == groups[-1][-1] + 1:
            groups[-1].append(page)
        else:
            groups.append([page])
    page_text = ', '.join(str(g[0]) if len(g) == 1 else f'{g[0]}–{g[-1]}' for g in groups)
    text = (q['section_label'] + ' · p. ' + page_text if len(pages) == 1
            else q['section_label'] + '; pp. ' + page_text)
    if q.get('extra_reference'):
        text += '; ' + q['extra_reference']
    return text, min(pages)


def markdown(data):
    parts = ['# ' + data['title'], data['subtitle'],
             '[Full study](RESEARCH-PREPRINT.md) · '
             '[Illustrated FAQ](FAQ.md)\n\n'
             'Each answer describes its measured sample.']
    for n, q in enumerate(data['questions'], 1):
        _, page = reference(q)
        evidence = f"[{q['reference']}]({q['doc']})"
        if page and q.get('paper_heading'):
            evidence += f" · [Paper, p. {page}](RESEARCH-PREPRINT.md#{q['paper_heading']})"
        parts.extend([f"## {n}. {q['question']}", q['answer'], evidence])
    return '\n\n'.join(parts) + '\n'


def consistency(data=None, check_markdown=True):
    data = data or json.loads(DATA.read_text())
    contract = json.loads((ROOT/'docs/research/RENDER-CONTRACT.json').read_text())
    errors = []
    for key in ('preprint_version', 'renderer_version'):
        if data[key] != contract[key]:
            errors.append(key + ': brief is stale')
    sections = json.loads(SECTIONS.read_text())
    if sections['preprint_version'] != data['preprint_version']:
        errors.append('Full-preprint section map is stale')
    if sections['page_count'] != data['full_preprint_pages']:
        errors.append('Full-preprint page count differs')
    if sections.get('edition') != 'English':
        errors.append('Expected the English paper section map')
    ids = [row['number'] for row in sections['sections']]
    if ids != [q['id'] for q in data['questions']] or len(ids) != len(set(ids)):
        errors.append('Expected one mapped evidence location per answer')
    for row in sections['sections']:
        if not row['text_anchor'] or not 1 <= row['page'] <= sections['page_count']:
            errors.append(row['number'] + ': invalid evidence location')
    if not data['source_hashes']:
        errors.append('No reviewed source hashes')
    for name, expected in data['source_hashes'].items():
        path = ROOT/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(name + ': changed since brief review')
    for q in data['questions']:
        if q.get('preprint_sections') != [q['id']] or not q.get('paper_heading'):
            errors.append(q['id'] + ': missing English paper reference')
        if not (ROOT/'docs'/q['doc']).is_file():
            errors.append(q['id'] + ': missing reference')
        try:
            reference(q, sections)
        except ValueError as exc:
            errors.append(str(exc))
    if not errors and check_markdown and (not MARKDOWN.exists() or MARKDOWN.read_text() != markdown(data)):
        errors.append('Generated brief Markdown differs')
    return errors


def check_pagination(pages, sections):
    """Each evidence phrase must occur on exactly its recorded English-paper page."""
    errors = []
    if len(pages) != sections['page_count']:
        errors.append('English paper page count differs')
    texts = [' '.join(page.split()) for page in pages]
    for row in sections['sections']:
        hits = [i for i, text in enumerate(texts, 1) if row['text_anchor'] in text]
        if hits != [row['page']]:
            errors.append(f"{row['number']}: expected page {row['page']}, found {hits}")
    return errors


def check_paper(path):
    from pypdf import PdfReader
    with Path(path).open('rb') as file:
        pages = [page.extract_text() for page in PdfReader(file).pages]
    return check_pagination(pages, json.loads(SECTIONS.read_text()))


def write_local_links(buffer, output, target, links):
    """Use a relative PDF GoToR action so the two files can travel together."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DictionaryObject, NameObject, NumberObject,
                               RectangleObject, TextStringObject)
    buffer.seek(0)
    writer = PdfWriter(clone_from=PdfReader(buffer))
    for rect, page in links:
        action = DictionaryObject({
            NameObject('/S'): NameObject('/GoToR'),
            NameObject('/F'): TextStringObject(target),
            NameObject('/D'): ArrayObject([NumberObject(page-1), NameObject('/Fit')]),
        })
        writer.add_annotation(0, DictionaryObject({
            NameObject('/Type'): NameObject('/Annot'),
            NameObject('/Subtype'): NameObject('/Link'),
            NameObject('/Rect'): RectangleObject(rect),
            NameObject('/Border'): ArrayObject([NumberObject(0)]*3),
            NameObject('/A'): action,
        }))
    with output.open('wb') as file:
        writer.write(file)


def pdf(data, output, font_dir, full_pdf=None):
    # Optional authoring dependency; the renderer and --check need no ReportLab.
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    sans = ('LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf')
    if not all((font_dir/file).is_file() for file in sans):
        sans = ('Arial.ttf', 'Arial Bold.ttf')
    for name, file in zip(('Brief', 'BriefBold'), sans):
        pdfmetrics.registerFont(TTFont(name, str(font_dir/file)))
    local = None
    if full_pdf and not urlsplit(full_pdf).scheme:
        paper = (output.parent/full_pdf).resolve()
        if paper == output.resolve():
            raise ValueError('Choose different files for the brief and companion paper')
        errors = check_paper(paper)
        if errors:
            raise ValueError('Invalid companion PDF: ' + ', '.join(errors))
        local = Path(os.path.relpath(paper, output.parent.resolve())).as_posix()
    pdfmetrics.registerFontFamily('Brief', normal='Brief', bold='BriefBold')
    width, height, margin = 595.276, 841.89, 38
    available = width - 2*margin
    body = ParagraphStyle('answer', fontName='Brief', fontSize=11.2,
                          leading=13.9, textColor=HexColor('#183744'))
    paragraphs = []
    for n, q in enumerate(data['questions'], 1):
        ref, first_page = reference(q)
        ref_markup = html.escape(ref)
        text = (f"<b>{n}. {html.escape(q['question'])}</b><br/>"
                f"{html.escape(q['answer'])} "
                f"<font size='8' color='#607783'>{ref_markup}</font>")
        paragraph = Paragraph(text, body)
        _, ph = paragraph.wrap(available, height)
        paragraphs.append((paragraph, ph, first_page))
    used = sum(ph for _, ph, _ in paragraphs) + 6*(len(paragraphs)-1)
    top, bottom = height-88, 45
    if used > top-bottom:
        raise ValueError(f'Brief needs {used:.1f} pt; available {top-bottom:.1f}. Shorten the prose.')
    output.parent.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height), pageCompression=1, invariant=1,
                      title=data['title'], author='Brick Blueprint research draft')
    c.setFillColor(HexColor('#183744')); c.setFont('BriefBold', 20)
    c.drawString(margin, height-37, data['title'])
    c.setFont('Brief', 9); c.setFillColor(HexColor('#607783'))
    c.drawString(margin, height-54, data['subtitle'] + ' · renderer ' + data['renderer_version'])
    c.drawString(margin, height-68, 'RGB differences are measured on the 0–255 channel scale.')
    y = top
    links = []
    for i, (paragraph, ph, first_page) in enumerate(paragraphs):
        paragraph.drawOn(c, margin, y-ph)
        if full_pdf and first_page:
            rect = (margin, y-ph, width-margin, y)
            if local:
                links.append((rect, first_page))
            else:
                c.linkURL(full_pdf+'#page='+str(first_page), rect, thickness=0)
        y -= ph + 6
        if i == 2:
            c.setStrokeColor(HexColor('#C5D7E0'));c.setLineWidth(.5)
            c.line(margin, y+2, width-margin, y+2)
    c.setStrokeColor(HexColor('#C5D7E0'));c.line(margin, 34, width-margin, 34)
    c.setFont('Brief', 8); c.setFillColor(HexColor('#607783'))
    footer = (f"Open the full paper · {data['full_preprint_pages']} pages. Select an answer above to open its source page."
              if full_pdf else f"English research paper · edition {data['preprint_version']}")
    c.drawString(margin, 21, footer)
    if full_pdf:
        rect = (margin, 16, width-margin, 30)
        if local:
            links.append((rect, 1))
        else:
            c.linkURL(full_pdf, rect, thickness=0)
    c.save()
    if local:
        write_local_links(buffer, output, local, links)
    else:
        output.write_bytes(buffer.getvalue())
    return {'page_count':1, 'body_height_pt':round(used, 2), 'body_font_pt':body.fontSize}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--pdf', type=Path)
    ap.add_argument('--font-dir', type=Path)
    ap.add_argument('--full-pdf', help='Companion PDF relative to the brief, or a public PDF URL')
    ap.add_argument('--check-paper', type=Path, help='Check all evidence destinations against a built English paper')
    args = ap.parse_args()
    data = json.loads(DATA.read_text())
    errors = consistency(data, check_markdown=args.check)
    if args.check_paper:
        errors.extend(check_paper(args.check_paper))
    if errors:
        raise SystemExit('\n'.join(errors))
    if not args.check:
        MARKDOWN.write_text(markdown(data))
    info = {'status':'PASS', 'questions':len(data['questions']), 'preprint_version':data['preprint_version']}
    if args.pdf:
        if not args.font_dir:
            ap.error('--pdf needs --font-dir with Liberation Sans or Arial regular and bold')
        info.update(pdf(data,args.pdf,args.font_dir,args.full_pdf))
    print(json.dumps(info))


if __name__ == '__main__':
    main()
