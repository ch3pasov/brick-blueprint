# Dependency scope and the checked environment

Checked on 26 October 2026. The core renderer, RGB/grayscale export and source
candidate exporter use the Python standard library plus a local C++17 compiler.
They do not import Pillow, launch CAD applications or download a parts library.
The source tree vendors fourteen pinned Clipper2 files; its Boost 1.0 license
and [upstream hashes](../brick_blueprint/native/vendor/Clipper2/PROVENANCE.json)
remain included in both source and wheel.

The optional `png` extra installs pypdfium2 and Pillow. The model and tray commands load them when raster output is requested. Gallery authoring scripts can also use Poppler for their editorial previews.

The optional `print` extra declares **Pillow>=13.0**, which requires
**Python 3.11+**. Core rendering remains Python 3.10+ and does not require Pillow.
The checked optional environment uses Python 3.12.14, Pillow 13.0.0 and LittleCMS
2.19. The compatibility suite also passed with Pillow 12.3.0. The supported optional installation starts at version 13.0.

Pillow [13.0.0 release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
record the Python support change and fixes beyond the three advisories below,
including additional decoder and font error paths. This is a tested compatibility
baseline, not a claim that every permitted future version is safe or identical.
The [local optional-environment record](PILLOW-VERIFICATION.json) pins the downloaded
wheel hash and environment. Recheck upstream releases and advisories before a
public release. Build tooling uses the declared setuptools backend; keep its
version and the fixed `SOURCE_DATE_EPOCH` with a reproducible wheel build.

## Current Pillow advisories and the paths used here

The upstream pages list the following on the check date:

| Advisory | Listed affected releases / fix | Relevant code-path boundary |
| --- | --- | --- |
| [GHSA-78g4-xqwv-q3g8](https://github.com/python-pillow/Pillow/security/advisories/GHSA-78g4-xqwv-q3g8) | 11.1.0–12.3.0; lists 13.0.0 as patched | JPEG 2000 decoding through bundled OpenJPEG. The CMYK path never opens an image file. Preview readers explicitly permit PNG only. |
| [GHSA-fc9g-5qg7-mf45](https://github.com/python-pillow/Pillow/security/advisories/GHSA-fc9g-5qg7-mf45) | 9.2.0–12.3.0; lists 13.0.0 as patched | GIF comment handling during GIF save. These tools save PNG previews and do not save GIF. |
| [GHSA-654x-cwwv-5j9c](https://github.com/python-pillow/Pillow/security/advisories/GHSA-654x-cwwv-5j9c) | 11.2.1–13.0.0; lists no patched release | Arrow export with nondefault alignment. The project does not use Arrow APIs or set allocator alignment. |

These are a bounded reachability review of the listed advisories, not a general
dependency vulnerability scan. The first two list 13.0.0 as patched; the Arrow
advisory still lists no patched release on the check date. This project does not
use Arrow export or set its allocator alignment. Version 13 is not described as
free of all vulnerabilities. The historical 12.3 environment contains OpenJPEG
2.5.4; an unrelated operating-system update does not clear that affected codec.
No global package was upgraded or downgraded for this audit.

## What is restricted

`print_colors.py` creates a one-pixel in-memory RGB sample and uses ImageCms
to transform vector paint colors through a caller-supplied ICC output profile.
It does not call `Image.open`. ICC parsing is a separate input surface; header,
size and color-space checks are not a proof that an arbitrary profile is safe.

The optional font/FAQ preview scripts read PNG files created by Poppler or
their own preceding steps. `tools/preview_images.py` passes an explicit PNG
format allowlist, so a JPEG/JP2 file renamed to `.png` is rejected before its
decoder is selected. Tests preserve valid PNG pixels and reject a valid JPEG
under a PNG filename. This does not turn PDF/font parsing or the renderer into
a hardened service for untrusted public uploads.

Research generators additionally use optional local packages such as numpy,
pdfplumber and FreeType through Pillow, plus Poppler. They are not required
for the installed renderer's smoke check. No research source PDFs, proprietary
font programs, external DAT library, ICC profile or codec binary is bundled.

See [the upstream Pillow security policy](https://github.com/python-pillow/Pillow/security),
[license boundaries](LICENSING.md), [verification](VERIFICATION.md) and
[source reproduction](REPRODUCIBILITY.md).
