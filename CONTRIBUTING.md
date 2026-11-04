# Development

Use English for documentation, captions, help text and examples. Keep attribution names as supplied by their authors.

## Renderer changes

Keep the core independent of particular sets. Preserve page-space line width through projection, occlusion, SVG and PDF export. A useful regression case isolates a visible difference, such as a line showing through an opaque part or a missing layer of glass.

```sh
python3 -m unittest discover -s tests -v
python3 tools/export_candidate.py --check
```

## Illustrations and research

Render examples with the project renderer. Include the editable model, camera settings, geometry credits and a way to reproduce the picture. Use separately supplied libraries. [Portfolio recipe](docs/PORTFOLIO.md)

Match geometry, camera and framing when comparing renderers. When comparing two alternatives to an official source, put the official reference in the center. Link to the official page for the public edition. [Comparison layout](docs/COMPARISON-LAYOUT.md)

Run `python3 tools/check_research_sync.py` with NumPy installed when changing the scientific evidence. Maintain the research brief alongside the study. When a result changes, review the affected answers and their evidence, then update the reviewed source hashes and regenerate the brief with `python3 tools/build_research_brief.py`. [Research brief](docs/RESEARCH-BRIEF.md) · [Evidence record](docs/research/RENDER-CONTRACT.json)

## Distribution

The core, gallery geometry and vendored code have separate rights and notices. [Licensing boundaries](docs/LICENSING.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)
