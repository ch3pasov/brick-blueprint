# Glass, fading and emphasis are different operations

The renderer uses perspective and measured colors for eleven opaque materials. [Working camera angles](CAMERA-PRESETS.md) · [Material validation](MATERIAL-PROFILES.md)

Five already-sampled pages were audited on 2026-10-25 using full-page inspection, image-object inspection and PDF graphics-state/operator extraction. The important finding is a limit: the paper appearance is observable, but its original 3D material settings are not recoverable from these PDFs. [Machine-readable audit](MATERIAL-FORENSICS.json) records the exact files, pages, image placements, masks and graphics states.

## What is actually in the source PDFs

| Source/page | Visual role | Placed image objects | Form objects | Image alpha masks |
|---|---|---:|---:|---:|
| 31051 p74 | Lantern glass and light-function inset | 4 | 0 | 0 |
| 31376 p10 | Faded whole-model context card | 4 | 0 | 0 |
| 10343 p14 | Blue outline around current addition | 15 | 0 | 0 |
| 11508 p32 | Red current-part outlines and insertion | 4 | 0 | 0 |
| 11504 p10 | Red emphasis against dark slate | 16 | 0 | 0 |

None of the inspected graphics-state dictionaries specifies a non-default fill/stroke alpha (`/ca` or `/CA`); none of the placed images has a `/SMask` or `/Mask`. This is a statement about these five pages, not all LEGO PDFs. Some page images are tiled or clipped, so object count is not part count. Clip paths can hide rectangular image backgrounds without making their interior translucent.

### Glass is already drawn into opaque pixels

In [31051 page 74](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6167581.pdf), the main lighthouse image is 211×610 pixels and the inset illustration is 211×335 pixels. Both are opaque CMYK images without image alpha masks. Inspection of the inset's extracted pixels already shows the pale lantern enclosure, subdued interior and light outlines on dark roof/railings. The yellow star seen on the complete page is absent from that extracted illustration and is a separate page element.

Consequently, an inferred statement such as “the official glass uses 90% opacity” would be unsupported. The visible result could have been produced by a combination of face tint, transparency, selective line suppression, compositing and later image processing. A single flattened pixel supplies too little information to recover those choices. The existing renderer's glass-opacity slider is a controllable approximation, not a recovered source parameter.

### A context ghost is not a transparent LEGO material

In [31376 page 10](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6616307.pdf), the little hamster in the white context card is pale as a whole: solid brown body, eyes and outlines all recede. The extracted 130×111 RGB image already contains this faded appearance, without alpha. This is editorial context treatment of an entire model. Applying a transparent-plastic material to its bricks would expose hidden surfaces and produce a different result.

### A current-step outline is not ordinary edge ink

In [10343 page 14](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6555769.pdf), a blue contour emphasizes the newly handled group while ordinary inner edges remain dark. The white local assembly card retains ordinary dark linework; blue is not applied indiscriminately to everything on the page. Red arrows and black destination pointers have separate meanings.

In [11508 page 32](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6618829.pdf), red outlines surround the newly handled foliage/stem while ordinary edges remain dark. [11504 page 10](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6618828.pdf) also uses red emphasis, including on white and blue parts against slate. These observations require an explicit step/group role; the part's nominal color alone is insufficient to choose the highlight.

## What can be said about line weight

The lighthouse uses light linework on dark roof/railings and dark linework on light tower walls. This contrast convention is visible. Exact continuous stroke width is not available from the flattened illustration: an image pixel spans a finite area, with antialiasing and compression. For example, the 211-pixel-wide inset is placed approximately 151.92 PDF points wide, about 100 pixels/inch. Measuring a one-pixel contour there cannot establish a precise 0.32 pt original stroke.

This differs from native panel outlines, whose path geometry can be measured. A PDF object's `linewidth=0` may also represent a hairline or accompany filled outline geometry; blindly treating it as zero visible width gives the wrong result. Keep measurements of panels, model ink, highlights and pointer lines separate.

## Implementation recommendations, not claims of source equivalence

1. **Material appearance:** expose face tint/opacity and internal-edge contrast independently. Retain a readable exterior boundary. Inspect clear studs separately: the current pipeline deliberately makes cylinder walls opaque, which can produce dark internal cylinders on transparent bricks. That remains an explicit limitation, not a newly verified official convention.
2. **Context fading:** treat a completed model/group as a context layer, preserving its own hidden-surface solution. Composite or recolor that layer once; reducing each overlapping triangle's alpha separately changes the visible structure.
3. **Current-step emphasis:** derive an outline from the visible boundary of the selected part/group. Keep its color and width distinct from ordinary internal edges. Do not highlight every triangle seam, hidden edge or unrelated part of the page.
4. **Light/function symbols:** keep them as semantic vector annotations placed after the model render. Their role is to communicate a function. They need not imply volumetric light or a physically simulated beam.
5. **Theme presets:** select page/panel/label appearance separately from these semantic operations. A slate page needs contrasting text and pointer treatment; a change of background alone is insufficient.

Brick Blueprint renders native vectors with shared scale, per-item camera settings and adjustable glass opacity. Fading the previous assembly, outlining new pieces and drawing light or function symbols would require additional composition. The renderer applies measured face colors and separate shading to the vertical walls of selected studs. [Material profiles](MATERIAL-PROFILES.md)

Local extracted-image previews were used only to establish which visible effects were already baked into the images. Their simple color conversion was not used for palette measurements, and no official image or font program is distributed in this project.

## Paired-source and shading follow-up

[16 same-theme/year presentation pairs](PAIRED-THEME-STUDY.md), [ten-color face shading](SHADING-STUDY.md), and [actual-step gallery evidence](ACTUAL-STEP-EXAMPLES.json) extend the earlier samples. Earlier page counts refer to their historical study, not the enlarged 38-book corpus.


## Opt-in continuous slope colors

The `research-angular` profile implements the subsequently tested piecewise linear-light rule, with explicit white calibration and eight prospective geometry controls. The default `research` profile retains the three-face blend. [Implementation, matched vectors, cohort accounting and limits](ANGULAR-MATERIALS.md).
