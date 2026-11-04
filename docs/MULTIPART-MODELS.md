# Models with reusable subassemblies

Brick Blueprint accepts an **assembly-only subset of MPD**: one file contains named `.ldr`/`.mpd` blocks, each made of type-1 placements. The first block is the main model; referenced blocks are expanded recursively. Unreferenced blocks are not rendered. This follows the container structure in the [official LDraw MPD specification](https://www.ldraw.org/article/47.html); it does not claim support for every legal MPD payload.

```sh
python3 -m brick_blueprint render examples/garden.mpd \
  --library /path/to/ldraw --output output/garden-mpd \
  --preset creator-blue --width 400 --height 330
```

The [multipart garden](../examples/garden.mpd) has exactly the same 41 placements as [the flat example](../examples/garden.ldr). Ground and garden-top placements are separate internal blocks; this grouping is for file organization, not a recovered assembly sequence or independent validation of connections. The native projected scene hashes match.

## Supported behavior

- Forward references, nested assemblies and repeated instances.
- Parent/child translation and matrix composition, including rotations and mirrored transforms.
- Color 16 inheritance from the enclosing assembly; explicit child colors override it.
- Case-insensitive names, spaces in names and normalized slash/backslash separators.
- `0 FILE`/`0 NOFILE` boundaries. Prose outside blocks is ignored; geometry before the first block is rejected.
- The final leaf placements retain their root insertion step. A child `STEP` does not advance the main timeline. This renderer shows the final model; it does not generate assembly steps.
- Full container SHA-256 and a `model_structure` receipt record the format, root, declared/used blocks and expanded part count. Tray items retain this receipt too.

Root color 16 remains unresolved unless the enclosing placement supplies a concrete color. The renderer does not invent a default model color.

## Explicit boundaries

Only embedded **assembly blocks** are expanded. Leaf DAT files still come exclusively from the explicitly supplied external parts library. Embedded `.dat` replacements, raw type 2–5 geometry in model blocks, model-side BFC INVERTNEXT, placement color 24, TEXMAP and embedded image data are unsupported and fail explicitly. This is not yet a general OMR/unofficial-part importer.

Separate neighboring `.ldr` files are not searched. A missing `.ldr`/`.mpd` reference is an error; nothing is read from arbitrary paths or downloaded. Duplicate names after case/slash normalization, traversal references, reachable cycles, singular and nonfinite transforms are rejected. Unsupported geometry inside an unreferenced assembly is not parsed because it is not part of the rendered scene; global unsupported data/texture declarations still fail.

Current limits:16 MiB input,1024 named blocks,64 expansion levels,100,000 expanded assembly calls and 100,000 leaf parts. These bounds protect model expansion; they are not a total renderer-memory guarantee. Referenced DAT geometry can itself be large.

## Verification

Independent hand-calculated nested rotation/reflection coordinates and color/step expectations are tested. A separate native comparison renders an MPD and a manually flattened equivalent: projected scenes, final SVG and final PDF match exactly. Repeated instances, forward references, mixed-case/spaced names, missing/unsafe references, duplicate names, cycles, overflow, explicit unsupported input and expansion limits have regression coverage.

The real 41-part garden also gives identical projected scene hashes for flat and multipart inputs. Its own vector output is inspected separately; no official illustration is copied into this example.
