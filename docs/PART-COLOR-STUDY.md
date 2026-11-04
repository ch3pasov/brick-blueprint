# Do themes recolor the same part?

**The matched examples support a shared part-illustration palette, with different page/tray backgrounds.** They do not justify a theme-specific recoloring rule. We checked four opaque elements across five books/themes, then followed the brown brick into the actual per-step parts trays of three books.

This is a bounded comparison: 12 end-inventory occurrences on 7 pages, plus 3 step occurrences on 3 pages. One step page was already in the style atlas, so 9 new pages bring the overall corpus to 106 distinct sampled pages in 23 PDFs. No official illustration pixels or profiles are included in this repository.

## Per-step control: the brown 2×2 brick

The source parts trays show the same reddish-brown 2×2 brick, identified by shape/color against element 4211210 in each book's end inventory:

| Theme / set | Official PDF | Page / step | Native part image | Interior side-face median sRGB |
|---|---|---|---|---|
| Classic 11038 | [6509312](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6509312.pdf) | PDF 21, step 4 |63×59 px |91,43,19 |
| Minecraft 21269 | [6556015](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6556015.pdf) | PDF 27, step 29 |63×59 px |91,43,19 |
| Star Wars 75375 | [6509377](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6509377.pdf) | PDF 20, step 26 |63×59 px |91,43,19 |

All three images use the same embedded sRGB profile and visually aligned geometry/orientation. Their part images are flattened onto blue, green and gray backgrounds, respectively; the full images consequently have different hashes.

Corresponding interior pixels give a mean absolute difference of 0.048–0.085 channel levels on a 0–255 scale on the first face. The second selected face matches pixel-for-pixel across all three and has median 80,38,18. Moving the first rectangle by one native pixel in each direction gives mean differences no greater than 0.243. Individual first-face pixels differ by up to 5 levels; this small variation is consistent with compression/antialiasing, but its exact origin has not been proven.

[Step measurements](STEP-COLOR-CONTROLS.json) retain every source/image/profile hash, native image placement, exact interior rectangles, pixel differences and shifted-rectangle sensitivity. Step cards do not print element numbers, so the link from the numbered end-inventory item to the step item is a visually verified shape/color match, not an embedded ID lookup.

## End-inventory controls

| Exact element ID | Matching books and one-based PDF pages | Observation |
|---|---|---|
|4211104, dark-gray 1×3 brick |Creator 31051 p181; Architecture 21062 p218; Star Wars 75375 p. 182 |The modern Architecture/Star Wars images are 52×43 px and **decoded RGB bytes match exactly**, with identical ICC profiles. |
|6066097, light-gray 1×2 jumper |Creator 31051 p181; Architecture 21062 p218; Star Wars 75375 p. 181 |Modern 39×26 px images share the sampled top-face median 163,163,163; mean absolute pixel difference 2.75, max 5 in the selected tiny patch. Not exact image equality. |
|4211210, brown 2×2 brick |Classic 11038 p. 53; Minecraft 21269 p. 82; Star Wars 75375 p. 181 |48×45 px images. One corresponding 36-pixel side-face patch matches exactly across all three; the second patch differs slightly. |
|4211399, light-gray 1×1 plate |Architecture 21062 p218; Minecraft 21269 p. 83; Star Wars 75375 p. 181 |26×22 px images. Sampled side median 169,169,169 in all three; selected-patch maximum channel difference 1. |

Sources: [Creator 31051](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6167581.pdf), [Architecture 21062](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6566168.pdf), and the three PDFs linked in the step table. [Inventory measurements](MATCHED-PART-COLORS.json) provide the precise image/element-number positions and source hashes.

All 12 element-number/image associations were checked on rendered source crops, and all 7 complete inventory pages were inspected. Sample rectangles were checked on native-image enlargements. Quantities and inventory background colors were not treated as part-color samples.

## Why color management matters

The older 2016 Creator examples use embedded **ISO Coated v2 CMYK**; the modern examples use embedded **sRGB**. Their original image sizes also differ. A naïve CMYK-to-RGB conversion visibly changes the old gray pieces. We reconstructed indexed palettes in their original color space and converted the old CMYK images through their embedded profile with LittleCMS, relative colorimetric intent. Modern tagged-sRGB values were compared without recoloring.

The 2016 images are therefore a profile/resolution control, not a clean test of a Creator-specific part palette. We do not attribute remaining differences to theme, year or a specific rendering pipeline without additional controls.

## What changes in Brick Blueprint

The primary preset contact sheet now puts **four individual parts** in every actual parts tray: a white 1×2 plate, red 2×4 brick, tan 2×2 slope and black Technic pin. All thirteen tray styles use the same camera and 0.95 points/LDU scale, with quantities 2x/1x/2x/3x. Shape, spacing and quantity contrast come from the presentation preset; material colors stay fixed.

The sampled Star Wars foldout has no separate parts tray, so its orange example remains explicitly labeled as a **subassembly card**. Two additional role examples also remain assemblies. We do not invent a parts-frame convention for that source.

The [six-part tray](PART-ILLUSTRATION.md) illustrates shared scale. In the [paper-style gallery](PRESETS.md), each inventory lists the individual pieces for its step. A separate panel can show an assembled module.

## Limits

This is not a full palette census. It covers four opaque neutral/brown parts and only one part in per-step trays. Transparent shells, printed parts, saturated reds/blues, instruction-era changes, assembled-model shading and current-step outlines need separate controls. Tiny raster samples limit measurement precision. Shifted rectangles are sensitivity checks, not statistical confidence intervals. RGB/profile equality concerns the digital source and does not prove identical physical ink on different paper.
