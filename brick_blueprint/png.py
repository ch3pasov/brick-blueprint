"""Rasterize the finished RGB page, including its background and labels."""
from contextlib import closing
import hashlib
from importlib.util import find_spec
from pathlib import Path
from threading import Lock

# PDFium calls, including object cleanup, cannot overlap across threads.
_pdfium_lock = Lock()


def check_png_dpi(dpi):
    if dpi is None:
        return
    if type(dpi) is not int or not 1 <= dpi <= 600:
        raise ValueError('PNG resolution must be an integer from 1 to 600 DPI')
    if find_spec('pypdfium2') is None or find_spec('PIL') is None:
        raise RuntimeError('Install PNG support from the checkout with python -m pip install ".[png]"')


def export_png(pdf_path: Path, dpi: int):
    import pypdfium2 as pdfium

    output = pdf_path.with_suffix('.png')
    with _pdfium_lock, pdfium.PdfDocument(pdf_path) as document, closing(document[0]) as page:
        with closing(page.render(scale=dpi / 72, rev_byteorder=True)) as bitmap:
            with bitmap.to_pil() as image:
                width, height = image.size
                image.save(output, format='PNG', dpi=(dpi, dpi))
    return {'file': output.name, 'dpi': dpi, 'width_px': width, 'height_px': height,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
