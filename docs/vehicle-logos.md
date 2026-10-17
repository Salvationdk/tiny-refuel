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
