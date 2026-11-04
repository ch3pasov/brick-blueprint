# Lighthouse Point

Two houses stand next to the striped tower. A whale approaches the landing, and a bird perches on the lantern roof. This scene has 537 LDraw placements. The LEGO Group designed set 31051 and published its building instructions. The scene was reconstructed for this project using geometry by LDraw part authors. The figures have simplified details. Anatolii Chepasov developed the Brick Blueprint renderer used to draw the scene. [Model](../examples/lighthouse.ldr) · [Instruction, page 77](https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6167581.pdf#page=77)

[![A lighthouse, two blue houses, two figures and a whale, all drawn as vector paths](images/lighthouse-point.svg)](images/lighthouse-point.svg)

## Render the full scene

Run these commands from the checkout root with a complete LDraw library. The first writes the full-precision SVG, native PDF and render receipt. The second makes the lighter web illustration shown above.

```sh
python3 -m brick_blueprint render examples/lighthouse.ldr \
  --library /path/to/complete.zip --output output/lighthouse \
  --camera-preset instruction --width 590 --height 400 \
  --line-width 0.5 --glass-opacity 0.7 --underpaint --background '#d4edfc'

python3 tools/compose_lighthouse_plate.py output/lighthouse output/lighthouse-web.svg
```

The receipt records all 537 placements, the external geometry and material revisions, the camera and the vector output hashes. This illustration reuses the checked-in scene. It has no separate physical build test. [Toolchain, geometry credits and reproduction records](gallery/lighthouse-vector.json)

## How the smaller SVG was checked

The renderer placed the paths on a 0.001-unit grid. The web edition writes those positions as integers and enlarges the SVG coordinate system by the same factor. Each path is decoded again and compared with the renderer's commands before saving. All **493,499 commands across 906 paths** match in order and position, including repeated vertices and closed contours. The file shrinks from **5.22 MB to 3.12 MB**. Colors, opacity and drawing order carry through from the render.

The two files can be compared at display widths from 320 to 3,000 pixels. A viewer can round edge pixels differently even when the coordinates agree. [Per-viewer pixel checks, file sizes and source hashes](gallery/lighthouse-vector.json)

We also rendered the full scene on arm64 macOS with Apple clang 21 and on Alpine Linux with GCC 15.2. At the same four display widths, the largest single-channel pixel difference between the two web plates was 7 levels out of 255. The mean per-channel difference over the page stayed below 0.001 at each size. [Cross-platform measurements](gallery/compiler-replay.json)
