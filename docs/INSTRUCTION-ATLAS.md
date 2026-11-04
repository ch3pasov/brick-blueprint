# Instruction atlas: what each book actually does

[Expanded projection study](PROJECTION-EXPANSION.md): seven large step illustrations, six sets, five themes, with native-image landmarks and spatial holdout checks. These pages were already in the sampled corpus; this adds measurements, not new books.

This atlas separates **observation**, **interpretation**, and **tool support**. The base atlas covers 23 official PDFs across thirteen themes. Its 106 distinct pages comprise 97 build or feature pages and nine additional pages used to compare matching parts. The paired study extends the collection to 38 books. The newest sampled sets are from 2026. We inspected complete pages and selected details, not every page in every book. PDF indices below are one-based; source hashes and sampling lists are in [STYLE-SOURCES.json](STYLE-SOURCES.json).

[Palette study](STYLE-RESEARCH.md) · [Part illustration guide](PART-ILLUSTRATION.md) · [Gallery](GALLERY.md) · [Camera measurements](CAMERA-STUDY.md) · [Materials and emphasis](MATERIALS-AND-EMPHASIS.md)

See the [2026 longitudinal comparison](EDITION-COMPARISON-2026.md) for Creator 31376, Botanicals 11508 and Technic 42221, including the green rounded Botanicals counterexample.

The [theme-control study](THEME-CONTROLS.md) adds Architecture 21062, Minecraft 21269 and the larger Star Wars 75375 book, with an explicit advertising-page exclusion.

## Creator — 31051 Lighthouse Point, 2016

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6167581.pdf), sampled pages 18, 22, 74 and 78.

- Pages 18 and 22: pale blue page, darker rounded blue inventory, fine dark frame. Counts use the PDF-identified LEGOChalet60-Bold at 8 pt; main step numbers use 38 pt. The tray contains genuinely different part sizes, not equal-sized icons.
- Page 74: step 139 shows the lantern's light function separately in a red-framed inset with a yellow star. The glass is an illustration treatment that lets the mechanical interior remain understandable. The symbol communicates light; it is not a simulated optical effect.
- Page 78: an exploded presentation separates major tower and coastal modules. Vertical ordering explains how the tower stacks. This is a module relationship view, not a list of raw parts or a new numbered assembly sequence.

**Use in the tool:** `creator-blue`, quantity labels, shared-scale trays and tunable glass. Automatic light symbols and exploded module layout remain future work.

## Creator — 31139 Cozy House, 2023

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6456165.pdf), sampled pages 11, 25 and 60.

The page blue stays close to the older lighthouse book, while the tray blue, border and typography change. CeraPro-Medium replaces Chalet in the sampled labels. Cream secondary panels hold assembly operations; white cards have a contextual role. Red arrows describe local insertion, while thin leaders connect the inset to the larger model. A blue footer strip tracks progress.

**Interpretation:** a newer edition may change typography and small presentation details without changing the theme's recognizable page color. The inset can have its own scale; that does not justify independently scaling parts inside a single inventory.

**Use:** `modern-blue`, with separate parts/subassembly roles.

## Creator — 31169 Typewriter with Flowers, 2025

[Official PDF, main model](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6556274.pdf), sampled pages 9, 10, 20, 30 and 40.

Pages 9–10 show the underside of a wide plate assembly. The useful face of the model determines the camera: the drawing does not preserve a top-down view merely for stylistic consistency. Page 20 uses a cream local assembly card; page 40 combines a faded contextual module, an inventory and a numbered subassembly sequence. Counts remain 8 pt CeraPro-Medium, and the main page/tray palette matches modern Creator and City.

**Use:** added as a third evidence source for `modern-blue`, not a redundant new preset. Per-item tray camera overrides support identification views; automatic context ghosting and rotation icons are not implemented.

## City — 60404 Burger Truck, 2024

[Official PDF, book 1](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6490981.pdf), sampled pages 10, 20 and 40.

The blue page/tray system is shared with contemporary Creator. Some pages are split by a thin vertical rule; the progress strip includes a character. Step-number font metadata is CeraPro-Medium. Not all quantity labels on these pages are extractable text, so their exact font is not independently established here.

**Use:** also maps to `modern-blue`. Separate theme names should not force a duplicate palette when the measured presentation is shared.

## Classic — 10692 Creative Bricks, 2015

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6117826.pdf), sampled pages 8, 12 and 20.

The build artwork uses a warm yellow background with texture/gradient and a yellow footer. The inventory is cyan. Page 12 is promotional, not a build step. The PDF includes white margins and prepress marks outside the artwork: these dominate a naive pixel histogram but are not the page design. Labels identify LEGOChalet60-Bold, with 8 pt counts and 32 pt main step numbers in the measured examples.

**Use:** a historical comparison only. A flat yellow preset would omit a material part of this design, so it is not advertised as implemented.

## Classic — 11038 Vibrant Creative Brick Box, 2024

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6509312.pdf), sampled pages 8, 12 and 20.

White page, blue parts tray, rounded dark frame and CeraPro-Medium. Multiple independent small builds can share a page, separated by a fine rule. There is no progress strip on the sampled pages. The visual emphasis is on simple, readable geometry and quantities.

**Use:** `classic-white`. The white background is useful for technical comparisons and less ink-heavy printing, but we have not measured printer ink use.

## Star Wars — 30654 X-Wing Starfighter, 2023

[Official instruction download](https://www.lego.com/en-us/service/building-instructions/30654), both pages of the foldout.

A compact gray foldout arranges many small steps into a reading sequence. Orange panels describe repeated subassemblies, with repetition counts such as 2x/4x; there is no ordinary separate parts-tray header in this sampled format. White flow arrows and rotation symbols help navigate the dense page.

**Use:** `starwars-foldout` defaults to a subassembly card and rejects a parts tray. It is a specific small-format preset, not a claim about large Star Wars booklets. Its normalized quantity size differs from the source's larger repetition labels.

## Fortnite — 77073 Battle Bus, 2024

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6541111.pdf), sampled pages 12, 25 and 50.

A lilac page contains deeper lilac inventory trays and green subassembly panels. White context cards, a purple progress strip and character/completion graphics add hierarchy. Page 12 shows differently sized plates at compatible projected stud pitch; the lower assembly view has a different scale.

**Use:** `fortnite-lilac`. The palette and panel roles are supported; character graphics and completion effects are neither copied nor generated.

## Technic — 42167 Mack LR Electric Garbage Truck, 2024

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6495267.pdf), sampled pages 10, 20 and 40.

Gray page, white inventory and cream subassembly panels. Length badges distinguish visually similar axles/beams. Separate 1:1 references use physical scale, while the main assembly remains an illustrative view. Red arrows show insertion; thin black lines relate insets to their destinations. The progress indicator is restrained and mechanical in character.

**Interpretation:** a part's identifying feature may be its hole count or shaft length. A technically attractive three-quarter view is insufficient if it hides those features.

**Use:** `technic-gray` plus explicit physical scale. The tool does not yet generate calibrated 1:1 rulers, length badges or insertion constraints.

## Friends — 42604 Heartlake City Shopping Mall, 2024

[Official PDF, book 1](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6493646.pdf), sampled pages 10, 20 and 40.

A pale aqua page uses a darker aqua inventory with a conspicuous teal frame, about 2 pt in the measured source contours. Page 10 also contains a purple local assembly inset/arrow, with a purple border rather than teal. White context cards use a separate treatment. The count and main-step text identify CeraPro-Medium, at 8 and 26 pt respectively.

**Use:** `friends-aqua`, including a role-specific purple subassembly border. The stronger panel border does not thicken the model's outlines.

## Botanicals — 10281 Bonsai Tree, 2021

[Official PDF revision inspected](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6532381.pdf), sampled pages 10, 20, 30 and 40. The set year is 2021; a downloadable PDF's revision can be newer than the set launch.

The interior build pages are gray, not the black background one might infer from adult-set packaging. Inventory boxes have square corners, the same gray fill as the page and thin dark outlines. White assembly/context boxes stand out. The sampled font is LEGOChalet60-Light: an explicit counterexample to the idea that all instruction quantities are bold. Page 40 uses contextual images to explain how curved trunk sections join.

**Use:** `botanicals-gray`, with regular Helvetica as a disclosed substitute for the light source font.

## Botanicals — 10343 Mini Orchid, 2025

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6555769.pdf), sampled pages 10, 14, 20, 30, 36 and 40.

Gray page and square inventory frames continue, but the font metadata now identifies CeraPro-Light. Page 14 combines a white 2x subassembly box, a rotation symbol, red insertion arrows, a thin leader and blue emphasis on the receiving assembly. Pages 30 and 36 show repeated connectors with 3x labels, explicit assembly order and placement on a curved stem. Page 40 is a finished-model presentation rather than a parts step.

**Interpretation:** light typography can be an audience/edition treatment without implying a separate geometry renderer. Blue contours may communicate a current-step emphasis; changing material color to blue would lose that meaning.

**Use:** the same `botanicals-gray` preset; step emphasis is documented but not implemented.

## Speed Champions — 77240 Bugatti Centodieci, 2025

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6598214.pdf), sampled pages 10, 20, 30, 40, 56 and 72.

Gray pages have darker gray inventory panels with **four clipped corners** and a tonal/beveled edge. Cream secondary panels share the clipped-corner language. Page 56 sequences a small assembly in a panel and connects it to the car. Page 72 uses curved yellow arrows to communicate a movement/rotation rather than introducing new parts. The step-label typography is CeraPro-Medium.

**Use:** `speed-chamfer` reproduces the polygonal corner shape and sampled flat colors. The multi-tone border is simplified to a uniform stroke, and the pale inset's variation is normalized to one sampled fill. These are disclosed approximations.

## NINJAGO — 71832 Thunderfang Dragon of Chaos, 2025

[Official PDF](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6566338.pdf), sampled pages 10, 20, 30, 40, 100 and 120.

A peach page contains orange inventories with **top-left and bottom-right corners clipped**. Gray subassembly panels and white faded context cards have distinct roles. Page 100 shows repetition and several short sequential steps. Page 120 combines a length badge, a dedicated 1:1 axle reference, a multi-step spring mechanism and a caution symbol. It demonstrates that measurement aids are not exclusive to sets branded Technic. Counts/steps identify CeraPro-Medium; sampled page numbering includes LEGOTypewellArchive-Bd.

**Use:** `ninjago-peach` reproduces the two-corner panel geometry and role palette. Safety symbols and 1:1 mechanism diagrams are not automatically inferred.

## DREAMZzz — 71488 Bunchu's Creative Animal Adventures, 2025

[Official PDF variant inspected](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6553546.pdf), sampled pages 10, 20, 30, 34, 38, 40 and 66. The download page offers more than one PDF variant; this claim is about the identified file.

The main build uses a warm textured page, cream rounded inventory and prominent yellow routing/assembly graphics. Page 30 makes a repeated subassembly conspicuous with a thick yellow frame and leader; page 34 emphasizes the placement of an accessory. Page 38 presents a pile of reusable pieces, inviting rebuilding. Alternate builds on pages 40 and 66 use blue textured fields with story characters and different reading structure.

**Interpretation:** one theme name and even one booklet do not imply one flat background. Narrative and branch state are part of the presentation model.

**Use:** research only. No texture or branded character artwork is copied into the project, and no misleading single-color DREAMZzz preset is claimed.

## Feature-to-evidence index

| Question | Useful pages | What a renderer/composer must preserve |
| --- | --- | --- |
| How large should each inventory item be? | 31051 p18/22; 31139 p11; 77073 p12 | Common physical scale within the tray; quantities separate from dimensions |
| When should the camera change? | 31169 p9–10; 10343 p14 | Show the attachment face; make a model rotation explicit in a sequence |
| How do repetition counts work? | 10343 p14/30/36; 71832 p100; 30654 foldout | Distinguish quantity of a part from repetitions of an assembly |
| How are small details explained? | 42167 p40; 71832 p120 | Dedicated length/1:1 references, not arbitrary enlargement in the inventory |
| What do arrows mean? | 10343 p14/36; 77240 p72; 71488 p30/34 | Insertion, routing/association and rotation are different operations |
| How is an earlier module referenced? | 31169 p40; 71832 p10/20 | Context card and subdued illustration, separate from new inventory |
| How are translucent parts shown? | 31051 p74 | Readable shell and interior; effect icon separate from material rendering |
| How can a whole model be decomposed? | 31051 p78 | Rigid subassemblies and assembly order; exploded spacing is explanatory |
| Are adult instructions black? | 10281 p10/20; 10343 p10/20 | Packaging color does not determine interior-page color |
| Does one theme equal one style? | 71488 p30 vs p40/66; Classic 10692 vs 11038 | Branch, format and edition belong in the style model |

No layout observation here certifies the physical correctness of our reconstruction or derives assembly instructions automatically from a finished model.

## Quantitative scale follow-up

The [scale study](SCALE-STUDY.md) uses existing sampled pages: 75375 p20 for two inventory plate pitches, and 42221 p10/p16 for physical-size reference measurements. It adds no books or pages to the corpus totals.

The [large-grid camera audit](LARGE-GRID-STUDY.md) reuses 21062 p20 and compares affine/projective fits on held-out cap centers. It does not add pages to the corpus.

The follow-up also measures the complete 4×10 inventory plate on already-registered 75375 PDF page 60. Its weaker threshold-sensitive result is retained as a control, not discarded. See [large-grid camera study](LARGE-GRID-STUDY.md).

## Identical parts across themes

The [matched-part study](PART-COLOR-STUDY.md) adds 7 end-inventory pages and 2 new step pages; the third step page, 75375 p20, was already sampled. Four opaque elements and a three-theme per-step brown-brick control show shared palettes/reused part assets despite different backgrounds. Exact sampled page lists are recorded per source.

## Illustrated FAQ and font-label follow-up

The [FAQ](FAQ.md) gathers thirteen practical answers with original diagrams and a typed [constants index](FAQ-CONSTANTS.json). The [free-font comparison](FONT-STUDY.md) adds label-only inspection of five pages: 31051 p8/p13 and 31376 p5/p6/p8. These are recorded separately from the 106 full-page style/color samples. Four OFL font downloads have source/license hashes; source labels remain private. The independent 75375 p60 grid yields a conditional approximately 35°/35° view, without establishing a universal camera.

## Paired-source and shading follow-up

[16 same-theme/year presentation pairs](PAIRED-THEME-STUDY.md), [ten-color face shading](SHADING-STUDY.md), and [actual-step gallery evidence](ACTUAL-STEP-EXAMPLES.json) extend the earlier samples. Earlier page counts refer to their historical study, not the enlarged 38-book corpus.
