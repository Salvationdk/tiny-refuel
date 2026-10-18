# Hent manglende køretøjsspecifikationer

`scripts/scrape_vehicle_specs.py` bruger Python 3.10 eller nyere og kræver ingen ekstra pakker. Det laver først en mangelliste fra det **ufiltrerede, fulde JSON-katalog**. Brug ikke frontendfilen `bilkatalog.json`, som er et manifest, eller kataloget med kun 470 modeller: de udeladte modeller findes kun i originalen.

## 1. Lav mangellisten

```sh
python scripts/scrape_vehicle_specs.py --catalog katalog-ufiltreret.json --output resultater
```

På Windows kan `python` erstattes med `py -3`. Der foretages ingen netværkskald uden `--sources`.

`missing.json` indeholder mærke, model, manglende felter, kendte drivmidler og antal varianter. Ren el kræver batterikapacitet; kendte brændstofkøretøjer kræver tankstørrelse. Hybrid kræver begge. Ukendt drivmiddel betyder, at anvendeligheden af tank og batteri stadig skal afklares. Motorredskaber springes over. Det medfølgende rensede originalkatalog giver 26.902 modeller med mindst ét manglende relevant felt; dette omfatter også modeller, der allerede har én kapacitet, men mangler andre oplysninger.

## 2. Angiv præcise kildesider

Kopiér `scripts/data/vehicle-spec-sources.example.json` til `sources.json`. Erstat eksemplet med reelle kildesider. Brug helst fabrikantens specifikationsside for det konkrete modelår og den konkrete variant. Én række pr. kilde, flere kilder pr. model er tilladt:

```json
[
  {
    "make": "Mærke præcis som i kataloget",
    "model": "Model præcis som i kataloget",
    "year": 2020,
    "variant": "Variant præcis som på kildesiden",
    "url": "https://example.invalid/erstat-med-en-rigtig-kildeside"
  }
]
```

`year` og `variant` kan udelades ved den indledende indsamling. I så fald kan scriptet returnere flere kandidater med forskellige år/varianter. Det er stadig nødvendigt at gennemgå dem; én fundet kapacitet gælder ikke automatisk hele modelserien. År og variant i kildelisten er filtre, aldrig oplysninger som scriptet tilføjer til et mangelfuldt kildefund.

## 3. Hent kandidater

```sh
python scripts/scrape_vehicle_specs.py --catalog katalog-ufiltreret.json --sources sources.json --output resultater --delay 2
```

Scriptet læser JSON-LD med køretøjstype, et udtrykkeligt `brand`/`manufacturer` og `model`. Mærke og model skal matche. Hvis du angiver år eller variant, skal de også være angivet og matche i kildedata. Tekst på almindelige HTML-sider, tabeller, PDF'er og JavaScript-genereret indhold udtrækkes ikke automatisk. Sider uden passende strukturerede data står som `no_matching_structured_specs` i statusfilen. Scriptet søger ikke selv på nettet efter kilder og omgår ikke login eller blokeringer.

- `candidates.json`: forslag med felter, årgang, variant, kilde-URL, hentetidspunkt, sidehash og `review_required: true`.
- `source-status.json`: fund, fejl og eventuelle modstridende oplysninger pr. kilde.
- `without-source.json`: modeller fra mangellisten, som endnu ikke har en kilde i din kildeliste. En angivet kilde er ikke bevis på, at data er fundet; kontrollér også statusfilen.
- `cache/`: hentede sider, så en ny kørsel genbruger sideindholdet. Slet en cachefil, hvis siden skal hentes igen. `retrieved_at` er tidspunktet, hvor kandidaten blev lavet; ved genbrug kan sideindholdet være ældre.

Der er minimum ét sekund mellem netværkskald, standard to. `robots.txt` kontrolleres, og en længere angivet crawl-pause respekteres. Midlertidige fejl stopper ikke resten af kildelisten. Resultater gemmes efter hver kilde; ved genstart gennemløbes listen igen og cachede sider genbruges.

Tankstørrelse accepteres kun med en udtrykkelig literenhed eller entydig amerikansk/britisk gallon-kode. Batterikapacitet accepteres kun i kWh eller Wh. Ah omregnes ikke til kWh. Modstridende kapaciteter i samme køretøjspost afvises. Brutto/netto markeres, når kilden udtrykkeligt angiver det; ellers står `battery_basis` som `unspecified`.

**Import er bevidst manuel.** Originalkataloget og integrationen ændres aldrig af scriptet. Gennemgå fundets årgang, variant, drivmiddel, batteriets brutto/netto og kilde, før oplysningerne indarbejdes. Manglende fund er ikke et nul. Bevar kildehenvisning ved senere import.

Felternes definitioner: [schema.org Vehicle](https://schema.org/Vehicle), [fuelCapacity](https://schema.org/fuelCapacity) og [fuelType](https://schema.org/fuelType).

## Test uden internet

```sh
python -m unittest discover -s tests -p test_scrape_vehicle_specs.py -v
```

Testene kontrollerer model/år/variant, enheder, modstridende værdier, mangellister og en hel kørsel med simulerede kildesvar. De bekræfter ikke dækning på bestemte levende websites.
