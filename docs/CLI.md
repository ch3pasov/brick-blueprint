# CLI reference

[Quickstart](QUICKSTART.md) · [Python API](API.md) · [Print](PRINTING.md)

Run `python3 -m brick_blueprint --help` and append a command plus `--help` for
its exact accepted options. After installation, `brick-blueprint` is equivalent.

| Command | Input | Result |
| --- | --- | --- |
| `doctor` | Optional library and model | Readiness JSON and success/failure exit code |
| `presets` | None | All measured presentation presets as JSON |
| `camera-presets` | None | Camera recipes, settings and evidence as JSON |
| `render` | Flat LDraw or assembly-only MPD | SVG, PDF, dependency/render receipt |
| `tray` | Explicit JSON item list | Common-scale vector parts grid |
| `print` | This renderer's SVG | Separate RGB, gray or ICC CMYK PDF |

## Diagnose a checkout

```sh
python3 -m brick_blueprint doctor
python3 -m brick_blueprint doctor --compile
python3 -m brick_blueprint doctor --library /path/to/ldraw --model my-model.mpd
```

Default checks read data and query the compiler version; they do not compile,
download, open an application or create a cache. `--compile` explicitly builds
both bundled native programs in `--cache-dir` (default `.brickblueprint-cache`).
A detected compiler version is not proof of C++17 support; the explicit compile
check supplies that evidence. Optional Pillow absence does not fail core readiness.
The optional section reports the Pillow distribution version and whether it
meets the declared Python 3.11+/Pillow 13+ print-extra policy. An older installed
Pillow version does not fail core readiness or trigger an upgrade. Unknown/dev
distribution versions remain unclassified. Model preflight reads recursive
geometry and colors; it does not certify a build.
Use a Python 3.10+ interpreter; `doctor` reports the interpreter actually running.

## Render controls


| Control | Purpose |
| --- | --- |
| `--preset modern-blue` | Page and panel presentation |
| `--camera-preset instruction` | Weak perspective 2°; independent of paper style. Alternatives: `instruction-depth`, `presentation`, `orthographic`. [Details](CAMERA-PRESETS.md) |
| `--layout illustration` or `callout` | Full illustration or a single model with quantity |
| `--panel-role parts` or `subassembly` | Role-specific panel, where observed |
| `--width 600 --height 450` | Canvas in points; each dimension 64–1000 |
| `--azimuth 35 --elevation 35` | Camera direction; LDraw up is negative Y |
| `--projection perspective` | Pinhole projection. Use `orthographic` for a parallel view with constant scale at every depth. |
| `--field-of-view 30` | Vertical full-page FOV; perspective only |
| `--camera-distance 500 --camera-target=0,0,0` | Explicit eye distance and target in LDU; render only |
| `--camera-roll 0 --principal-point=300,225` | Source-specific camera replay; principal point requires explicit distance; render only |
| `--near-clip 0.1` | Reject geometry this close to the eye; perspective only |
| `--line-width 0.32` | Outline thickness in page points |
| `--glass-opacity 0.8` | Transparent-shell opacity; opaque stud walls stay opaque |
| `--background D4EDFC` | Override page color while retaining panel fill |
| `--scale 0.35` | Points/LDU at target plane; uniform in orthographic; excludes camera distance |
| `--material-profile research` | Default measured eleven-color profile; `research-angular` adds the opt-in empirical slope rule.  Applies to render and tray. |
| `--style my-style.json` | Admitted palette/material rules; [active fields and example](CUSTOM-STYLES.md) |
| `--png` or `--png-dpi 300` | Add `model.png` to a model or tray render. `--png` uses 144 DPI. The accepted range is 1–600 DPI. Install with `python3 -m pip install ".[png]"`. |
| `--underpaint` | Add inset paths behind opaque faces to suppress pale seams at small display sizes. Works with render and tray. [Visual comparison](PORTFOLIO.md#opaque-surfaces-at-screen-size) |
| `--no-detail-filter` | Retain small annular detail lines |
| `--timeout 300` | Timeout per native render/union stage |

Supported: assembly-only MPD containers, recursive DAT geometry, BFC winding, mirrored transforms, ordinary and conditional edges, visibility, transparent shells, polygon union, compact SVG and direct PDF.

Not yet supported: embedded custom DAT geometry, separate neighboring model files, TEXMAP, space-optimized inventory packing, step generation, arrows, progress bars, 1:1 measurement guides or interactive editing. Research documents these graphics without claiming they are implemented. Oversized fixed-scale models are rejected rather than cropped. Complex overlapping glass can still be expensive. [Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md)


## Tray totals

Tray JSON reports `items` (distinct displayed entries), `rendered_parts`
(geometry placements drawn once per entry) and `represented_parts` (placements
multiplied by each entry's quantity). A 16-entry kiosk BOM therefore represents
41 parts. These arithmetic totals do not establish that multiple depicted
assemblies share a valid inventory or form one physical build.
