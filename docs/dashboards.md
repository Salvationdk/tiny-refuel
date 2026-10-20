# Ekstra kort og betjeningspaneler

Alle kort er valgfrie. Det oprindelige `custom:tiny-refuel-card`, dets editor,
køretøjer og opsætninger bevares. De ekstra kort registreres automatisk i
Home Assistants kortvælger og kræver ingen andre frontend-udvidelser.

| Kort i kortvælgeren | Type | Indhold |
|---|---|---|
| Tiny Refuel · Mine køretøjer | `custom:tiny-refuel-vehicles-card` | Fælles køretøjer, nærmeste relevante steder og beregnet pris for hele kapaciteten |
| Tiny Refuel · Prissammenligning | `custom:tiny-refuel-comparison-card` | Samme drivmiddel, enhedspris, afstand, hel kapacitet og merpris mod billigste i udvalget |
| Tiny Refuel · Køretøjsoplysninger | `custom:tiny-refuel-vehicle-details-card` | Gemte oplysninger, årgang, variant, kapacitet, kontrolstatus og tilgængelige kilder |
| Tiny Refuel · Opladning | `custom:tiny-refuel-charging-card` | Lokale ladesteder og separat afsnit med generelle takster |
| Tiny Refuel · Datastatus | `custom:tiny-refuel-status-card` | Kilder, fejl, kataloger, historik og kortmarkører; start af datahentning |

De tre tidligere stationskort (Prisoversigt, Station og Favoritter) kan bruges
på de samme paneler. Kortene bruger det fælles tema, fungerer på mobil og
computer og understøtter lyst/mørkt tema og kompakt visning.

## Køretøjskort

Tilføj fælles køretøjer under Tiny Refuels integrationsindstillinger. Vælg
et bestemt køretøj eller alle i kortets visuelle editor. Kortene ændrer ikke
værdierne i køretøjet. Tidligere kort med egne køretøjer fungerer fortsat;
for avanceret brug kan de nye kort også få en `biler`-liste i samme format.

Omkostninger beregnes kun fra positive kapaciteter og aktuelle lokale priser.
Uden kapacitet vises enhedsprisen uden total. Uden position kan priser
sammenlignes, hvis radius er 0; nærmeste sted kræver en position. Afstand er
i luftlinje. En plug-in-hybrid skifter mellem relevante drivmidler; liter
og kWh sammenlignes ikke som samme produkt. Aktuelt tankindhold/batteriniveau,
ladetab, abonnement og gebyrer indgår ikke i en beregning for hel kapacitet.

Detaljer viser tilgængelig kontrolstatus fra det gemte køretøj. Manglende
status bliver ikke til en godkendelse. Katalogvalg bevarer kildehenvisninger
og kontrolstatus; ændres kapacitet, drivmiddel, årgang eller variant ved
lagring, markeres oplysningerne til kontrol igen.

## Stationer på Home Assistants indbyggede kort

Åbn **Indstillinger → Enheder og tjenester → Tiny Refuel → Konfigurer →
Stationer på HA-kortet**. Funktionen er slået fra som standard.

Vælg radius (1–500 km), selskaber, maksimal markørmængde (1–250) og eventuelt
bestemte stationer. Uden positionsenhed bruges HA's hjemmeplacering. En valgt
positionsenhed, der er utilgængelig, medfører ingen markører; der skiftes ikke
ubemærket til en anden placering. Udvælgelsen opdateres ved pris-/positions-
ændringer. De nærmeste match vises først op til markørgrænsen.

Kun fysiske stationer med koordinater får `geo_location`-entiteter. Generelle
selskabstakster får ingen markører. Markørernes oplysninger omfatter priser,
enheder, adresse, ladeform, seneste hentning og om priserne er aktuelle.
Når en station falder uden for udvalget, fjernes dens aktive markør. HA's
eget kort styrer markørdesign og kortbaggrund.

Tilføj et indbygget kort med den geografiske kilde **tiny_refuel**:

```yaml
type: map
title: Stationer
geo_location_sources:
  - tiny_refuel
```

Kortets visuelle editor kan også vælge geolokationskilder. Uden aktiverede
markører er kortet tomt; det downloader ikke selv stationsdata.

## Samlede betjeningspaneler

[examples/dashboards.yaml](../examples/dashboards.yaml) indeholder fire visninger:
**Priser**, **Opladning**, **Mine køretøjer** og **Datastatus**. Ingen paneler
oprettes eller overskrives automatisk. Man kan bygge dem ved at tilføje
kortene i UI eller indsætte YAML-eksemplet i et nyt betjeningspanel. Vælg
station/favoritter og køretøjer i de enkelte korts editor bagefter.

## Kontrol

Python-tests dækker map-filtre, tilvalg, markørgrænse, manglende position,
stabile opdateringer/fjernelse af entiteter, generelle takster og API-resuméer.
Frontend-tests dækker de ni kortregistreringer og beregninger. Den visuelle
HA/Chromium-test kontrollerer både eksisterende og nye kort, editorer og
HA's eget kort på mobil/computer i lyst/mørkt tema med faste prøvedata.
