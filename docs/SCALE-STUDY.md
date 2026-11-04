# Inventory scale and physical-size references

This follow-up measures three illustrations on already-registered pages. It separates **shared inventory scale**, **projected image size** and **a physical 1:1 reference**. These are different requirements. No new pages are added to the corpus count, and no accepted model or renderer default changes.

## Two different plates in one inventory

[Star Wars 75375 official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6509377.pdf), PDF page 20, printed step 27, shows a tan 2×4 plate and a gray 1×4 plate in the same inventory. Both have a four-stud row with closely matched projected direction.

First/last top-cap centers were selected in the **original embedded images**, which are only 98×59 and 86×49 pixels. The native PDF placement converts pixel displacement to page points. Each row spans three stud intervals. The comparison uses matching directions; it does not infer physical scale from the outer image rectangle.

| Illustration | Projected stud pitch | Sensitivity to ±1.5 original pixels per endpoint coordinate |
|---|---:|---:|
| Tan 2×4 plate | 9.13 pt | 8.51–9.76 pt |
| Gray 1×4 plate | 9.09 pt | 8.47–9.71 pt |

The point-estimate ratio is 1.004; the conservative independent endpoint envelope is approximately 0.88–1.15. **The observations are consistent with shared scale, but do not establish exact equality.** Magnifying the source image does not reduce this uncertainty. This is one inventory comparison, not a universal claim about every part or theme.

[Landmarks, image hashes and PDF placements](INVENTORY-SCALE-MEASUREMENTS.json) make the measurement reproducible. Source images remain local. The tool's shared points-per-LDU rule is explicit and testable; the publisher's inferred rule remains bounded by the available evidence.

## A 1:1 beam is a stronger dimensional reference

[Technic 42221 official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6621082.pdf), PDF page 10, has a side-on 13-hole beam reference labeled `13` and `1:1`, separate from the oblique inventory picture above.

The reference is an opaque 615×48-pixel image placed 294.9598 pt wide. Thresholding the bright hole interiors on nine central rows at three thresholds identifies thirteen centers. First-to-last center span covers **twelve intervals**, not thirteen. The resulting pitch is approximately **8.01 mm** at native PDF size. Threshold choices produce 7.994–8.009 mm; allowing ±1 original pixel at each end gives a wider 7.980–8.037 mm sensitivity range.

That agrees with nominal 8 mm pitch at this measurement precision. The [LDraw specification](https://www.ldraw.org/article/218.html) defines a brick width/depth of 20 LDU and lists 0.4 mm/LDU as a real-world approximation. Neither this comparison nor that approximation certifies a physical printed sheet.

## A length badge is not an exact silhouette dimension

On PDF page 16, the yellow axle reference is labeled `3` and `1:1`. It is drawn with native filled contours, so the yellow face and outer black ink can be measured separately:

- Yellow fill width: **23.21 mm**.
- Outer black ink width: **23.36 mm**.

Those values are not exactly `3 × 8 = 24 mm`. Do not stretch a silhouette to nominal pitch times a length-class badge, or diagnose a printing error from that shortcut alone. End geometry, contour selection and drawing normalization must be considered. This audit does not identify the cause of the difference, verify a particular CAD axle revision or measure a physical axle.

[Reference measurements](REFERENCE-SCALE-MEASUREMENTS.json) preserve the native contours' bounds, source hash, image placement, threshold sweep and assumptions. The source axle's outline is intentionally not copied into the project.

## The page itself has a physical size

Both inspected Technic pages are **195 × 259 mm**, with PDF user unit 1 and no rotation. “Fit to page” on a different paper format can invalidate the reference scale. In the idealized case of fitting this entire page to borderless A4, the width-limited scale would be `210 / 195 ≈ 1.077`: about a 7.7% enlargement. Actual printer margins and viewer settings can produce a different result.

For a future 1:1 tool feature, store the part and measurement axis, generate a dedicated side-on view, label actual-size printing, and validate geometry plus page units. Inventory fit and model presentation cameras must not silently control the reference. The current renderer exposes scale and exports physical PDF dimensions, but **does not yet generate or certify 1:1 measurement guides**.

[Printing guide](PRINTING.md) · [Camera study](CAMERA-STUDY.md) · [Annotation semantics](ANNOTATION-GRAMMAR.md)
