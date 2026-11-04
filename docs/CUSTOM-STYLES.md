# Choose illustration colors

[CLI](CLI.md) · [Python API](API.md) · [Presentation presets](PRESETS.md)

A presentation preset controls paper, panels and labels. Since 0.6.0.dev1 the
default `research` material profile is generated from measured three-face data.
Named material profiles
and `--style` are mutually exclusive; both render and tray accept them.
[Measured anchors and extrapolation limits](MATERIAL-PROFILES.md).

 The separate `--style`
JSON controls the admitted material/face-color rules. Start from the included
complete schema; it is strict, so removing required keys or passing another
JSON format fails with a readable error.

## Try a small, self-contained variation

Run this from a checkout. It writes a new file and refuses to replace one:

```python
import json
from pathlib import Path

style = json.loads(Path("brick_blueprint/default-style.json").read_text())
style["palette"]["4"].update(
    side=[190, 50, 45],
    top=[230, 80, 75],
    front=[210, 60, 55],
    confidence="user-chosen illustration colors",
)
path = Path("output/custom-style.json")
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("x") as stream:
    json.dump(style, stream, indent=2)
    stream.write("\n")
```

```sh
python3 -m brick_blueprint render examples/demo.ldr \
  --library examples/library --style output/custom-style.json \
  --output output/custom-color-example
```

Open the PDF and retain `render.json`. The synthetic smoke model uses nominal
color 4, so the color change is visible without an external parts library. These
are illustration colors, not a calibrated match to a manufactured material.

For the kiosk, use its supplied assembly and your external library instead.
The same file applies to every occurrence of a material; there are no set/part
instance selectors or source-image sampling at render time.

## Which fields affect the current adapter?

| Fields | Current use |
| --- | --- |
| `palette.<LDraw color>.side/top/front` | Blend these RGB triples with the absolute X/Y/Z face-normal weights. Values are finite 0..255 numbers. |
| `fallback` | Materials absent from the palette retain the supplied library's nominal RGB. Only the explicit identity gains are admitted. |
| `stud_wall.rgb` | Illustration color for geometrically classified stud cylinder walls. Their opacity is kept opaque. |
| `explicit_colour.black_rgb` | Black convention for the supported explicit-color surface case. |
| `edges.light_if_nominal_Y_below` and `light_if_nominal_max_below` | Thresholds used by the adapter's light-ink polarity rule; the adapter also limits chroma. |
| `confidence` and `family` text | Required source/configuration metadata; not a measured quality score. |

The full schema also retains research/compatibility fields. `page`, `annotation`,
`arrows`, and identity `step_states` do not turn on page composition, arrows or
automatic instruction steps. The adapter does not take line width or ink RGB
from the inactive `edges.width_points`, `dark_rgb` and `light_rgb` fields. Use
`--line-width`; current ink colors follow the shared adapter rule, with a glass
contrast treatment. Keep the complete schema even for fields not connected to
an output control.

Page background, role-specific panel fills and quantity typography come from
`--preset` plus supported CLI overrides. `--background`, `--glass-opacity`,
`--line-width`, `--scale` and camera controls are independent of this material
file. A style hash may change when only metadata/reserved values change; that
does not imply the vector artwork changed. Compare actual output hashes.

## Error behavior and limits

The loader rejects a non-object palette, unsupported keys, invalid material
IDs, nonfinite/out-of-range RGB/thresholds, boolean scalar substitutes and invalid
metadata types before shading. Valid JSON is not necessarily a supported style.
Failed rendering leaves no final output folder; choose a new name for each
successful result. Ordinary Python call/argument errors may still use `TypeError`.

`render.json` records the exact style-file hash. This is provenance, not physical
color calibration or recovery of the publisher's complete shader. Rendering defaults to perspective and uses its documented glass-shell approximation.
The research profile deliberately does not apply opaque measured anchors to
transparent surfaces; those retain nominal RGB. The nominal stud-wall convention
remains opaque. Custom styles retain their explicitly supplied behavior.
