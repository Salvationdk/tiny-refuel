# Tiny Refuel v0.1

Benzin, diesel og opladning til biler i Home Assistant. Tiny Refuel samler kort, visuel editor, selskabslogoer og scraping i én HACS-integration.

## Installation

### HACS

Tiny Refuel kan installeres gennem [HACS](https://hacs.xyz/) (Home Assistant Community Store).

Brug knappen til at åbne Tiny Refuel direkte i HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Salvationdk&repository=tiny-refuel&category=integration)

*eller*

1. Installér HACS, hvis du ikke allerede har det.
2. Åbn HACS i Home Assistant.
3. Vælg **menuen med tre prikker → Brugerdefinerede repositories**.
4. Tilføj `https://github.com/Salvationdk/tiny-refuel` med typen **Integration**.
5. Søg efter **Tiny Refuel**, og tryk på **Download**. ⬇️

### Opsætning efter download

1. Genstart Home Assistant.
2. Gå til **Indstillinger → Enheder og tjenester → Tilføj integration → Tiny Refuel**. Vælg interval, som standard 6 timer.
3. Genindlæs browseren med **Ctrl+F5**. Tilføj **Tiny Refuel** i dashboardets kortvælger eller brug:

```yaml
type: custom:tiny-refuel-card
vis_benzin: true
vis_diesel: false
vis_el: true
vis_andet: true
```

4. Vælg din telefon/positions-enhed, biler og Waze eller Google Maps i den visuelle editor. Første scraping starter automatisk i baggrunden og kan tage flere minutter. **Scrape alle data** i kortet eller integrationens knap starter en fælles opdatering.

Kortets JavaScript indlæses af integrationen. Hvis kortet ikke findes efter genindlæsning, kan denne JavaScript-modulressource tilføjes manuelt under dashboardets ressourcer:

`/tiny_refuel/static/tiny-refuel-card-v0.1.js?v=0.1.0`

## Funktioner

- Benzin, diesel og EL efter valgt bil. Hybrid uden stik viser benzin; plug-in-hybrid viser benzin og opladning.
- Adresser og nærmeste sted med afstand **i luftlinje**. Waze/Google Maps beregner køreruten, når du trykker på selskabets logo.
- **Ladesteder** pr. selskab: nærmeste først, relevante AC/DC/Normal/Hurtig/Lyn-filtre, 10 ladevalg ad gangen og **Vis 10 mere**.
- Q8 samlet i én EL-celle. Generelle OK/Q8-takster er mærket som generelle og bliver ikke tilskrevet et bestemt ladested.
- **Fordele** med vilkår, hvor der findes relevante oplysninger. Medlemsrabat trækkes ikke automatisk fra priser.
- Antal unikke ladesteder, selskaber og steder med konkret lokal elpris. AC/DC på samme sted tælles én gang pr. selskab. Generelle takster tæller ikke som lokale priser.
- Én opdateringshandling for alle kilder. Gentagne klik deler den igangværende hentning; de starter ikke parallelle scraperkørsler.
- Tre status-sensorer: antal ladesteder, antal steder med lokal elpris og seneste hentning. En fælles opdateringsknap og handlingen `tiny_refuel.refresh`.

## Kilder og begrænsninger

Kun frit tilgængelige kilder uden betalt eller registreret API-adgang bruges. Der kræves ikke en konto hos ladeselskaberne for indsamlingen. Betaling og adgang ved selve ladestedet følger selskabets vilkår.

| Selskab | Oplysninger fra anvendt kilde |
|---|---|
| Circle K / INGO | Offentlige brændstofpriser; Circle K også danske ladesteder, stiktyper og effekt |
| Q8 / F24 | Stationspriser inklusive HPC, når oplyst; Q8's generelle ladetakster vises særskilt |
| Go'on / Shell / Uno-X | Eksisterende offentlige brændstofkilder; Shell og Uno-X også ladesteder |
| OK / OIL | Lokale brændstofpriser og ladeadresser; generelle OK-ladetakster særskilt |
| Clever / E.ON | Ladesteder, adresser, koordinater og AC/DC/effekt, når oplyst |
| Tesla | Offentlige danske steder åbne for andre bilmærker; hentning kan blive afvist med HTTP 403 |
| IONITY | Aktive danske steder, koordinater og effekt/antal, når oplyst; ingen gadeadresse i udtrækket |

Ved vellykket hentning erstattes selskabets tidligere liste. Ved kildefejl bevares eventuelle tidligere data fra **denne installation**, tydeligt markeret som gemte data. En downloaddato er ikke en garanti for selskabets egen kontroltid. En første hentning kan give data fra nogle selskaber og fejl fra andre; fejlene vises i kortet.

Adressekoordinater, der ikke findes i selskabets kilde, kan slås op med Nominatim, maksimalt 30 nye adresser pr. kørsel. Det er stationsadresser, ikke din GPS-position. Din valgte telefonposition bruges i browseren til afstande. Den ønskede destination sendes til Waze/Maps ved navigation.

## Filer og opdateringer

HACS installerer al kode og alle medfølgende aktiver under `custom_components/tiny_refuel/`. Genererede prisdata, ny historik og koordinatcacher gemmes privat under `.storage/tiny_refuel/` og overlever kodeopdateringer. Der skrives ikke i HACS' kodefiler under scraping. Data til kortet leveres gennem en Home Assistant-API, der kræver login.

Bilkatalog og standardlogoer ligger under integrationens `frontend/`. Direkte ændringer dér kan blive overskrevet af en HACS-opdatering. Eget bilkatalog kan i stedet vælges med en brugerdefineret URL i korteditoren.

For en bevidst ren start: fjern integrationen under Enheder og tjenester, og slet kun mappen `.storage/tiny_refuel/`, mens integrationen er stoppet. Tilføj integrationen igen. HACS-afinstallation eller fjernelse af integrationen sletter ikke automatisk dataene.

## Udvikling og test

Minimum Home Assistant: **2025.11.0**. Teknisk version: **0.1.0**; kortets footer viser **Tiny Refuel v0.1**.

```bash
python -m unittest discover -s tests -v
node tests/frontend.test.js
```

Automatiske checks kører gennem GitHub Actions. Versionsnummer, HACS-struktur og integrationens manifest følger med. Faktisk layout, telefonnavigation og selskabernes fortsatte datatilgængelighed skal afprøves i installationen.
