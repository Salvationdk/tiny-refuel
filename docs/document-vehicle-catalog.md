# Tilføj og kontrollér kildehenvisninger

Python 3.10+, ingen ekstra pakker. Læg den berigede JSON og den tidligere
`kontrol-resultat.zip` i den mappe, hvor kommandoen køres:

```powershell
python scripts/document_vehicle_catalog.py --input "bilkatalog_online_beriget.json" --results "kontrol-resultat.zip"
```

Programmet gemmer en kopi i `tiny-refuel-kilder/katalog-med-kilder.json`.
Originalen og alle oprindelige kapaciteter/drivmidler bevares. `source_review`
pr. felt henviser til poster i `source_review_data.records`; disse indeholder
kilder, rå kildeværdier, variant, årgang, marked, batterigrundlag og datasætlicens.
`source_review_data.sources` indeholder fælles URL-oplysninger og onlinekontrol.
Eksisterende `source_url` og anden dokumentation overskrives ikke.

Konkrete HTML-links fra kandidatdataene kontrolleres online. Ved understøttet
JSON-LD eller projektets eksisterende producentregler udtrækkes nye kandidater.
URL'er betragtes ikke automatisk som producentkilder ud fra datasættets mærkning.
En hentet side eller et numerisk match er ikke verifikation af modelvarianten.
PDF-links, generelle forsider og sider uden understøttet struktur markeres til
videre kontrol. Der foretages ingen fri websøgning og ingen Wikipedia-opslag.
Det betyder, at modeller uden eksisterende henvisninger fortsat mangler kilder.

Der forsøges højst 100 konkrete sider pr. kørsel (`--limit` kan ændres). Cache og
`page-checks.json` gemmes løbende. Genstart med samme outputmappe for at genbruge
resultaterne og fortsætte til næste sider. HTTP 403/429/503 pauser værten resten
af kørslen; vent til eventuel Retry-After er udløbet før ny kørsel.
`--offline` genbruger kun gemte sider. `--skip-online` tilføjer kun de allerede
indsamlede kildehenvisninger. Ingen login, API-nøgle eller eksterne pakker kræves.

`online-candidates.json` kan efterfølgende læses af `verify_vehicle_catalog.py`
med `--candidates`. Det udfører selve sammenligningen af kapaciteter og drivmidler.
Ingen kandidater godkendes automatisk eller erstatter katalogværdier.

Send `tiny-refuel-kilder/kilder-resultat.zip` til gennemgang. Det indeholder den
dokumenterede katalogkopi, kildekontrollen og nye kandidater, men ikke sidecachen.
Bevar kilde- og licensoplysninger ved videre brug af datasættene.
