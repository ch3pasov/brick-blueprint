# Color on inclined surfaces

The measured axial palette does not, by itself, define the color of a slope.
For the three directions sampled here, a shared affine rule from the measured
dark vertical face transfers across several materials. It is a bounded result,
not a recovered lighting system or a universal LDraw-to-LEGO transform.

## Evidence and controls

The sample contains **50 source occurrences, 44 distinct decoded images,
22 material classes and 14 sets from seven themes** (2020–2025). Six exact
image repeats are retained as reuse evidence and excluded from the unique-image
summary. Distinct encodings are not assumed to be independent rendering jobs.

We measure flat, opaque, unprinted slope interiors and an adjacent vertical
face in the native PDF images. Every selected image has the same embedded sRGB
profile. Rectangular windows are fixed before measurement; all nine ±1-pixel
window shifts are retained. The descriptive acceptance rule is MAE ≤3 RGB
levels and maximum channel error ≤10 for every shift. These shifts are
sensitivity conditions, not independent observations or confidence intervals.

The normal comes from DAT geometry and the illustrated orientation. Part names
are insufficient: the sampled `3298` and `4286` DAT slopes rise 20 LDU over 40 LDU,
which is 26.565° to horizontal, despite the nominal “33” name. Also, the same
`3037` design is shown facing different sides in different catalogue images.

## A rule from a measured dark-face color

For each RGB channel, `slope = clip(gain × dark_face + bias, 0, 255)`.
The input is the separately measured axial dark-face color, **not the nominal
RGB from LDConfig.ldr**. The same gain and bias apply to all three channels.

| Surface direction in the reference view | Gain | Bias | Neutral training |
|---|---:|---:|---|
| Left-facing 45° | 1.0166343 | −0.7151300 | Black and white |
| Left-facing 26.565° | 1.0825688 | −0.5504587 | Black and light gray |
| Right-facing 45° | 1.1192661 | 4.8715596 | Black and light gray |

Across the **28 unique images with an admitted axial palette**, central MAE is
0.723 RGB and all 28 pass every window shift. This summary includes training
and exploratory images; it is not an independent validation score.

The coefficients were frozen before measuring five further source images with
available palette inputs. All five pass every shift; central MAE is 0.945 RGB,
and the worst shifted MAE is 2.685. They cover white, red, yellow and black,
including a different-width white slope. These are new source/geometry
controls with already known materials, not five new material classes.

## Why another visible face can be a poorer input

A separate neutral-trained affine rule uses the adjacent vertical face of the
same image. It passes 40 of 44 unique images, including 14 of 15 fresh pixel
controls. The failures are yellow/yellow-orange examples with nearly saturated
input channels. A bright face near 255 loses information needed to infer a
different face; the dark-face input avoids that particular ambiguity here.
This supports the choice of input, but does not prove clipping is the sole
source of every residual.

## Why the present interpolation is insufficient

A convex average cannot exceed its brightest anchor. Yet a sampled black
right-facing slope is 53, above the axial maximum 48. A light-gray slope is 175,
above the axial maximum 170. The current interpolation predicts 47 and 167.
This is direct evidence against that interpolation for these surfaces.

Seven private native-vector probes apply the frozen formula only at the three
sampled normals. Model geometry, camera, outlines and axial colors match each
baseline/probe pair, and the predicted fills are verified in the SVG/PDF.
The default renderer still uses its declared axial interpolation extension.
The discrete probe is not a validated continuous shader. Additional directions
are tested below; the opposite side and transparency remain unresolved.
Right-facing 45° has only three sampled images and no fresh
prospective material holdout.

## Prospective tests at additional inclinations

An additional 45 occurrences from 21 sets and 11 themes contain 39 distinct
decoded images; 38 have admitted palette inputs. Exact DAT planes give
18.435°, 30.964°, 65.556° and 73.610° inclinations. Predictions and windows were
frozen before the new RGB measurements. The four rules are the default axial
convex blend, linear interpolation in angle between measured directions,
normalized sine weights between adjacent normal directions, and a polynomial
through the directional anchors (left cubic, right quadratic).

| Rule | Steep 65.6°/73.6°: MAE; pass | Shallow 31°: MAE; pass | Low 18.4°: MAE; pass |
|---|---:|---:|---:|
| Default axial blend | 2.358; 6/10 | 1.145; 26/26 | 6.875; 1/2 |
| Linear in angle | 4.266; 4/10 | 1.122; 23/26 | 4.235; 1/2 |
| Sine weights | 4.264; 4/10 | 1.110; 23/26 | 4.199; 1/2 |
| Global polynomial | 10.775; 0/10 | 1.360; 23/26 | 2.384; 1/2 |

The 31° group has nine primary element/shape classes. The default passes 9/9
with MAE 1.000; each alternative passes 8/9. Repeated colors cannot hide the
white-class failure. Both 18° images show design 30363, but white faces right
and black faces left: color and direction are confounded. The white slope is
(251,252,254), brighter than all its axial anchors, and none of the four rules
passes its windows. The black image passes all four.

Three private native-vector pairs verify the current and continuous angular
rule with identical geometry/camera in each pair. The latter applies only on
the two examined principal-normal sectors; it is not a validated full shader.
Formula errors and the additional ≤0.5-level quantization to vector RGB fills
are recorded separately. **The angular alternatives are not promoted:** they
worsen several unseen directions. A complete lighting law is still unresolved.

## Same element across themes

Eight elements repeat across different books in the 31° group. Every channel's
measured span is at most one RGB level, including all window shifts. Backgrounds
differ, while the interior part colors agree. This supports shared part colors
for those examples; it does not establish independent rendering jobs. Different
full-image hashes can arise from background and compression changes.

## Reproduce the arithmetic

```sh
python3 -I -S tools/analyze_sloped_faces.py
python3 -I -S tools/analyze_angular_shading.py
```

[Numeric data, source URLs, hashes, ROIs and every shifted result](research/SLOPED-FACE-STUDY.json).
The portable replay checks 4,999 arithmetic/provenance conditions. The private
source audit independently checks 7,056 conditions against PDF pixels; the
native probe checks 133 conditions. None of these counts is a sample size.
Official images are not included in this repository.

[Additional directions: numeric data, sources and all shifted results](research/ANGULAR-SHADING-STUDY.json).
The additional-direction replay checks 5,489 arithmetic conditions; the private
PDF source audit checks 8,009 and the native control pairs check 69. These are
audit counts, not statistical sample sizes. Original figures and complete
page context remain in the private research workspace.


## Opt-in continuous slope colors

The `research-angular` profile implements the subsequently tested piecewise linear-light rule, with explicit white calibration and eight prospective geometry controls. The default `research` profile retains the three-face blend. [Implementation, matched vectors, cohort accounting and limits](ANGULAR-MATERIALS.md).
