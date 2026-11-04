# Catalogue camera study: preprint 0.2

Development study, 26 October 2026. Not a registered confirmatory experiment.

Twelve existing official books were screened in their last eight PDF pages. A candidate catalogue page needed at least ten printed six/seven-digit element IDs; embedded candidates had width 90–700 and height 45–700 pixels. The screen found 282 candidates, 220 exact decoded-pixel/ICC unique assets. Morphology was selected before new angle fitting: flat rectangular plates with at least 3 by 4 visible stud caps, without decoration, transparent, curved or stacked top surfaces.

39 images passed morphology. The detector then identified at least 80% of the grid in 34. Visual review admitted 30 cap-center assets (1150 centers, eight books); four dark side/outline centroids are retained separately, and five segmentation failures remain visible in the private paper. This post-selection quality review is exploratory. Different files can share a render or part geometry; no pooled population p-value is reported.

Thresholds 15 through 245 in increments of 10 were scanned in both polarities. The main threshold is the midpoint of the longest maximum-coverage plateau; adjacent thresholds ±10 measure sensitivity. Connected-component filters: area 6–70 source pixels, width 4–13, height 2–8. The indexing seed has origin (12, (columns−1)·5.16+5.3), basis vectors (12.85,−5.16) and (8.9,7.55), and a gate of 0.32 grid units. This labels rows and columns; every final affine coefficient is free. Expanding the gate to 0.48 left all 30 primary landmark sets unchanged. These controls do not validate an arbitrary unseen orientation.

The source-to-page vertical/horizontal scale ratio is applied before equal-pitch affine/SVD angle recovery. Angle order is azimuth to the up-right grid direction, elevation. No-roll estimates, row/column deletions and common-center threshold controls are preserved privately. A homography is compared with affine prediction in three checkerboard folds and four column bands. Sixteen primary assets have three eligible thresholds, twelve have two, and two have one (a threshold requires at least 80% grid coverage). Ten of the sixteen complete three-threshold cases favor the homography in all common-center/fold-method comparisons. Twenty of thirty favor it across all available thresholds, but that mixes complete and incomplete sensitivity checks. Neither count has a prespecified minimum effect size or a significance interpretation.

The simplified detector control fixes an orthographic 35/35 camera and uses 4×4, 10×4 and 16×6 grids, sixteen subpixel phases, no JPEG / quality 90 / quality 70, and thresholds 120/140/160. All 432 runs recover complete grids. It is not a validated error model of LEGO's renderer.

## Numeric replay

Research dependency: NumPy. No official artwork or font is needed.

```sh
python tools/analyze_catalogue_camera.py --output /tmp/catalogue-camera-replay
```

The output directory must be new. The script recomputes all supplied trial angles and RMS values, checks agreement to 1e-10 degrees/pixels, and validates a 20/30 numerical projection control. It does not reproduce private PDF extraction, visual selection, plots or synthetic raster generation.

[Numeric source data](CAMERA-CATALOGUE-DATA.json) · [Synthetic control](CAMERA-CALIBRATION.json) · [Research paper](../RESEARCH-PREPRINT.md).
