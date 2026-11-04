# Measuring perspective in assembly illustrations

The sample contains 793 grid centers in 13 assembly views from 12 sets and six themes. A perspective fit predicted withheld centers more accurately than an affine fit in every view. The sample was selected for visible, measurable grids. The result describes those views. [Observations](PERSPECTIVE-DATA.json) · [Fitted values](PERSPECTIVE-RESULTS.json) · [Research paper](../RESEARCH-PREPRINT.md#1-perspective)

## Which surfaces were measured?

Seven views account for 373 centers. To find additional examples, we screened PDF pages 10, 15, 20, 25, 30 and 40 of sets 31168, 21270, 42603, 75376, 77071, 21063, 31376 and 11038. An image had to measure at least 350 × 180 pixels and show a planar grid with at least 20 visible centers spanning at least three rows and three columns. We took the earliest qualifying grid in each book. Six books supplied a view, adding 420 centers. Sets 77071 and 11038 had no eligible grid on those pages. [Seven-view measurements](../PROJECTION-EXPANSION.md)

All centers in a fit must lie on the same surface. For 42603 we used the lower green platform. For 75376 we used the right-hand 4 × 8 plate, excluding the raised central section. The selected centers remained in the fit regardless of their final prediction error.

## How were the projections compared?

An affine map has six free parameters. A planar perspective map has eight and allows the apparent spacing between parallel rows of studs to change with depth. We normalized the grid coordinates, initialized each map with a linear fit and minimized squared distances in the image.

Extra parameters make it easier to fit points the model has already seen. We therefore withheld centers in two ways. Three checkerboard groups tested predictions between measured points. Four contiguous bands tested predictions across a larger region. We repeated both comparisons at three detection thresholds and on the centers common to all three. The perspective fit had the smaller held-out error throughout. [Per-image measurements](PERSPECTIVE-RESULTS.json)

## Which camera angles can a flat grid reveal?

On a square grid of known pitch, the two denominator coefficients of the perspective map give the direction in which scale changes across the surface. Their ratio gives an acute angle for the optical axis projected onto that plane. The axis labels and signs must be specified. When the perspective effect is weak, small errors in locating centers can move the estimated direction appreciably.

Nine synthetic cameras of known geometry check the calculation. A separate ambiguity test constructs square-pixel cameras at elevations of 20°, 35° and 50° that reproduce the same fitted plane. The elevations become distinguishable when measurements also constrain a known height above the plane. [Planar camera family](PERSPECTIVE-RESULTS.json) · [Known-height brick measurements](../VOLUMETRIC-CAMERA.md)

## Repeat the fits

With Python and NumPy installed, run from the checkout root and select a fresh output directory.

```sh
python3 tools/analyze_perspective.py --output output/perspective-replay
```

The command fits all 13 views at each of three thresholds, then repeats those 39 fits using only the grid points shared by the three thresholds. The second set reuses the same images. It checks aggregate and individual held-out errors against the saved results, with a numerical tolerance of one millionth of a source pixel for RMS and 0.0001° for azimuth. Source identities, thresholds, center counts, fold sizes and the winning model must match. Nine synthetic cameras check the geometry separately. The observations include the PDF edition hashes, pages and image identifiers. [Check the original PDF editions](../VERIFICATION.md#verify-the-original-source-editions)

## How were the two renderers aligned?

For a near-parallel control, LDView used a 0.1° field of view and explicit camera centers and distances derived from the orthographic view. The maximum measured marker discrepancy was 0.176 px across 24 noncoplanar markers at an image width of 800 px. Across the geometry vertices the maximum calculated displacement between the two projections was 0.205 px. Both images received the same crop and resize. LDView used quality studs, matched nominal line width, and disabled seams and primitive substitutions. [Alignment measurements and settings](RENDERER-CAMERA-CONTROL.json)

A second control used a finite 30° perspective camera shared by both renderers. On four models, 32 noncoplanar markers agreed within 0.13 px at 800 px wide. These checks measure agreement between two configured renderers. The official-instruction measurements above use separate images. [Finite-camera results](PERSPECTIVE-IMPLEMENTATION.json) · [Camera equations](../CAMERA.md)
