"""Read only generated PNG previews; do not probe unrelated image decoders."""


def open_png(path):
    from PIL import Image
    return Image.open(path, formats=('PNG',))
