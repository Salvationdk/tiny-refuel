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

## Raster tracing and broader source search

31 additional register makes were identified in the car-logos-dataset PNG
collection. 12 were accepted as visually reviewed path-based raster traces:
Bitter, DKW, Hupmobile, Innocenti, Lifan, Panhard, Pierce Arrow, Radical, Riley,
Ultima, Wanderer and Zastava. 19 detailed marks use bundled transparent PNG
fallbacks instead of large or inaccurate traces. The existing Leapmotor, NIO,
Zeekr and NAVOR marks now use embedded traced SVG; their raster inputs remain
in logo_raster_sources. Hongqi retains its colored PNG badge. NAVOR no longer
requires a remote image request. These conversions are not original SVG artwork.

Every trace has origin=raster_trace, source/input hashes, tool/mode and review
metadata. Polygon tracing preserves angular Leapmotor/Zeekr edges; other marks
use reviewed spline traces. scripts/data/vehicle-logo-raster-review.json records
accepted traces and PNG decisions. Source raster URLs are pinned to the reviewed
car-logos-dataset revision where applicable. Existing packaged input sources are
identified separately from higher-resolution reference images.

Current asset pool: 243 SVG + 20 PNG, no external make-logo images (263 names).
Coverage of the cleaned register list is 259/882; 389 single names and 234
composite names remain pending. Model wordmarks and the 54-make model list are
unchanged. Text fallback remains available.

The optional developer command scripts/vectorize_vehicle_logo.py requires
Pillow and vtracer (reviewed with vtracer 0.6.12). It produces sanitized paths,
retains provenance, enforces a size budget, and explicitly requires visual
review. It is not a Home Assistant dependency or runtime scraper. Example:

```sh
python scripts/vectorize_vehicle_logo.py --input logo.png --output candidate.svg --source-url https://example.com/brand --monochrome --polygon
```

## Further native SVG review, 17 October 2026

Four more native SVG assets are included: Albach, ALKE, Paxster and KEEWAY.
Albach, ALKE and Paxster come directly from manufacturer websites. KEEWAY
is the 2023 wordmark from Wikimedia Commons, whose description credits the
manufacturer about-us page; it is retained as a historical mark, not described
as the latest brand identity. Source and available license metadata are kept.
Static CSS was flattened and editor-only attributes removed. Paxster's local
clip IDs were prefixed to satisfy the existing sanitizer; vector paths and
colors are preserved. All four were rendered and visually checked.

Current totals supersede earlier dated batches: 247 SVG, 20 PNG, no external
make assets (267 asset names). Coverage of the 882-name register list is
263 available and 619 pending: 385 single names and 234 composite names.
20 additional register names have PNG but still lack SVG, so 639 register
names lack SVG. The shipped model list remains 645 models / 54 makes.

## Manufacturer-site vectors, second review on 17 October 2026

Seven additional native SVG assets were verified: EBUSCO, MELEX, Cenntro,
KABE, KALMAR, MICRO and DULEVO. Every source is the manufacturer's own site.
Kalmar, Micro, Dulevo and Melex are extracted from the header's inline vector
markup; no remote dependencies remain. Melex's canonical header logo is used
instead of the anniversary footer badge. Micro's white header foreground is
normalized to black for the existing theme inversion. Dulevo's CSS foreground
is normalized to black; its viewBox includes the left edge of the emblem.
Sources, normalization and exact hashes are recorded. Shapes were rendered
and checked; colored marks retain their palette, monochrome marks use the
existing foreground filter in dark mode.

Latest totals: 254 SVG, 20 PNG, no external make assets (274 asset names).
Register coverage: 270 of 882 names have an asset, 612 pending (378 single
names and 234 composite names). Including 20 PNG-only names, 632 register
names still lack SVG. The 645-model / 54-make bundled model list is unchanged.
