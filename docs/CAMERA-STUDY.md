# Camera study: what the stud grid can establish

**Expanded catalogue study, preprint 0.2:** [30 cap-center assets from eight books](RESEARCH-PREPRINT.md), 1150 landmarks, exact-duplicate screening and a 432-condition raster detector control. Approximate angles remain near 35°/35°. Complete three-threshold sensitivity is available for 16 assets; ten favor projective prediction in every common-center/fold-method comparison. This is exploratory, not a universal camera estimate or a significance test. [Data and replay](research/CAMERA-CATALOGUE-PROTOCOL.md). The historical pilot below remains unchanged.

**26 October statistical follow-up:** the [research preprint](RESEARCH-PREPRINT.md)
reanalyzes the inventory grid with free in-plane rotation and equal-pitch geometry.
The primary estimate is 35.348° acute azimuth / 35.021° elevation; the older
no-roll slope estimate remains below with its original assumptions. Structured
residuals and threshold-sensitive tests prevent a calibrated exact-angle claim.
See [data](research/CAMERA-STATISTICS.json) and the reproducible analysis linked in the preprint.

**Expanded sample:** [seven large step views from six sets](PROJECTION-EXPANSION.md), with held-out spatial bands and threshold controls. The original measurements below remain unchanged.

The initial pilot measured four views on two already-sampled official pages on 2026-10-25. The question is whether a single exact camera can be inferred from the instructions. The answer is **not from this sample**. Three point estimates are near 35 degrees elevation, but the inventory views are too small to establish an exact angle. The existing renderer's 30-degree default remains a design choice, not a measured LEGO standard.

A subsequent [large-grid audit](LARGE-GRID-STUDY.md) adds 76 detected cap centers from Architecture 21062 p20. Held-out projective predictions outperform an affine mapping, so a larger grid does not by itself validate the orthographic assumption. The original pilot measurements below are preserved as bounded evidence.

## Method and limitations

Choose four top-cap centers spanning a rectangular stud grid: A/B and C/D run along one direction, A/C and B/D along the other. Average the parallel projected vectors, then compute their slopes `m1` and `m2`. For a horizontal plane under a level, unrolled orthographic camera:

```
sin(elevation)^2 = abs(m1 * m2)
acute_yaw_class = atan(sqrt(abs(m1 / m2)))
```

The second quantity depends on which grid axis is named first. Reflections, axis swaps and quarter turns are unresolved without the model's own coordinate frame. It is not automatically the renderer's `--azimuth` value. Perspective, camera roll, a tilted subassembly or a distorted screenshot invalidate this simple inverse.

Landmarks were manually selected on page rasters with a 4000-pixel long side. This increases coordinate convenience, **not the detail present in the source image**. Each coordinate was perturbed by ±6 pixels and all 256 coordinate-box corners were evaluated. The ranges below are sensitivity envelopes for that chosen perturbation, not statistical confidence intervals or a formally proved global bound. A wider error assumption gives wider ranges. Top-cap centers must be used consistently: the center of the visible stud cylinder silhouette sits lower than the top ellipse center.

The inverse was checked independently against synthetic orthographic projections at azimuth/elevation pairs 20/15, 35/30, 55/35 and 70/50 degrees; recovery differed by less than `1e-9` degrees. That checks the algebra, **not** the validity of the source-image assumptions or manual landmarks.

## Observations

| Source and role | Point estimate of elevation | ±6 px corner sensitivity | Interpretation |
|---|---:|---:|---|
| 31376 p16, red 2×4 brick in inventory | 34.8° | 27.1–45.0° | Only one stud interval across the narrow direction; weak angle constraint |
| 31376 p16, same red brick in assembled model | 35.0° | 29.8–41.4° | Larger drawing helps; azimuth appearance differs from the inventory |
| 31051 p18, blue 2×8 plate in inventory | 38.8° | 24.7–68.9° | Too weak to infer a different camera; reject it as an exact-angle calibration |
| 31051 p18, broad tan grid in assembled model | 35.1° | 31.8–38.8° | Six stud intervals by three give the strongest constraint in this sample |

Sources: [31376 official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6616307.pdf), page 16; [31051 official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6167581.pdf), page 18. The [source registry](STYLE-SOURCES.json) identifies the exact files. [Sanitized measurements](CAMERA-MEASUREMENTS.json) preserve crop origins, landmarks, assumptions and computed ranges; official images remain outside the public project.

The long stud row of the 31376 inventory brick rises to the right; the same brick's long row in the assembled view falls to the right. The drawing therefore changes object orientation relative to the viewer between these roles. Elevation alone is not enough to reproduce the view. Keeping a common physical scale inside an inventory does not require every object to use an identical camera orientation.

Other already-inspected evidence is qualitative but decisive: 31169 pages 9–10 and 31376 page 10 deliberately show the underside needed for the current operation. These cannot be reproduced by imposing the same positive-elevation overview on every illustration.

## Consequences for the renderer

- Keep the current camera explicit and overridable. Do not claim that 35° azimuth / 30° elevation is an official universal convention.
- Treat an elevation near 35° as a useful **candidate for comparison**, supported most strongly by the broad assembled grid above. Do not silently change existing output based on four views.
- Choose a view that shows the relevant connection or identifying face. To compare several parts side by side, use the same camera and align their local stud grids.
- Keep scale and orientation separate: common points-per-LDU can coexist with per-item rotations. Avoid normalizing each object's outer pixel box.
- For more precise calibration, use a larger flat grid, known model axes and several views; retain held-out landmarks. Do not use upsampling or a successful algebra self-check as evidence of source fidelity.


## Large inventory grid: conditional angle refinement

The independent 40-center control in 75375 p60 also supports an approximately 35° elevation and 35° acute grid-axis azimuth under the orthographic assumptions above. Correcting for native image placement aspect ratio, the threshold-140 affine fit gives 34.955° elevation and 35.086° acute azimuth. Thresholds 120/140/160 span 34.955–35.027° and 35.071–35.086° respectively. These ranges are threshold sensitivity only, not accuracy bounds; roll, perspective, grid planarity and centroid bias remain unbounded. This does not calibrate a perspective camera or establish a universal parts-tray pose.

The derivation is reproducible with `tools/build_faq_constants.py`, using the affine vectors and placement in [INVENTORY-GRID-CONTROL.json](INVENTORY-GRID-CONTROL.json). Results are stored with their conditional status in [FAQ-CONSTANTS.json](FAQ-CONSTANTS.json). The renderer default remains azimuth 35°, elevation 30°.
