# Python API

For instruction-like output, choose `camera_preset="instruction"` in Python or
`--camera-preset instruction` in the CLI. [Built-in recipes and evidence](CAMERA-PRESETS.md).

[Project](../README.md) · [Architecture](ARCHITECTURE.md) · [CLI](CLI.md)

The same functions drive the CLI and the original-example recipes. Paths can be
strings or `pathlib.Path` objects. Run from a checkout or install the wheel into
your own environment. Core rendering uses the standard library and an installed
C++17 compiler; the supported optional CMYK/preview environment uses Python
3.11+ and Pillow 13+/LittleCMS. Core rendering remains Python 3.10+.

## One model

```python
from brick_blueprint.pipeline import render

receipt = render(
    "examples/kiosk/kiosk.mpd",
    library="/path/to/ldraw",
    output="output/python-kiosk",
    cache_dir=".brickblueprint-cache",
    preset="modern-blue",
    width=760,
    height=600,
    azimuth=35,
    elevation=35,
    material_profile="research",
    line_width=0.55,
    glass_opacity=0.75,
)
print(receipt["parts"], receipt["pdf"]["PDF_sha256"])
```

Output is a new directory with `model.svg`, `model.pdf` and `render.json`; the
returned receipt is a dictionary matching that JSON. `FileExistsError` preserves
an existing output. Supported input checks raise `ValueError`; ordinary Python
call/argument errors may raise `TypeError`. Native build/render failures
can raise `RuntimeError` or subprocess errors. No library download or CAD/GUI
application is invoked. The caller controls its model, library, cache and output.

Pass `png_dpi=144` to `render` or `render_tray` to add `model.png` to the output directory. Install the optional rasterizer with `python3 -m pip install ".[png]"`. It draws the finished PDF page, including glass, the background and quantity labels. The `png` entry in the receipt records the pixel dimensions, DPI and file hash. At 144 DPI, a 600 × 450 point page gives a 1200 × 900 pixel PNG.

Dimensions and line width are PDF points. `projection="perspective"` is the default.
`field_of_view=30` sets vertical FOV; `camera_distance` and `camera_target` can
make the camera explicit. `camera_roll` and `principal_point=(x,y)` replay
a cropped source camera; principal point requires explicit distance. These
calibration controls are render-only. `scale`, if specified, is target-plane points/LDU;
otherwise the model fits the reserved viewport. LDraw up is -Y. A fixed scale
that cannot fit is rejected. `layout="callout"`, `quantity=2` and
`panel_role="subassembly"` create a role-specific card when the preset supports it.

`material_profile="research"` is the default for both `render` and `render_tray`.
Use `style_path` for a custom JSON; named profiles and custom files are
mutually exclusive. Receipts include material evidence, used color
bindings, interpolation rules and coverage. [Material profiles](MATERIAL-PROFILES.md).

Pass `underpaint=True` to `render` or `render_tray` to use the gallery surface treatment. Each render receipt then includes the number of inset paths and their tolerances. The default is `False`. [Compare the boat hull](PORTFOLIO.md#opaque-surfaces-at-screen-size)

## A shared-scale parts tray

```python
from brick_blueprint.tray import render_tray

receipt = render_tray(
    "examples/kiosk/bom-tray.json",
    library="/path/to/ldraw",
    output="output/python-kiosk-parts",
    preset="modern-blue",
    width=780,
    height=650,
    columns=4,
    gap=16,
    line_width=0.4,
    azimuth=35,
    elevation=35,
)
print(receipt["item_count"], receipt["represented_parts"])
```

The complete kiosk BOM has 16 entries representing 41 placements. Every entry
uses the same target-plane scale and distance in perspective (uniform scale in orthographic); model references in the JSON resolve relative to
that JSON. Explicit per-item cameras retain the scale. The composer does not
infer part identities, inventory sufficiency or a valid physical assembly.

## Export an existing SVG for print

```python
from brick_blueprint.print_export import export_print

proof = export_print(
    "output/python-kiosk/model.svg",
    output="output/python-kiosk-gray",
    mode="gray",
)
print(proof["page_mm"], proof["pdf"]["PDF_sha256"])
```

This validates the renderer's restricted SVG dialect and writes `print.pdf` plus
`print.json` into a new directory. It does not compile/render the model again.
For CMYK use `mode="cmyk", profile="/path/to/output.icc"` and optionally select
`intent`. RGB/gray need no Pillow. [Print details and limits](PRINTING.md).

These APIs are local development interfaces. The input guards and timeouts are
not a total memory/resource budget for an untrusted public upload service. Keep
physical assembly validation, source-instruction acceptance and licensing review
separate from successful output generation.

[Custom material styles and active fields](CUSTOM-STYLES.md) explain `style_path`; presentation presets and CLI page/line controls are separate.
