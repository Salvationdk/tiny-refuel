# Vehicle logos

Vehicle make logos are used in the card's vehicle buttons and the visual editor.
The card also supports model wordmarks through `model_logos` in `bilkatalog.json`.
The vehicle name stays visible if a logo is missing or an image fails to load.

## Current coverage

| Asset | Coverage | Delivery |
| --- | --- | --- |
| Make logos | 54 of 54 catalog makes | 53 bundled; NAVOR loads from its official website |
| Model wordmarks | 7 of 645 catalog models | 5 Porsche model entries use bundled official SVG signatures; Citroën C3 and C5 Aircross load from the documented source URLs |

Model wordmark collection is **not complete**. The C3 wordmark identifies the
third generation (2016), and the C5 Aircross wordmark identifies the first
generation. Other models use a text model-name mark on the vehicle button;
custom vehicle names stay visible and the full name stays accessible. A failed
model image reveals the text mark immediately. Do not describe this as
complete coverage of official model emblems or every model generation.

Bundled make-logo sources and trademark attribution are recorded in the
catalog's `logo_source` field. External assets have a `source_url`. Remote image
requests send no referrer. An image that fails during a page session is hidden
and is not repeatedly loaded on every Home Assistant state update.

## Catalog format

- `logos[make]`: bundled SVG text.
- `logo_pngs[make]`: bundled PNG data in base64, with no whitespace.
- `logo_colors[make]`: true for a colored make logo that keeps its colors.
- `logo_urls[make]`: external `url`, `source_url`, `monochrome`, and optional
  `white` to identify an asset whose original mark is white.
- `model_logos[make][model]`: `svg`, `png`, or `url`, with `source_url`, optional
  `generation`, and `monochrome`.
  Set `family: true` when a shared family emblem needs the full variant name
  alongside it, such as Macan Electric and Cayenne E-Hybrid.

Monochrome marks change between dark and light themes without adding a logo
background. Colored marks keep their colors. The catalog is fetched once per
URL and shared by cards and the editor in the same page session.

## Editor stability

Home Assistant config echoes do not rebuild the form. Car name, model, GPS,
tank, battery and fuel changes update existing fields. A needed catalog or
structural render retains open sections, focus, cursor and the focused draft.
Each car has one removal link.


## Prepared motor-vehicle makes

Ten additional monochrome SVG marks are embedded in JSON: DUCATI, YAMAHA
(Yamaha Motor), KTM, VESPA, JOHN DEERE, CATERPILLAR, SCANIA, MAN, IVECO and DAF.
They are available for manual vehicles and future DMR catalogs without adding
unverified models. `logo_aliases` resolves title-case versions to the same asset.
`logo_assets` records a source URL and SHA-256 for each prepared SVG.

These assets use the existing fixed-size logo boxes and dark-theme foreground
filter in both editor and dashboard. Existing full-color logos are unchanged.
The strict sanitizer in `scripts/prepare_vehicle_logos.py` rejects scripts,
external references, embedded images, CSS and document entities. Other makes
and model wordmarks retain the existing text fallback; this is partial coverage.

## Second logo expansion

28 further SVG marks are embedded, bringing the prepared extra-make pool to 38:
Acura, Aston Martin, Bentley, Bugatti, Cadillac, Chevrolet, Ferrari, Husqvarna,
Infiniti, Koenigsegg, Lamborghini, Lucid, Mahindra, McLaren, Rolls Royce, Saturn,
Tata, Vauxhall, Abarth, Aiways, Alpina, Autobianchi, Holden, Ineos, Lincoln, RAM,
Rivian and Trabant. These are make marks, not model-specific wordmarks.

Sources are Simple Icons and vehiclespecs/brand-logos, using pinned revisions
in each new asset's source URL. Every embedded file passed the strict SVG
allowlist; incompatible source files were skipped. Multi-color source marks
retain their colors. Text fallback and manual/custom vehicle catalogs remain
supported. Prepared assets do not add unverified vehicle models.

## Third logo expansion

100 additional make names now have embedded SVG assets. The asset pool contains
187 SVG make marks, 4 PNG marks and 1 external mark (192 names). This does not
mean the shipped 54-make model list has expanded. New names are prepared for
manual vehicles and the later DMR catalog import. Model wordmarks are unchanged.

The reviewed manifest is scripts/data/vehicle-logo-additions-2026-10.json.
Sources include node-vehicle-logos, vehiclespecs/brand-logos and detain/svg-logos,
with pinned revisions and SHA-256 hashes. The visual review excluded unrelated
football, tool, university and other company marks with matching names.
Static gradients and allowlisted inline paint declarations are supported;
scripts, external references and active SVG content are rejected.

## Remaining-name audit

Ten further reviewed SVG marks were embedded: Caterham, Harley Davidson, Moke,
Morris, BAC, BAW, e.GO, Lada, Puch and Vinfast. BAC and Lada use automotive
collection sources rather than unrelated marks found in the broad logo set.
The Puch 800x800 canvas is made explicit as a viewBox. Moke's static fill class
is flattened; BAW's unused class labels are removed without changing paint.

Current asset pool: 197 SVG, 4 PNG, 1 external logo (202 names). In the supplied
882-name cleaned DMR catalog, 198 names match an asset and 684 remain pending.
234 pending names are composite chassis/coachbuilder labels. They are not
assigned a chassis logo as though it were an authentic composite brand mark.
The complete audit is scripts/data/vehicle-logo-coverage.json; its counts are
also in catalog.logo_coverage. Pending names retain text fallback. This is not
complete logo coverage and the large DMR model catalog is still not shipped.

## Single-name search (30 additional assets)

The requested next batch of 100 could not be verified. 30 single register names
were added after source and visual checks: Bürstner, Carado, Carthago, Dethleffs,
Etesia, Goupil, Hisun, Hobby, LMC, Sunlight, TGB, Yutong, Polski Fiat, Daimler Benz,
VDL, Mercedes-AMG, Auto-Union, Temsa, Saviem, Multicar, Kreidler, Aebi, BMC, Delage,
Leyland, CF Moto, Eagle, Italcar, Matra and Hymer. No composite labels were added.

Assets from manufacturer websites, Wikimedia Commons, theSVG and the reviewed
logo collections record their provenance. Available Commons attribution and
license metadata is retained with the asset. Static masks are supported only
with local fragment references; external/active content remains rejected.
White foregrounds on Carado, Carthago and Goupil were normalized for light-theme
contrast, with mask paint preserved. Colored marks keep their palette.

Current pool: 227 SVG, 4 PNG and 1 external asset (232 names). Coverage of the
882-name cleaned register catalog is 228 available, 654 pending; pending is
234 composite names and 420 single names. These are make/logo-pool counts,
not additions to the shipped 54-make model list. Model wordmarks are unchanged.
