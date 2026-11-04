# Third-party notices

## Clipper2

Source: https://github.com/AngusJohnson/Clipper2

Pinned commit: `a6e7294703ae329576462f9471b356971f53010d`.

Author: Angus Johnson; additional authors, if any, are recorded in the preserved source notices. License: Boost Software License 1.0, reproduced in `brick_blueprint/native/vendor/Clipper2/LICENSE`.

Used for integer polygon union and clipping only. The visibility renderer, projection and PDF-writing layers are separate project code. Vendored files are byte-identical to the recorded snapshot; hashes are in `PROVENANCE.json`.

## LDraw

This software can use the [LDraw Parts Library](https://www.ldraw.org/), supplied separately. No official LDraw parts are bundled. Attribution and license obligations depend on the particular library files and output being distributed. `render.json` preserves the dependency headers available in the chosen library.

The showcase images use LDraw geometry with CC BY 4.0 headers. [Per-file authors, hashes and license notices](docs/gallery/LDRAW-ATTRIBUTION.json) are retained. The geometry has been transformed, projected, shaded and composited into illustrations; [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) applies to the identified third-party material. See [gallery provenance](docs/GALLERY.md). Set-design and trademark considerations remain separate.

## Trademarks

LEGO is a trademark of the LEGO Group. This project is independent and is not sponsored, authorized or endorsed by the LEGO Group or LDraw.org. No official logo is included.

## Editorial type in the original kiosk previews

Outfit, Copyright 2021 The Outfit Project Authors
(https://github.com/Outfitio/Outfit-Fonts), is licensed under SIL Open Font License
1.1. It is used to rasterize editorial captions in the kiosk portfolio PNGs.
No Outfit font program is included. Font source/hash are recorded in
[FONT-SOURCES.json](docs/FONT-SOURCES.json); the optional recipe accepts a
caller-supplied font. The font's [OFL guidance](https://openfontlicense.org/)
is separate from the project’s [MIT code license](LICENSE).

For contributor names, use the per-file credit indexes, which preserve the original spelling in the DAT headers. Some historical render receipts display an accented name incorrectly. For example, the header of `s/63864s01.dat` credits Ulrich Röder [UR].

The articulated crossing gate has its own [model and geometry credits](docs/gallery/crossing-gate.json). The five original portfolio models have a separate [geometry credit index](docs/portfolio/sources.json) with file authors, original license notices and hashes. Their placement, transformation, shading and vector projection are documented in the [portfolio recipe](docs/PORTFOLIO.md).

The [Quayside Shunter credit index](docs/gallery/shunter-step.json) lists the LDraw authors, notices and file hashes used for the locomotive and its two headlamps.

The [Lighthouse Point vector credit index](docs/gallery/lighthouse-vector.json) records the external geometry and original notices for the 537-placement scene. The LEGO Group designed set 31051 and published its [official instructions](https://www.lego.com/en-us/service/building-instructions/31051). Anatolii Chepasov developed the Brick Blueprint renderer used to illustrate the reconstruction.
