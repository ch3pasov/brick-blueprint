# Prepared CI and the local build environment

[Verification](VERIFICATION.md) · [Source and wheel workflow](RELEASE-TOOLING.md)

The [workflow](../.github/workflows/test.yml) is prepared locally. It has **not run
on GitHub**. It runs core tests, research-to-render consistency checks, table replay, source checks and installed-wheel smoke checks; there is no
release, package upload, Pages, deployment, write permission or secret requirement.

The core matrix uses Ubuntu/macOS and Python 3.10/3.13. The research and print job uses
Python 3.12, NumPy 2.3.5 and Pillow 13.0.0 for PNG reader and print tests. A real ICC output
profile is not bundled, so that integration case is skipped in hosted CI unless
an appropriate profile is deliberately provided later. Local QA supplied one and
records the actual no-skip result separately. Core jobs also report optional
Pillow-dependent skips rather than silently claiming they ran.

The optional PNG check exercises both CLI commands with pypdfium2 and Pillow. The compatibility runs below describe the vector release that preceded this output option.

### Local compatibility run

We ran the core suite on arm64 macOS with Apple clang 21 and CPython 3.10.22, 3.11.18, 3.12.14, 3.13.18, 3.14.10 and 3.15.2. The five standard-library environments each passed 131 tests and skipped nine optional cases. The fixture SVG was byte-identical across all six Python versions in each of two modes, with and without underpaint. Python 3.12.14 passed all 140 tests with optional dependencies and a real CMYK output profile on both Apple clang 21 and GNU GCC 16.2.

The same 140 tests passed with a CMYK profile on Alpine Linux 3.24.3, CPython 3.14.10 and GCC 15.2 in a local arm64 virtual machine. The guest had no network connection. From a clean archive it also built and installed the wheel, repeated the perspective and color calculations, and composed the material guide from fresh native SVGs. [Compiler and pixel comparisons](REPRODUCIBILITY.md#what-changes-with-the-compiler)

With setuptools 84.1.0 and the same build timestamp, macOS and Linux produced byte-identical installable wheels. We installed both wheels and ran their render checks. The guest also rendered the 537-placement lighthouse and the shunter instruction page. [Build and drawing results](gallery/compiler-replay.json)

Actions are pinned to full commit SHAs, checked 26 October 2026 against official
release/commit pages:

- [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1):
  `3d3c42e5aac5ba805825da76410c181273ba90b1`.
- [setup-python v7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0):
  `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`.

Both actions declare Node 24 in their own [checkout](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/action.yml) and [setup-python](https://github.com/actions/setup-python/blob/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0/action.yml) action definitions. This workflow uses
current GitHub-hosted runners; self-hosted runner compatibility is not established.
Checkout credentials are not persisted into Git configuration for subsequent steps.
Only `contents: read` is granted. Events are ordinary push/pull_request, with no
privileged pull_request_target or workflow_run execution of fork code.

The locally exercised build backend is **setuptools 84.1.0**, supporting Python 3.10+.
CI provisions that exact version and then builds with `--no-build-isolation
--no-index --no-deps`, plus a fixed `SOURCE_DATE_EPOCH`. Backend provisioning still
needs the public package index. The wheel smoke check installs offline into a
temporary directory; no global/user installation is performed by that check.

The Mac runtime also has wheel 0.48.0 and pip 26.2.2; those are recorded environment
facts, not runtime dependencies of Brick Blueprint. Current setuptools builds the
wheel without requiring the separate `wheel` command package. A separate local
isolated build tests that boundary. Version pins are a reproducible baseline,
not an exhaustive supply-chain or vulnerability assessment. Recheck them before
release; never describe prepared YAML as a successful hosted run.

Primary package metadata:
[setuptools 84.1.0](https://pypi.org/pypi/setuptools/84.1.0/json),
[wheel 0.48.0](https://pypi.org/pypi/wheel/0.48.0/json).
