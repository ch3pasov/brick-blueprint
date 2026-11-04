# Expanded projection study: seven large step views

These seven views from six sets and five themes contribute 373 centers to the [13-view perspective study](research/PERSPECTIVE-PROTOCOL.md). In every view, the planar perspective fit predicts the stud positions more accurately than the parallel fit.

| Source | Centers | Parallel error | Projective error | Gain across three thresholds |
|---|---:|---:|---:|---:|
| [Architecture 21062, p 20](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6566168.pdf#page=20) | 76 | 0.875 px | **0.147 px** | 5.7–6.8× |
| [Creator 31139, p 11](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6456165.pdf#page=11) | 72 | 0.873 px | **0.121 px** | 6.6–7.2× |
| [Creator 31169, p 20](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6556274.pdf#page=20) | 64 | 0.603 px | **0.153 px** | 3.7–4.4× |
| [Minecraft 21269, p 20](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6556015.pdf#page=20) | 33 | 0.470 px | **0.137 px** | 2.8–3.4× |
| [Friends 42604, p 10](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6493646.pdf#page=10) | 47 | 0.457 px | **0.154 px** | 2.8–3.0× |
| [Minecraft 21269 base, p 70](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6556015.pdf#page=70) | 29 | 0.414 px | **0.089 px** | 3.4–4.6× |
| [Fortnite 77073, p 25](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6541111.pdf#page=25) | 52 | 3.615 px | **0.171 px** | 17.8–22.6× |

## Method

Native embedded images are measured before resizing. Connected cap interiors (or matching hollow-stud openings on the Fortnite edge beams) yield centers. Visually selected seed axes assign integer grid coordinates; they are not the fitted camera. Component filters, grid bounds and every center are recorded in [PROJECTION-EXPANSION.json](PROJECTION-EXPANSION.json).

The affine fit has six parameters and preserves parallel equal-pitch rows. The homography has eight parameters. Fits are evaluated with three held-out checkerboard folds. A second check holds out four contiguous column bands. Three thresholds test segmentation sensitivity, and the threshold comparison is also repeated on an identical intersection of centers. All checks favor the projective model for every retained image.

Known synthetic affine and projective grids independently check the fitting code. This validates the calculation, not the source-plane assumptions. Initial extraction drafts had misindexed rows and dark stud-side components; these were corrected by visual review of grid labels and feature shapes, not by deleting points with inconvenient residuals. The final annotated sources are kept in the local research edition.

## A direct equal-length control

Fortnite 77073 p25 has two long parallel beams with repeated hollow studs. On each beam compare indices 1–6 with 22–27: five identical physical intervals each. At the main threshold the upper spans measure 143.35 and 156.47 native pixels; the opposite beam gives 144.45 and 157.54 px. Across both beams and all three thresholds the ratio is 1.0901–1.0925. This is visible size variation along one direction, incompatible with a single undistorted parallel projection of a constant-pitch straight beam.

## Interpretation and limits

- 7/7 is the selected sample, not all instruction books. Minecraft contributes two images, so seven images are not seven independent books.
- The Friends example is a large base during a part-addition step, not a completed model. Native widths range 325–1198 px.
- Cap/inner-hole centroids approximate geometric centers; planarity and constant physical pitch are assumptions reviewed visually.
- Perspective-compatible geometry does not uniquely recover focal length, distance or the original production pipeline. Post-render image warping remains possible.
- Threshold variation is a sensitivity check, not a confidence interval. Errors below one pixel are measured from native components, not an assertion of unlimited image precision.
- The inventory control at 75375 p60 remains inconclusive and is not counted among these seven.

## Reproduction record

The data links each measurement to its PDF edition, page and embedded image. It records file hashes, native pixel dimensions, thresholds, bounds, seed vectors, detected centers, fitted parameters, held-out groups and errors.
