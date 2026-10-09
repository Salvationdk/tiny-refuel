# Tiny Refuel v0.1

Benzin, diesel og opladning til biler i Home Assistant. Tiny Refuel samler kort, visuel editor, selskabslogoer, bilkatalog og scraping i én HACS-integration.

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
5. Søg efter **Tiny Refuel**, og tryk på **Download**.

### Opsætning efter download

1. Genstart Home Assistant.
2. Gå til **Indstillinger → Enheder og tjenester → Tilføj integration → Tiny Refuel**.
3. Vælg opdateringsinterval. Standard er hver 6. time.
4. Genindlæs browseren med **Ctrl+F5**.
5. Tilføj **Tiny Refuel** fra dashboardets kortvælger.
6. Vælg din positionsenhed, biler og Waze eller Google Maps i den visuelle editor.

Kort, editor, selskabslogoer, bilkatalog og scraper følger med integrationen. Kortets JavaScript indlæses automatisk.

Kortet kan også tilføjes med YAML:

```yaml
type: custom:tiny-refuel-card
vis_benzin: true
vis_diesel: false
vis_el: true
vis_andet: true
```

Første scraping starter automatisk i baggrunden og kan tage flere minutter. **Scrape alle data** i kortet eller integrationens knap starter en fælles opdatering.

Hvis kortet ikke findes efter genindlæsning, kan denne ressource tilføjes manuelt under dashboardets ressourcer med typen **JavaScript-modul**:

```text
/tiny_refuel/static/tiny-refuel-card-v0.1.js?v=0.1.3
```

## Eksempler fra v0.1

Billeder fra en faktisk Home Assistant-installation. Priser og datastatus er øjebliksbilleder fra 8. oktober 2026.

### Benzin

Selskabslogoer, priser, adresser og bilvalg.

![Benzinpriser](https://raw.githubusercontent.com/Salvationdk/tiny-refuel/main/docs/images/benzin-v0.1.png)

### Hybrid uden stik

Hybrid uden stik viser benzin. Plug-in-hybrid kan vise både benzin og opladning.

![Hybrid med benzinpriser](https://raw.githubusercontent.com/Salvationdk/tiny-refuel/main/docs/images/hybrid-v0.1.png)

### EL

Ladepriser, generelle selskabstakster og knapper til ladesteder. Position er ikke valgt i dette eksempel.

![Ladepriser og ladesteder](https://raw.githubusercontent.com/Salvationdk/tiny-refuel/main/docs/images/el-v0.1.png)

### Datastatus

Antal ladesteder, steder med lokal elpris og status for datakilder. Eksemplet viser en fejl hos Tesla.

![Antal ladesteder og datastatus](https://raw.githubusercontent.com/Salvationdk/tiny-refuel/main/docs/images/el-datastatus-v0.1.png)

### Visuel editor

Vælg drivmidler, selskaber og biler med forhåndsvisning af kortet.

![Kortets visuelle editor](https://raw.githubusercontent.com/Salvationdk/tiny-refuel/main/docs/images/editor-v0.1.png)

### Navigation

Vælg Waze eller Google Maps. Navigation åbnes ved tryk på selskabets logo.

![Valg af Waze eller Google Maps](https://raw.githubusercontent.com/Salvationdk/tiny-refuel/main/docs/images/navigation-v0.1.png)

### Bilkatalog

Vælg bilmærke og model fra kataloget, eller indtast bilen manuelt.

![Valg af bilmærke fra kataloget](https://raw.githubusercontent.com/Salvationdk/tiny-refuel/main/docs/images/bilkatalog-v0.1.png)

## Funktioner

- Benzin, diesel og EL efter valgt bil.
- Hybrid uden stik viser benzin; plug-in-hybrid viser benzin og opladning.
- Adresser og nærmeste sted med afstand i luftlinje.
- Navigation gennem Waze eller Google Maps ved tryk på selskabets logo.
- **Ladesteder** pr. selskab med nærmeste først og relevante AC/DC/Normal/Hurtig/Lyn-filtre.
- 10 ladevalg ad gangen med mulighed for at vise flere.
- Q8 samlet i én EL-celle.
- Generelle OK/Q8-takster vises særskilt fra konkrete lokale priser.
- **Fordele** med vilkår, hvor der findes relevante oplysninger.
- Antal unikke ladesteder, selskaber og steder med konkret lokal elpris.
- Én opdateringshandling for alle kilder.
- Gentagne klik deler den igangværende hentning.
- Tre status-sensorer: antal ladesteder, antal steder med lokal elpris og seneste hentning.
- En fælles opdateringsknap og handlingen `tiny_refuel.refresh`.

AC og DC på samme sted tælles én gang pr. selskab. Generelle selskabstakster tæller ikke som lokale priser. Medlemsrabat trækkes ikke automatisk fra priserne.

## Datakilder

Kun frit tilgængelige kilder uden betalt eller registreret API-adgang bruges.

| Selskab | Oplysninger fra anvendt kilde |
|---|---|
| Circle K / INGO | Offentlige brændstofpriser; Circle K også danske ladesteder, stiktyper, effekt og daglig listepris for lynladning |
| Q8 / F24 | Stationspriser inklusive HPC, når oplyst; Q8's generelle ladetakster vises særskilt |
| Go'on / Shell / Uno-X | Offentlige brændstofkilder; Shell og Uno-X også ladesteder |
| OK / OIL | Lokale brændstofpriser og ladeadresser; generelle OK-ladetakster særskilt |
| Clever | Ladesteder, adresser, koordinater og AC/DC/effekt, når oplyst. Prisen varierer pr. sted og tidspunkt og skal ses i Clever-appen/kortet |
| E.ON | Ladesteder, adresser, koordinater og AC/DC/effekt, når oplyst; offentlige danske startpriser vises som generelle takster |
| Tesla | Danske Superchargere med adgangsmarkering, adresser, koordinater, effekt og antal ladepunkter. Separate lokale priser for Tesla/medlemmer og andre biler uden medlemskab, når oplyst. Hentning kan blive afvist med HTTP 403 |
| IONITY | Aktive danske steder, koordinater og effekt/antal, når oplyst; ingen gadeadresse i udtrækket. Offentlige minimumspriser for app, direkte betaling og abonnement vises særskilt |

Ved vellykket hentning erstattes selskabets tidligere liste. Ved kildefejl bevares eventuelle tidligere data fra denne installation, tydeligt markeret som gemte data.

En downloaddato er ikke en garanti for selskabets egen kontroltid. En hentning kan give data fra nogle selskaber og fejl fra andre; fejlene vises i kortet.

Adressekoordinater, der ikke findes i selskabets kilde, kan slås op med Nominatim, maksimalt 30 nye adresser pr. kørsel. Det er stationsadresser, ikke din GPS-position.

Din valgte telefonposition bruges i browseren til afstande. Den ønskede destination sendes til Waze eller Google Maps ved navigation.

## Filer og opdateringer

HACS installerer kode og medfølgende aktiver under:

```text
custom_components/tiny_refuel/
```

Genererede prisdata, ny historik og koordinatcacher gemmes privat under:

```text
.storage/tiny_refuel/
```

Disse data overlever kodeopdateringer. Scraping ændrer ikke HACS' kodefiler. Data til kortet leveres gennem en Home Assistant-API, der kræver login.

Bilkatalog og standardlogoer ligger under integrationens `frontend/`. Direkte ændringer dér kan blive overskrevet af en HACS-opdatering. Eget bilkatalog kan vælges med en brugerdefineret URL i korteditoren.

Efter en opdatering gennem HACS: genstart Home Assistant, og genindlæs browseren.

### Ren start

1. Fjern integrationen under **Enheder og tjenester**.
2. Slet kun mappen `.storage/tiny_refuel/`, mens integrationen er stoppet.
3. Tilføj integrationen igen.

HACS-afinstallation eller fjernelse af integrationen sletter ikke automatisk de gemte data.

## Udvikling og test

Minimum Home Assistant: **2025.11.2**.

Automatiske tests bestået med Home Assistant **2026.10.0**.

Teknisk integrationsversion: **0.1.3**. Kortets footer viser **Tiny Refuel v0.1**.

GitHub Actions kører integrations- og frontendtests samt HACS-validering. Workflowet er sat til Home Assistant **2026.10.0**.

```bash
python -m unittest discover -s tests -v
node tests/frontend.test.js
```

Automatiske tests dækker ikke hele den visuelle brugeroplevelse, telefonnavigation eller selskabernes fortsatte datatilgængelighed.


## Rettelser i 0.1.1

Priser og adresser vises også uden koordinater. Kortet angiver, når nærmeste station ikke kan bestemmes eller kun er valgt blandt stationer med kendte koordinater. Op til 30 nye adresseopslag pr. kørsel fordeles på skift mellem selskaberne efter frasortering af cachede og gentagne adresser.


## Tesla-priser i 0.1.2

Tesla-rækken og listen over ladesteder viser **Tesla/medlemmer** og **Andre biler uden medlemskab** hver for sig. Begge vises uanset bilvalg; intet medlemskabsvalg eller login er nødvendigt. Den enkelte station er markeret med adgang for andre bilmærker.

Priserne hentes fra Teslas offentlige stationssider. Flere takster vises som et interval med de oplyste tidsvilkår; laveste pris fremstilles ikke som prisen lige nu. Manglende priser vises som ikke oplyst. Medlemsabonnement samt eventuelle trængsels- og parkeringsgebyrer indgår ikke i kWh-prisen. Tesla indgår ikke i den generelle beregning af fuld opladning, da den beregning kræver én entydig kWh-pris.

Ved et mislykket prisopslag beholdes stationen. Eventuelle tidligere priser markeres som gemte med deres oprindelige hentetid. Ved HTTP 403/429 stoppes yderligere prisopslag efter de allerede igangværende kald. Højst tre stationssider hentes samtidigt med en samlet startgrænse på tre minutter. Første hentning kan derfor tage længere tid.

Denne ændring kan ikke garantere adgang fra alle installationer, hvis Tesla afviser hentningen.
