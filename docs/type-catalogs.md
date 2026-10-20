# Kataloger efter køretøjstype

Når et køretøj får valgt type, beder editoren Home Assistant om den type.
Home Assistant henter `catalogs/v1/index.json` og kun den relevante fil fra
GitHub. Browseren kontakter ikke GitHub direkte. Et eget `katalog_url` bevarer
sin eksisterende funktion.

| Køretøjstype | Fil |
|---|---|
| Personbil | car.json |
| Varebil/varevogn | van.json |
| Lastbil | truck.json |
| Motorcykel | motorcycle.json |
| Knallert | moped.json |
| Bus | bus.json |
| Traktor | tractor.json |
| Andet/ukategoriseret | other.json |

Flere typer kan bruges samtidigt. En model observeret i flere kategorier
findes i hver relevant fil. Ukendt type gættes ikke.

Filer gemmes under `.storage/tiny_refuel/catalogs`. Efter 24 timer kan næste
brug kontrollere indekset igen. Filen hentes kun igen, hvis dens SHA-256 er
ændret. Ved netværksfejl bevares lokal kopi. Uden lokal kopi bruges det
medfølgende katalog filtreret på typen; hvis typen mangler her, kan mærke,
model og kapacitet stadig indtastes manuelt. Kortets allerede gemte køretøjer
ændres ikke af katalogopdateringer.

## Datastatus og oprydning

De nye filer er et arbejdsgrundlag. Eksisterende positive kapaciteter er
bevaret med `needs_review`; onlineverificering af hele kataloget er ikke
færdig. Editorens modelnote oplyser, at tallet kræver kontrol. Kilder og
kapacitetsafhængige varianter bevares. Importprofiler, store kontrolrapporter,
logoer, generelle variantinventarer og gentaget importtekst er fjernet fra
kategorifilerne. Logoerne ligger separat i frontendens `vehicle-logos.json`.
De 15 poster med uafklaret registeridentitet er dokumenteret i
`docs/catalog-quarantine.json`; de er ikke slettet fra originalgrundlaget.

Runtime accepterer kun faste filnavne, et gyldigt katalogformat og en fil,
der matcher indeksfilens størrelse og checksum. Kilder leveres som data,
ikke som kode.

## Genopbygning fra eget arbejdsgrundlag

```sh
python scripts/split_type_catalogs.py --input katalog2.json --output catalogs/v1 --version YYYY-MM-DD.N --report catalog-build-report.json
```

Originalen ændres ikke. Rapporten gemmer udeladte identiteter og tæller poster
pr. kategori. Kontrolstatus ændres ikke til verificeret af opdelingen.

## Udrulning

Downloaderen bruger GitHubs `main`-branch. Kataloger og downloader skal derfor
merges sammen, før en udgivelse aktiverer hentningen. En kladde-PR ændrer ikke
den installerede integration.

## Fælles køretøjer og katalogstatus

Under integrationens indstillinger kan **Tilføj fra katalog** vælge type,
mærke, model og eventuel variant. Kun den valgte type hentes. Den sidste
formular giver mulighed for at rette kapacitet og angive årgang, position og
notifikationer. En variants kapacitet arver ikke modstridende modeltal.
**Tilføj manuelt** fungerer fortsat uden katalog. Fælles køretøjer bruges af
sensorerne og kort uden egne køretøjer; gemte kapaciteter ændres ikke ved
opdatering af kataloget.

En diagnostisk **Katalogstatus** viser `not_loaded`, `ready` eller `cached`.
Attributterne viser indlæste typer, antal modeller, version, kilde,
hentningstidspunkt og typer, der bruger en kopi efter hentefejl. Sensoren
indeholder kun disse summer, ikke hele kataloget. `ready` betyder, at
katalogfilen er tilgængelig; det godkender ikke modellernes kapaciteter.

Den visuelle test kører den rigtige integration, optionsflow, API, kort og
editor i Home Assistant og Chromium. Kataloghentninger leveres fra faste
prøvedata, så alle typer kan afprøves uden afhængighed af GitHub-netværket.
