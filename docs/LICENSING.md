# Licensing and asset boundaries

Anatolii Chepasov licenses the project-owned software and its associated software documentation under the [MIT License](../LICENSE). Commercial use is welcome. When you distribute copies or substantial portions of the software, including inside an application, keep the copyright notice naming Anatolii Chepasov and the MIT permission notice. A licenses file supplied with the application is a suitable place for both.

You can publish images created with the renderer without adding a Brick Blueprint credit, link or watermark. If your scene uses someone else's geometry or artwork, the terms for those assets still apply. See the [third-party notices](../THIRD_PARTY_NOTICES.md) for the materials used in this repository.

## Separate rights

A code license covers only code the licensor has the right to license. It does not authorize redistribution of official instruction PDFs, product images, proprietary fonts, third-party part libraries, or trademarks. A self-produced render can still depict third-party designs; producing it ourselves is not blanket clearance for every use.

The repository contains the Brick Blueprint renderer, a synthetic test library, original model arrangements, set-derived assembly placements and locally rendered illustrations. Clipper2 is included as a pinned source dependency. The example files reference external geometry from the LDraw Parts Library.

The five portfolio models and the articulated crossing gate were designed for this project with AI assistance. The [portfolio credits](portfolio/sources.json) and [gate credits](gallery/crossing-gate.json) identify the DAT geometry used in each illustration. The kiosk cover uses browser text with an Arial, Helvetica and sans-serif fallback list. The captions in the kiosk PNG studies use Outfit under SIL OFL 1.1. [Portfolio and geometry records](PORTFOLIO.md) · [Font records](FONT-SOURCES.json)

## Clipper2

The snapshot is under Boost Software License 1.0. Its copyright headers and full license are preserved in `brick_blueprint/native/vendor/Clipper2/`. `PROVENANCE.json` records the upstream commit and SHA-256 hashes. This third-party license remains in force independently of our eventual code license.

## External LDraw data

Users supply a library separately. Read the license headers and accompanying notices for the specific files/version used; do not assume all historical files have the same license. LDraw's current contributor agreement permits CC BY 4.0 or CC0, while historical data may carry legacy terms. Render receipts preserve dependency names, hashes, author and license headers to assist attribution, but are not an automatic legal clearance or complete publication notice.

## Naming, branding and examples

Brick Blueprint is an independent renderer developed by Anatolii Chepasov. The first public edition is planned to include the Lighthouse Point reconstruction. The LEGO Group designed set 31051 and published the instructions. LDraw contributors created the external part geometry. The gallery depicts the project's own staging and rendering of the scene. [Official instructions](https://www.lego.com/en-us/service/building-instructions/31051) · [Per-part credits](gallery/lighthouse-vector.json)

LEGO is a trademark of the LEGO Group. The project links to the official instructions. Their public availability provides a reference for the reconstruction. Commercial reuse of the depicted set design is a separate rights question from commercial use of the renderer. The LEGO Group describes its guidance for fan sites in its [Fair Play policy](https://www.lego.com/en-us/legal/notices-and-policies/fair-play).

## Primary sources consulted, 2026-10-25

- [LEGO Fair Play](https://www.lego.com/en-us/legal/notices-and-policies/fair-play)
- [LDraw contributor agreement](https://library.ldraw.org/documentation/licenses-and-legal/ldraworg-contributor-agreement)
- [LDraw attribution guidance](https://ldraw.org/community/the-ldraw-organization/link-to-ldraw.html)
- [Clipper2 license](https://github.com/AngusJohnson/Clipper2/blob/a6e7294703ae329576462f9471b356971f53010d/LICENSE)

These are references for preparation, not a substitute for reviewing the exact eventual distribution.
