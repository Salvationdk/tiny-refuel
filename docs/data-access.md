# Brug alle Tiny Refuel-data i Home Assistant

Tiny Refuels egne kort bevares. Andre kort, templates, scripts og automatiseringer kan bruge de samme data via entiteter og seks svarhandlinger. Forespørgsler starter ikke et nyt scrape. Katalogforespørgsler bruger katalogets eksisterende download/cache.

## Entiteter til almindelige kort

Åbn **Indstillinger → Enheder og tjenester → Tiny Refuel → Konfigurer → Stationssensorer til andre kort**. Vælg op til 50 stationer. Hver valgt station får fire sensorentiteter: benzin 95, benzin 100, diesel og el. Aktiver kun de relevante sensorer i dine kort. Manglende eller gamle priser giver `unknown`, ikke 0. Et tomt stationsvalg fjerner stationssensorerne. ID bygger på stationens eksisterende stabile ID, ikke dens position eller viste navn.

Fælles køretøjer får desuden **oplysninger**, **tankkapacitet** og **batterikapacitet**, sammen med de eksisterende sensorer for nærmeste sted, afstand, pris og fuld kapacitet. Alle køretøjets gemte felter, herunder kapacitetens kontrolstatus, findes som attributter. En kapacitet er stadig et forslag, hvis kontrolstatus siger det.

Vælg entiteterne fra integrationssiden; deres entity_id afhænger af navn og eventuelle brugerændringer. Brug de valgte ID'er i almindelige Entities-, Tile-, Gauge- eller History Graph-kort. Kort på HA-kortet bruger fortsat den separate kortindstilling.

```yaml
type: entities
title: Mine brændstofpriser
entities:
  - entity: sensor.erstat_med_din_stationssensor
  - entity: sensor.erstat_med_din_tankkapacitet
```

Home Assistants Recorder kan gemme numeriske sensorers historik, medmindre de er udeladt i Recorder. Historik før en stationssensor blev valgt udfyldes ikke bagud. Tiny Refuels lokale prishistorik er separat og tilgængelig via get_history.

## Svarhandlinger

Alle seks handlinger understøtter svar og kræver `response_variable` i scripts/automatiseringer. De kan prøves under **Udviklerværktøjer → Handlinger**. Du kan også kalde dem via Home Assistants almindelige service-websocket med `return_response: true`.

| Handling | Data |
| --- | --- |
| `tiny_refuel.get_data` | Alle originale felter: metadata, stationsrækker, ladedata, fordele, kilder, fejl, geokodning og fælles køretøjer |
| `tiny_refuel.get_stations` | Normaliserede stationer, priser, tidsstempler, kontrol af aktualitet, koordinater, navigation, valgfri afstand og filtre |
| `tiny_refuel.get_vehicles` | Alle gemte køretøjsfelter samt pris/afstand/omkostning ved nærmeste relevante station |
| `tiny_refuel.get_status` | Kildestatus, fejl, fremdrift, katalogstatus, historik og kortstatus |
| `tiny_refuel.get_history` | Lokale prisobservationer for et stations-ID og drivmiddel |
| `tiny_refuel.get_catalog` | Alle felter i modeller/varianter og deres mærkeoplysninger samt katalogmetadata |

Drivmiddelkoder er `p95`, `p100`, `diesel` og `kwh`. Priser er DKK/L eller DKK/kWh, afstand er km i luftlinje, og full_cost er DKK for fuld indtastet kapacitet uden ladetab, gebyrer eller rabatter.

### Alle rå felter og fordele

```yaml
action: tiny_refuel.get_data
data: {}
response_variable: refuel_metadata
```

Svaret indeholder `sections`, den aktuelle liste over tilgængelige felter. Også nye indsamlede felter bliver tilgængelige her uden at skulle oprette nye sensorer.

```yaml
action: tiny_refuel.get_data
data:
  section: benefits
  limit: 100
  offset: 0
response_variable: refuel_benefits
```

Lister returneres som `kind: list` og `items`. Opslag returneres som `kind: mapping` og `items: [{key: ..., value: ...}]`, så alle oprindelige nøgler og felter bevares. En enkelt værdi returneres under `value`. Rå data kan indeholde gemte/fejlramte priser og generelle selskabstakster: brug get_stations med current_only til aktuelle lokale priser. get_data-svaret viser seneste overordnede fejl.

### Billigste pris, område og favoritter

```yaml
action: tiny_refuel.get_stations
data:
  fuel: p95
  sort: price
  location_entity: device_tracker.moto_g15_power
  radius_km: 25
  current_only: true
  limit: 5
response_variable: refuel_stations
```

Billigste pris findes i `refuel_stations.items[0].prices.p95`, når listen ikke er tom. Stationer kan også filtreres med `brands`, `search` og `station_ids`. station_ids kan bruges som egen favoritliste. `sort: distance` kræver en tilgængelig positionsenhed. Uden position kan du sortere efter pris eller navn uden radiusfilter. Generelle selskabstakster er udeladt fra lokale stationer; hent dem fra råsektionen ev.

### Køretøjer, også fra et korts egen opsætning

```yaml
action: tiny_refuel.get_vehicles
data: {}
response_variable: refuel_vehicles
```

`items[0].calculations.p95` indeholder station, distance_km, price og full_cost. Manglende position, pris eller kapacitet giver null i beregningen.

Fælles køretøjer er dem fra integrationsindstillingerne. Biler og favoritter, der kun er gemt i et Lovelace-kort, er stadig kortets egen opsætning og bliver ikke automatisk flyttet til integrationen. Et eget køretøj kan sendes direkte til beregning:

```yaml
action: tiny_refuel.get_vehicles
data:
  vehicle:
    navn: Volkswagen up!
    brændstof: benzin
    tank_liters: 35
    location_entity: device_tracker.moto_g15_power
response_variable: refuel_vehicle
```

Kald med bruger-ID kontrollerer læseadgang til positionsenheden; køretøjer med beskyttet position udelades, og direkte forespørgsler på en beskyttet positionsenhed afvises. Automatiseringer uden bruger-ID kører som Home Assistants systemkontekst.

### Katalog og historik

```yaml
action: tiny_refuel.get_catalog
data:
  vehicle_type: personbil
  make: Volkswagen
  search: up!
  limit: 20
response_variable: refuel_catalog
```

Hver item indeholder `make` med mærkets metadata og `model` med alle oprindelige modelfelter, inklusive varianter og kildeoplysninger. Katalogets øvrige felter ligger under metadata. Kontrolstatus bevares; et katalogopslag validerer ikke kapaciteten.

```yaml
action: tiny_refuel.get_history
data:
  station_id: ERSTAT_MED_STATIONENS_ID
  fuel: p95
  days: 7
response_variable: refuel_history
```

Stations-ID findes i get_stations-svaret og stationssensorens attributter. Historikken viser enabled, retention_days, points og truncated. Der returneres højst 2000 observationer plus et eventuelt tidligere udgangspunkt. Tidsrummet begrænses af den valgte opbevaringstid; historik før registrering findes ikke.

### Sideinddeling

get_data, get_stations, get_vehicles og get_catalog returnerer `total`, `offset`, `limit` og `next_offset`. Standard er 100, højst 500 resultater pr. kald. Gentag kaldet med next_offset indtil den er null for at hente hele datasættet. Katalogvarianter ligger samlet med deres model, så de ikke mister sammenhængen.

### Templates uden ekstra integrationer

Indsæt dette i din eksisterende template-opsætning, hvis du ønsker en egen sensor baseret på en forespørgsel. Tilpas navne og drivmiddel. Det er valgfrit; de valgbare stationssensorer kræver ingen YAML.

```yaml
template:
  - triggers:
      - trigger: time_pattern
        minutes: "/5"
      - trigger: homeassistant
        event: start
    actions:
      - action: tiny_refuel.get_stations
        data:
          fuel: p95
          sort: price
          limit: 1
        response_variable: refuel_result
    sensor:
      - name: Min billigste benzin
        unique_id: min_tiny_refuel_benzin
        unit_of_measurement: DKK/L
        state_class: measurement
        availability: "{{ refuel_result is defined and refuel_result['items'] | count > 0 }}"
        state: "{{ refuel_result['items'][0]['prices']['p95'] if refuel_result is defined and refuel_result['items'] | count > 0 else none }}"
```

Forespørgslen læser kun integrationens fælles cache. Dataindsamling styres fortsat af Tiny Refuels interval, knap eller refresh-handling.
