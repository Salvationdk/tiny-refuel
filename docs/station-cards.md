# Stationskort uden køretøj

De eksisterende kort og gemte køretøjer bevares. Tre ekstra kort registreres
automatisk i Home Assistants kortvælger med visuel editor:

- **Tiny Refuel · Prisoversigt**: søgning, drivmiddel, selskaber, pris/afstand/navn,
  valgfri radius, position og kompakt visning.
- **Tiny Refuel · Station**: én station med priser, navigation og prishistorik.
- **Tiny Refuel · Favoritter**: udvalgte stationer med valg gemt i Lovelace.

Intet køretøj eller tank/batterikapacitet er nødvendigt. Positionsenhed er
kun nødvendig for afstand/radius. Afstand vises i luftlinje. Generelle
selskabstakster indgår ikke som lokale stationspriser. Ukendte priser vises
som manglende; gemte fejlramte data markeres og sorteres efter aktuelle priser.
Ved alle drivmidler sammenlignes liter og kWh ikke i prissorteringen.

Vælg stationer og favoritter i editoren. Stationsidentiteter er baseret på
selskab og udbyder-ID, adresse eller koordinater. Ladeformer adskilles.
Ændringer i kilde-ID/adresse kan kræve et nyt stationsvalg.

## Historik

Efter en vellykket hentning gemmes ændrede, aktuelle lokale priser i
`.storage/tiny_refuel/price-history.sqlite3`. Ingen køretøjsoplysninger,
positionsenheder eller brugerpositioner gemmes i historikken. Fejl i
historiklagringen stopper ikke indsamlingen; stationskortene viser fejlen.

Under integrationsindstillinger → Opdateringsinterval kan perioden vælges
fra 0 til 365 dage. Standard er 90 dage; 0 stopper ny registrering og
historikvisning, men sletter ikke en allerede eksisterende database.
Oprydning sker ved næste vellykkede hentning. Én tidligere observation pr.
station/drivmiddel bevares som udgangspunkt for en uændret pris.

Historikken starter ved aktivering; eksisterende cache importeres ikke som
nye observationer. Grafen viser registrerede ændringer med en tabel over de
seneste 12 punkter. Et udgangspunkt markeres særskilt. Observationer er ikke
en garanti for en pris mellem hentningerne. API'et begrænser svaret til
2000 ændringer og oplyser, hvis en kortere periode skal vælges.

## API

Begge endpoints kræver Home Assistant-login og bruger `Cache-Control: no-store`:

- `GET /api/tiny_refuel/stations`
- `GET /api/tiny_refuel/history/{station_id}?field=p95&days=7`

Drivmidler er `p95`, `p100`, `diesel`, `kwh`; periode er 1–365 dage og
begrænses til den valgte opbevaringsperiode. Historik leveres først ved åbning,
ikke i sensorattributter. Kortene deler stationshentninger og opdaterer deres
visning hvert minut; dette udløser ikke en ny scraping.

## Eksempler

```yaml
type: custom:tiny-refuel-prices-card
fuel: p95
sort: price
limit: 8
```

```yaml
type: custom:tiny-refuel-favorites-card
fuel: all
favorites: []  # Vælg stationer i den visuelle editor
```

Kortene kan placeres på eksisterende eller nye betjeningspaneler. Der
oprettes ikke automatisk et nyt betjeningspanel, og eksisterende Lovelace
ændres ikke. Stationer på HA's indbyggede kort er en separat kommende opgave.
