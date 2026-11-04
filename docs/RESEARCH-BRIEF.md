# Brick Blueprint in thirteen questions

Research brief 0.22 · 4 November 2026

[Full study](RESEARCH-PREPRINT.md) · [Illustrated FAQ](FAQ.md)

Each answer describes its measured sample.

## 1. Which projection fits the assemblies?

Perspective predicted held-out studs better in all 13 large views from 12 sets. On individual pieces its effect can be small.

[Projection study](RESEARCH-PREPRINT.md) · [Paper, p. 2](RESEARCH-PREPRINT.md#1-perspective)

## 2. Can one face predict the others?

For each measured left-face channel L, top ≈ min(255, 1.08 × L) and right ≈ min(255, 1.1144 × L). Across 17 colors, leaving one color out gave mean absolute errors of 1.56 and 1.22 RGB levels per channel.

[Face-color law](COLOR-LAW.md) · [Paper, p. 6](RESEARCH-PREPRINT.md#3-from-a-nominal-color-to-a-printed-face)

## 3. Can nominal LDraw RGB predict all three faces?

None of the tested conversions met the accuracy target. Mean error reached 15.75 RGB on 13 omitted colors and 17.75 on four new materials. The renderer uses measured face values for eleven materials.

[Palette study](LDRAW-COLOR-TRANSFER.md) · [Paper, p. 6](RESEARCH-PREPRINT.md#3-from-a-nominal-color-to-a-printed-face)

## 4. Which camera should I use?

The instruction preset uses a 35° azimuth, 35° elevation and 2° vertical field of view. Try instruction-depth at 5° for stronger depth. Two brick images support the working direction.

[Camera recipes](CAMERA-PRESETS.md) · [Paper, p. 4](RESEARCH-PREPRINT.md#camera-recipes)

## 5. Does part color change with the theme?

Eight recurring sloped elements differed by at most one RGB level between the sampled books. The paper behind the parts can change considerably.

[Cross-book controls](ANGULAR-MATERIALS.md) · [Paper, p. 7](RESEARCH-PREPRINT.md#inclined-faces-and-transparent-parts)

## 6. How do sloped faces get their colors?

The optional research-angular profile interpolates between measured directions. It passed eight prospective controls on two further geometries. Other orientations remain open.

[Inclined faces](ANGULAR-MATERIALS.md) · [Paper, p. 7](RESEARCH-PREPRINT.md#inclined-faces-and-transparent-parts)

## 7. Are the parts at a shared scale?

Two measured plates agree with a common scale. In a separate life-size guide the measured hole pitch was 8.009 mm against a nominal 8 mm. Print at actual size.

[Scale measurements](FAQ.md) · [Paper, p. 8](RESEARCH-PREPRINT.md#4-printed-pages-shared-scale-and-type)

## 8. Which color space do the books use?

Recent sampled image objects carry sRGB. Older Creator images from 2016 include CMYK with ISO Coated v2. Color space is a property of the individual PDF object.

[Color profiles](FAQ.md) · [Paper, p. 8](RESEARCH-PREPRINT.md#4-printed-pages-shared-scale-and-type)

## 9. How do the parts panels vary?

Fifteen presets describe a sample of 38 books. Edition and panel role matter within a theme. Measured borders span roughly 0.5–2 pt and include square, rounded and clipped corners.

[Page presets](PRESETS.md) · [Paper, p. 7](RESEARCH-PREPRINT.md#4-printed-pages-shared-scale-and-type)

## 10. Can we recover ink width and glass opacity?

The pictures show light outlines on dark pieces and milky glass. Flattening, pixel size and the underlying background prevent a unique estimate of source stroke width or opacity here.

[Ink and glass](MATERIALS-AND-EMPHASIS.md) · [Paper, p. 7](RESEARCH-PREPRINT.md#inclined-faces-and-transparent-parts)

## 11. Which fonts match the quantity labels?

Six inspected label runs used 8 pt type. Of four freely available families examined, Outfit Bold was closest to LEGOChalet60-Bold, and Jost Medium to CeraPro-Medium.

[Type specimens](FONT-STUDY.md) · [Paper, p. 8](RESEARCH-PREPRINT.md#4-printed-pages-shared-scale-and-type)

## 12. Do the observed bricks agree with 35°/35°?

Joint tests of both angles gave bootstrap p = 0.943 (11038) and 0.640 (11037), conditional on independent Gaussian corner errors. Two images support a working direction.

[Angle test](CAMERA-PVALUES.md) · [Paper, p. 4](RESEARCH-PREPRINT.md#testing-the-35-direction)

## 13. How does it compare with LDView?

The camera comparison aligns geometry, viewpoint and frame. Our measured palette gave 1.01 RGB mean face-patch error on twelve held-out images. Overall visual similarity requires a separate test.

[Material validation](MATERIAL-PROFILES.md) · [Paper, p. 9](RESEARCH-PREPRINT.md#6-comparison-with-ldview)
