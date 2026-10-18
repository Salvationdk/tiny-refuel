# Lokal indsamling af køretøjsdata

Python 3.10+ er nok. Ingen ekstra Python-pakker, API-nøgler eller betalte tjenester bruges af scriptet.

## Kom i gang med den selvstændige ZIP

Udpak hele pakken. Dobbeltklik på **START-HENTNING.cmd** på Windows. Bevar filerne og mappestrukturen. Alternativt åbnes en terminal i den udpakkede mappe:

```sh
python scripts/scrape_vehicle_specs.py --catalog katalog-ufiltreret.json --official-batch --open-ev --engine-data --output resultater
```

På Windows kan `python` erstattes med `py -3`. Den færdige kildeliste ligger i **sources.json** i pakkens rod og som `scripts/data/vehicle-spec-sources.verified.json`. `--official-batch` bruger den indbyggede liste, så du ikke behøver udfylde en skabelon. Hvis du selv ændrer rodens sources.json, bruges `--sources sources.json` i stedet for `--official-batch`.

Tre kilder behandles:

1. **Producenternes egne sider:** Seks gennemgåede HTML-regler til Abarth 500e/600e, Aiways U5/U6 og Alpine A290/A390 GTS. Tal læses fra synlig HTML med kontekst, ikke kun JSON-LD. Modelår eller brutto/netto gættes ikke, når siden ikke angiver det.
2. **OpenEV Data:** Scriptet finder og henter den seneste offentlige JSON-udgivelse. Batteriets brugbare og nominelle kapacitet, år, variant, marked og kildelinks bevares. Data er under CDLA-Permissive-2.0.
3. **vehicle-makes-models:** Scriptet henter et versionfastlåst samlet datasæt med motorer, drivmidler og rå specifikationer. Tankkapacitet læses kun fra et udtrykkeligt literfelt under Fuel capacity. Gallons uden literangivelse omregnes ikke. Generation, årgangsinterval og motorvariant bevares. Data er under ODbL-1.0.

De to datasæt er fællesskabsprojekter; deres tal er ikke uafhængigt kontrolleret mod fabrikantens specifikationer. Generiske kildelinks som audi.com markeres som svag dokumentation. Datasæt er ikke bevis for danske markedsvarianter. Resultater er forslag til gennemgang, aldrig automatisk færdige katalogposter.

## Resultater og dækning

Den første fulde kørsel den 18. oktober 2026 gav:

- 6 producentfund.
- 149 batteriforslag fra 1.189 OpenEV-poster, fordelt på 31 katalogmodeller.
- 8.105 tank-/drivmiddelforslag fra 30.535 motorposter, fordelt på 661 katalogmodeller.
- Samlet 8.260 forslag fordelt på 697 forskellige katalogmodeller. Et forslag kan dække enkelte felter for én variant, så dette er ikke 697 færdigverificerede modeller.

Antallet kan ændre sig, når kilderne opdateres. Resten af kataloget er ikke dækket af disse kilder og matches. Scriptet søger ikke frit på hele internettet. Det erstatter ikke behovet for flere kilder eller gennemgåede navnealiaser.

Filer i `resultater/`:

| Fil | Indhold |
|---|---|
| summary.json | Samlede antal forslag og modeller |
| all-candidates.json | Alle indsamlede forslag samlet |
| candidates.json | Producent-/JSON-LD-fund med kilde og kort evidens |
| open-data-candidates.json | Batteriforslag med netto/brutto, år, variant og marked |
| engine-data-candidates.json | Tank-/drivmiddelforslag pr. generation og motor |
| open-data-report.json / engine-data-report.json | Dækning, afvisninger og umatchede kildenavne |
| missing.json | Den oprindelige mangelliste |
| without-candidates.json | Modeller uden noget fund; øvrige modeller kan stadig mangle felter |
| source-status.json | Hentefejl og resultat pr. producentkilde |
| sources.json | Kildelisten brugt i den pågældende kørsel |

## Cache, genstart og offline

Gennemførte sidehentninger og datasæt genbruges. Scriptet kontrollerer datasætversionen og downloader ikke hele filen igen, når den er uændret. Motorsættet fylder cirka 85 MB udpakket; OpenEV cirka 3,2 MB. Den selvstændige ZIP indeholder den allerede hentede datacache med kilde- og licensoplysninger. En afbrudt stor download kan skulle begynde forfra, men den erstatter ikke den tidligere gode cache. Producentresultater gemmes efter hver kilde.

Scriptet kører lokalt på din egen computer. Lad terminalvinduet være åbent, indtil det er færdigt. Kør den samme kommando igen efter en fejl. Se fejlbeskeden og source-status.json, hvis en kilde ikke kunne hentes.

Datasættene kan genbehandles helt uden internet:

```sh
python scripts/scrape_vehicle_specs.py --catalog katalog-ufiltreret.json --open-ev --engine-data --offline --output offline-resultater
```

Bemærk: Brug samme outputmappe, som indeholder datacachen, fx `resultater`, eller kopiér dens `open-data-cache` til den valgte outputmappe først. Offline producenthentning kræver også, at siderne tidligere er hentet til `cache/`; HTML-siderne er ikke medleveret i ZIP'en.

## Navne og gennemgang

Der anvendes ikke ukontrolleret fuzzy matching. A4 og A 4 er forskellige indtil en eksplicit aliasmapping er gennemgået. OpenEV kan modtage en aliasfil med `--aliases aliases.json`:

```json
[
  {"source_make":"Audi", "source_model":"A4", "make":"Audi", "model":"A 4", "reviewed":true}
]
```

Eksemplet viser formatet, ikke en godkendelse af, at de to poster i dit katalog skal sammenlægges. Flere tvetydige mål afvises. Motor-datasættet matcher foreløbig kun nøjagtige navne.

**Originalkatalog og integration ændres aldrig automatisk.** Kontroller variant, modelår, marked, drivmiddel, kilde og batteriets brutto/netto før import. Forskellige tankstørrelser pr. motor må ikke reduceres til én modelstandard. Manglende værdi betyder ikke nul. Datasætlicenser følger med cachen og skal bevares ved videre deling; ODbL-data skal holdes under deres egne vilkår. Scriptets kode og datasæt har forskellige licenser.

EV Database indgår ikke i automatisk hentning, fordi udbyderen udtrykkeligt forbyder automatiseret indsamling. Der omgås ikke blokeringer eller login. Producenthentninger kontrollerer robots.txt, har pause og gemmer cache.

Kilder: https://github.com/open-ev-data/open-ev-data-dataset og https://github.com/gor3a/vehicle-makes-models. De seks direkte producentlinks ligger i sources.json. Kildeoplysninger og version/hash gemmes i resultaterne.

## Test

```sh
python -m unittest discover -s tests -p "test_*spec*.py" -v
```

Testene omfatter identitet, år/variant, kapacitetsenheder, HTML-konflikter, aliaser og nettokapacitet større end brutto. Hele den lokale kørsel er også afprøvet med de faktisk hentede datasæt og producentdata.
