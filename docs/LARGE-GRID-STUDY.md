# A large grid is not automatically an orthographic calibration

**Expanded sample:** [seven large step views from six sets](PROJECTION-EXPANSION.md), with held-out spatial bands and threshold controls. The original measurements below remain unchanged.

A continuation of the [camera study](CAMERA-STUDY.md) tests a larger grid on [Architecture 21062, official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6566168.pdf), PDF page 20. This page was already in the source registry; corpus totals remain 23 books and 97 sampled pages.

The initial four-view pilot had wide landmark sensitivity, especially for tiny inventory parts. A large grid can reduce that limitation, but introduces a more basic question: **does a parallel projection adequately describe the image?**

## Source and method

The left foundation contains a visually identified 8-column by 10-row stud grid. The measurement uses its original embedded 1198×661-pixel image, not a resized screenshot. The native PDF placement is recorded separately. Official illustration pixels remain outside this repository.

Top-cap centers are estimated from connected bright regions inside their dark outlines. Three thresholds, 60, 80 and 100 on an 8-bit grayscale image, test sensitivity to the segmentation choice. Component area and width/height limits exclude background and large faces. A manually seeded grid assigns integer column/row indices; the resulting overlay was visually reviewed. Missing centers are retained as missing, not filled with fitted coordinates. The main threshold is 80 and yields 76 of 80 centers.

Two mappings are fitted to those grid coordinates:

- **Affine, six parameters:** parallel grid directions; includes translation, scale, shear and constant pixel-aspect effects.
- **Projective, eight parameters:** a planar homography, allowing grid lines to converge.

Three checkerboard folds, selected by `(column + row) % 3`, hold out one third of the detected centers at a time. Each fit uses only the other two thirds, then predicts the held-out centers. This tests prediction rather than reporting only training residuals. The folds still come from one source image; they are not independent books or independent physical captures.

## Results

Errors below are Euclidean distances in **original source-image pixels**, before page upsampling.

| Segmentation threshold | Detected centers | Affine held-out RMS | Projective held-out RMS |
|---|---:|---:|---:|
| 60 | 63 | 0.906 px | 0.133 px |
| 80 | 76 | 0.875 px | 0.147 px |
| 100 | 78 | 0.866 px | 0.153 px |

At the main threshold, the maximum held-out error falls from 2.15 px to 0.29 px. The projective model's advantage persists across the tested thresholds, with about 5.7–6.8 times lower RMS error.

The lighter rear plate and darker front plate were also fitted separately. This checks whether a discontinuity at their boundary alone explains the result:

| Section, threshold 80 | Centers | Affine held-out RMS | Projective held-out RMS |
|---|---:|---:|---:|
| Light section | 47 | 0.539 px | 0.142 px |
| Dark section | 29 | 0.447 px | 0.156 px |

The advantage remains within each section. Independent synthetic affine and projective fixtures verify the fitting and cross-validation code: the appropriate models recover the known transforms to numerical precision. Those fixtures test the method, not the source assumptions.

[Measurements and parameters](LARGE-GRID-MEASUREMENTS.json) include every detected center, missing grid indices, source/image hashes, native placement, segmentation settings, fitted parameters and fold results.

## What this establishes—and what it does not

For this illustration, a projective mapping predicts cap centers substantially better than a single affine mapping. That is evidence of a small, systematic departure from parallel projection. A constant stretch caused by native image placement would already be absorbed by the affine model, so it cannot alone explain this advantage.

The result is consistent with perspective rendering of a planar grid. It does **not** uniquely prove a particular camera or lens: source-image warping, top-cap centroid biases and the coplanar-grid assumption remain possible contributors. The threshold sweep is not a statistical confidence interval. Model selection on one image does not establish a universal publisher convention.

Applying the old orthographic slope inverse anyway gives an apparent elevation of about 37.36° after accounting for native PDF pixel scaling. Because the affine assumption is weaker here, that number is **not accepted as a camera calibration**. Focal length, camera distance and true elevation cannot be recovered from this fit alone without further constraints.

## Independent inventory control

A second, independently selected grid comes from [Star Wars 75375, official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6509377.pdf), PDF page 60. Its inventory plate has a complete 4-row by 10-column grid. The embedded image is only 226×121 pixels; all 40 cap centers were detected and the overlay was visually reviewed. This page was already registered, so corpus totals do not increase.

The same affine/projective fitting and held-out checkerboard method was used. Segmentation thresholds are source-specific: the Architecture thresholds 60/80/100 did not isolate usable closed cap regions here; 120/140/160 did. This is a sensitivity sweep, not a statistical confidence interval.

| Threshold | Centers | Affine held-out RMS | Projective held-out RMS |
|---|---:|---:|---:|
| 120 | 40 | 0.286 px | 0.177 px |
| 140 | 40 | 0.298 px | 0.200 px |
| 160 | 40 | 0.396 px | 0.350 px |

Here the projective advantage is modest and threshold-sensitive: about 1.1–1.6 times, with all errors below half an original pixel. It is substantially weaker than in Architecture. Subpixel center estimates do not imply subpixel source accuracy. This neither proves an orthographic camera nor establishes a universal perspective convention. Theme, book, image resolution and illustration role all differ, so the contrast cannot be attributed to any single one of them.

[Control measurements](INVENTORY-GRID-CONTROL.json) retain source/image hashes, native placement, every center, thresholds and fitted parameters. Official image pixels remain outside this repository.

## Implications for Brick Blueprint

At the time of this initial study the renderer was orthographic. Since 0.5.0.dev1
it defaults to a true perspective camera; since 0.6.0.dev1 the working angles are
35°/35°. This does not turn the old inverse fit into a recovered camera.
[Current camera and validation](CAMERA.md).

A useful next study would add higher-resolution grids with known model axes and additional planes, and match inventory/assembly roles within the same book. Any future perspective mode must retain explicit camera/distance parameters and clarify that common physical scale in an inventory does not imply equal apparent size at different depths. The present result supports investigating that feature; it does not justify silently replacing existing views or calling them exact reproductions.
