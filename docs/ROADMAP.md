# Open questions

## Camera and materials

- Extend the known-height camera experiment to higher-resolution parts and to more than two independently identified brick views. Cropping leaves the original optical center ambiguous.
- Test inclined and opposite faces on new materials with color coefficients fixed before measurement. Separately measure curved stud walls and outlines on dark surfaces.
- Measure transparent objects against multiple known backgrounds. That would help separate the glass from the ink and the objects behind it.

[Camera evidence](VOLUMETRIC-CAMERA.md) · [Color transfer](LDRAW-COLOR-TRANSFER.md) · [Angular materials](ANGULAR-MATERIALS.md)

## Instruction features

- Distinguish a new part from an existing assembly when generating a step view. The selection needs to survive projection and partial occlusion.
- Represent arrows, repeat counts and life-size guides through explicit roles. For a 1:1 guide, carry physical dimensions through to PDF and check a print at actual size.
- Evaluate additional LDraw input features against fixtures that exercise them. The supported MPD subset is documented separately.

[Annotation grammar](ANNOTATION-GRAMMAR.md) · [Multipart model support](MULTIPART-MODELS.md)

## Reproducibility

Run the prepared Linux and macOS workflows on the published repository. Compare native SVG/PDF geometry, rendered pixels and receipt fields separately when a compiler or library version changes. [CI configuration](CI.md) · [Reproduction guide](REPRODUCIBILITY.md)
