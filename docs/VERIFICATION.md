# Verifying Brick Blueprint

## Source checkout

Run these checks from the repository root. Core tests require Python 3.10+ and a C++17 compiler. The research consistency check also needs NumPy. The optional print integration can use a local ICC profile.

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_public_tree.py
python3 tools/build_measurement_tables.py --check
python3 tools/export_candidate.py --check
```

The suite exercises visible and hidden edges, transparent material layers, multipart transforms, tray scale, input errors, PDF paint, packaging boundaries and archive tampering. The archive check validates the actual distribution bytes, relative document links and the provenance of the gallery. A physical building test or a hosted CI run supplies separate evidence.

## Model plates

The five README models have editable inputs, complete native SVGs, model and illustration hashes, and per-file geometry credits. Three parts trays provide separate examples of the panel and quantity rules. The cover adds a frame and caption to the kiosk paths. [Recipes and expected hashes](PORTFOLIO.md)

## Research replay

The numerical checks below were run with Python 3.12.14 and NumPy 2.3.5. To repeat that environment, install the research library in a virtual environment using `python3 -m pip install numpy==2.3.5`. The brief and measurement-table generators use only the standard library for their Markdown checks.

| Check | What it tests |
|---|---|
| `python3 tools/build_research_brief.py --check` | The short answers, their reviewed evidence and the current research edition agree. |
| `python3 tools/build_measurement_tables.py --check` | The published per-image and color tables match their numerical sources. |
| `python3 tools/check_research_sync.py` | The runtime, packaged colors, camera defaults, saved example receipts and numerical sources agree with the declared contract. |
| `python3 tools/check_camera_pvalues.py` | The two 35°/35° angle tests and the recorded parametric bootstrap. The numerical check needs NumPy. |
| `python3 tools/analyze_face_law_17.py --check` | The 17-color gains from measured left-face RGB and their whole-color omission errors. |

The published study identifies the official source pages, selected image objects and measurements for each claim. [Research paper](RESEARCH-PREPRINT.md) · [Short answers](RESEARCH-BRIEF.md)

## Verify the original source editions

Keep your copies of the manuals in a directory outside the checkout. The checker identifies an edition by the SHA-256 of the complete PDF. File names may differ. For example, to check the Classic 11038 observations:

```sh
python3 tools/check_source_manuals.py --list --set 11038
python3 tools/check_source_manuals.py --set 11038 /path/to/manuals
```

The first command prints the expected hash and official source link using the standard library. For PDF inspection, the checked environment used pypdf 6.10.0 and Pillow 13.0.0. To audit the entire collection, place the PDFs in one or more directories and supply a new report filename.

```sh
mkdir -p output
python3 tools/check_source_manuals.py /path/to/manuals --report output/source-audit.json
```

The complete audit covers 38 book identities and page counts, 13 assembly image locators, 39 catalogue image records (30 in the primary cap sample), and 26 color observations. For each color record it checks the extracted image bytes, decoded RGB pixels, profile, central face-patch medians and all nine window positions. A missing edition or a failed measurement returns a nonzero exit status. The report identifies the set, page, image and failed measurement. It contains neither artwork nor local file paths.

This audit checks the observations used by the numerical analyses. To refit a camera or replay a statistical model, use the separate commands above. [Full audit report](research/SOURCE-MANUAL-AUDIT.json) · [Source corpus](STYLE-SOURCES.json) · [Research paper](RESEARCH-PREPRINT.md)

## Wheel and native code

Build a wheel and check its installed entry point away from the source tree. The checker verifies the wheel inventory, its RECORD hashes, the vendored Clipper2 notices, the packaged material definitions and an actual CPU render. [Build instructions](CI.md) · [Source archive verification](RELEASE-TOOLING.md)
