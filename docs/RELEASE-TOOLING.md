# Export a reviewable source candidate

The exporter produces a local ZIP, an exact source manifest and a verification
report. It has no network or GitHub operations. A successful export does not
grant a code license or approve the gallery's depicted designs for publication.
Resolve the decisions in [release preparation](RELEASE-PREPARATION.md) before
choosing a GitHub destination and visibility.

From the project directory, using the supported Python 3.10+ environment:

```sh
python3 tools/export_candidate.py --check
python3 tools/export_candidate.py --output output/release-review
python3 tools/export_candidate.py \
  --verify output/release-review/brick-blueprint-source-candidate.zip
```

The output directory must be new. The exporter validates all selected source
bytes before reserving it. Existing files and directories are never replaced.
A filesystem error during final copying can leave an incomplete new directory;
keep it for diagnosis and choose another output name for the next attempt.

The ZIP contains one `brick-blueprint/` directory. Its
`CANDIDATE-MANIFEST.json` lists each source path, size and SHA-256. The separate
`candidate-manifest.json` is the same record; `export-report.json` also records
the ZIP's SHA-256. The manifest identifies an exact candidate, not whatever is
later present in a working directory. The ZIP verifier checks its complete
inventory, each payload hash, source-tree digest and distribution checks.
It does not extract or execute the archived code.

## Stable file hashes after checkout

The render receipts and research checks identify files by their exact bytes. The repository uses LF line endings for text on all platforms. PNG files and the pinned vendor snapshot keep their original bytes. These rules also apply when Git is configured to convert ordinary text files to CRLF. [Checkout attributes](../.gitattributes)

## Distribution boundaries

Only explicit source areas and file types are accepted: package sources,
documentation, examples, tests, tools, the CI workflow and named root files.
Unknown source directories and file types cause an error. Development outputs,
the Git database, environment directories, bytecode caches, prior generated candidate manifests and egg metadata
are excluded without traversing them. Symlinks in selected areas are rejected.

The exact exported bytes are checked for:

- known credential and private home-directory path patterns;
- PNG provenance, unexpected text/EXIF metadata and trailing data;
- the five portfolio model hashes, three tray inputs, native vectors and cover;
- the named measurement CSV as part of the research data;
- Cyrillic text in filenames and content, including escaped JSON strings;
- active/raster SVG elements, event handlers and external references;
- local Markdown file links staying within the candidate;
- pinned Clipper2 file hashes and preserved notices;
- gallery image hashes and the existence of referenced render receipts;
- original synthetic DAT fixture headers, rather than an external parts library.

The default file limit is 2 MB. Two larger files have individual limits and SHA-256 checks. The bootstrap record contains all 3,998 fits. The 537-placement lighthouse SVG preserves all 493,499 expanded path commands. The complete distribution is limited to 100 MiB.

These are bounded checks. They do not detect every secret, prove ownership,
certify model geometry, or independently establish that a render receipt is
truthful. Review the content and its provenance before publication. Markdown
fragment anchors, remote links, workflow behavior and arbitrary source-code
security are outside the automated export checks.

Sorted paths, fixed ZIP timestamps and normalized file permissions exclude
machine usernames, filesystem mtimes and local absolute paths from the
manifest. Compression bytes can depend on the ZIP/zlib implementation, so
the recorded ZIP hash belongs to this exact artifact. Each payload hash and
the source-tree digest remain useful across environments.

## Verify from the exported checkout

Extract the ZIP into an unrelated directory. Then run:

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_public_tree.py
python3 tools/export_candidate.py --check
python3 -m brick_blueprint render examples/demo.ldr \
  --library examples/library --output output/demo
```

The synthetic smoke render needs Python and a C++17 compiler, with no external
LDraw download. Real part examples still require a separately supplied library.
Optional CMYK testing additionally needs Pillow/LittleCMS and a suitable ICC
profile. [Verification scope](VERIFICATION.md) and
[licensing boundaries](LICENSING.md) continue to apply.

## Installed package check

Build a wheel with the declared build backend, then check that exact wheel:

```sh
python3 -m pip wheel --no-deps . --wheel-dir dist
python3 tools/check_wheel.py dist/*.whl
```

The wheel check installs only into a temporary directory, with `--no-index --no-deps`. It verifies every wheel RECORD entry and the pinned vendor notices, then compiles native sources and runs a synthetic render plus grayscale export with site packages disabled. The smoke check itself uses no network or external LDraw library. Building the wheel may fetch declared build tools unless an existing environment is used with `--no-build-isolation --no-index`. CI includes this check; successful local runs do not imply GitHub-hosted CI has run.

For reproducible wheel timestamps, set `SOURCE_DATE_EPOCH` to a fixed Unix timestamp when building. Preserve the Python/build-tool versions alongside the wheel hash. Repeated builds in one verified environment can then be compared byte for byte.
