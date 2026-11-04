# Reproduce a render with the same inputs

Keep the model, render settings, style file and exact external library revision.
Each fresh model receipt records the model SHA-256, camera, physical scale,
style SHA-256, DAT dependency hashes/attribution and the `library_config`
record. Parts-tray receipts preserve the same record for every item.

`library_config` identifies the exact `LDConfig.ldr` bytes parsed for material
colors, with available author/license headers. A library's DAT files can stay
unchanged while its color or alpha definitions change. Geometry dependency
hashes alone do not identify that palette revision. The record contains a
library-relative filename, never the local library directory.

This receipt addition changes provenance only. It does not change projection,
colors, geometry, camera defaults or the SVG/PDF exporter. Historical gallery
receipts remain frozen and may predate the field. Do not fill their missing
provenance from a newer library or relabel an old render as a fresh one.

## Three levels of comparison

1. **Inputs:** compare the source candidate's manifest and the model, DAT,
   `library_config` and style hashes. Preserve the CLI options too.
2. **Vector bytes:** compare `SVG_sha256` and `PDF_sha256` from the render's
   PDF audit. The same environment and input can produce byte-identical
   exports. Cross-runtime byte identity is not guaranteed: floating-point
   evaluation, compiler/runtime versions and contour traversal can differ.
3. **Visible result:** rasterize both PDFs with the same renderer and DPI,
   then compare pixels. Pixel identity at that resolution does not establish
   identical vector paths or appearances on every output device.

Fresh `render` and `tray` receipts now contain an `execution` record: Python
version/implementation, OS family, machine architecture, compiler name/version,
native source/cache key, hashes of the actual native binaries and a package-source
tree fingerprint. The latter hashes the sorted relative paths and SHA-256 values
of runtime Python/JSON/C++/header/license files; bytecode, caches and private paths
are excluded. It can be compared across an installed wheel and source checkout.
This does not capture every system library or compiler option in the world.

Record the PDF rasterizer and editorial font too when comparing preview pixels.
The kiosk showcase recipe records those separately. The source-export manifest
identifies the distributed code/docs/examples. Historical receipts stay frozen
and may predate the execution record; do not retrofit them from a newer environment.

For example, compare two locally generated preview PNGs using optional Pillow:

```python
from PIL import Image, ImageChops
a = Image.open("first.png", formats=("PNG",)).convert("RGB")
b = Image.open("second.png", formats=("PNG",)).convert("RGB")
assert a.size == b.size
print("Same pixels:", ImageChops.difference(a, b).getbbox() is None)
```

An error score against official instruction artwork is a separate style study.
Keep its source, camera assumptions, registration and uncertainty; equal input
hashes or identical rerenders do not prove a match to LEGO's renderer.

See [architecture](ARCHITECTURE.md), [gallery provenance](GALLERY.md),
[source candidate export](RELEASE-TOOLING.md) and [verification](VERIFICATION.md).

## What changes with the compiler?

We rendered a boat, a transparent lantern, the crossing gate in two poses and the self-contained fixture with and without underpaint on three arm64 toolchains. Each run used the same projected scene as its two counterparts. The SVG and PDF files agreed byte for byte between GCC 16 on macOS and GCC 15 on Linux across all six examples. Apple clang 21 produced a different file for each example and format.

At one and two pixels per point, the largest whole-page mean absolute difference was 0.00157 of one 8-bit RGB level. The largest change in any individual channel was 25 levels. At most 0.0115% of pixels changed by eight or more levels in any channel. These measurements distinguish small local edge differences from changes to the scene itself. [Per-file hashes, toolchains and all 24 pixel comparisons](gallery/compiler-replay.json)

## Check the kiosk renders

`tools/verify_gallery.py` compares a fresh original-kiosk showcase and/or preset
folder with the included reference receipts. It checks the exact SVG/PDF hashes,
recipe-to-receipt links, model/manifest hashes, geometry and palette revisions,
and package sources. It recognizes the recorded vector renderer and the specific source revision that adds PNG conversion after PDF export. Both checks still require exact reference SVG and PDF bytes. The optional preview check compares PNG bytes without
importing Pillow. Runtime/toolchain differences are noted separately.

```sh
python3 tools/verify_gallery.py --showcase output/kiosk-showcase \
  --presets output/kiosk-presets --previews
```

The kiosk reference uses the complete 2026-10 library, the instruction camera and the measured material profile. Run the showcase with `--stages` for the full series. [Kiosk recipe and examples](KIOSK.md#render-the-eight-stages) · [Library hash](PORTFOLIO.md#which-parts-library-reproduces-the-pictures)

Exact print
comparison additionally requires all three modes and the same ICC profile as
the saved reference. Use `--print-proof` only for that case. A byte difference
may still look identical at one rasterization; inspect and classify it rather
than accepting an unspecified tolerance. The command never changes receipts,
renders files, extracts DAT data or contacts a network. [Original recipe](KIOSK.md).

## Print the English paper

The paper and measurement tables are also available in a print layout. Its text comes from the Markdown sources. The projection and color charts use vector primitives. The Brick Blueprint plate is embedded as native PDF paths beside the LDView raster control. The source links in the tables open the official pages.

The optional typesetter needs Python, ReportLab, pypdf, Pillow and a directory containing the regular, bold, italic and bold-italic TrueType files for Liberation Sans, Serif and Mono. Those packages and fonts are separate from the core renderer.

```sh
python3 tools/build_paper_pdf.py --font-dir /path/to/liberation-fonts \
  --output output/paper/Brick-Blueprint-research.en.pdf
```

To create the one-page brief alongside the paper, use the same font directory. Keep the two PDFs together. Each answer in the brief links to the page that contains its evidence. The generator checks the thirteen reference phrases against the actual text and page count of the supplied paper.

```sh
python3 tools/build_research_brief.py --check --font-dir /path/to/liberation-fonts \
  --pdf output/paper/Brick-Blueprint-brief.en.pdf \
  --full-pdf Brick-Blueprint-research.en.pdf
```

To check an existing edition without generating a PDF, run `python3 tools/build_research_brief.py --check --check-paper output/paper/Brick-Blueprint-research.en.pdf`.

[Research paper](RESEARCH-PREPRINT.md) · [Measurement tables](research/MEASUREMENT-TABLES.md)

With the same Liberation font files, the 12-page paper and one-page brief reproduced byte for byte on the reference macOS system and an offline Alpine Linux guest. Both documents were generated from the English checkout. The brief's thirteen links were checked against the generated paper.
