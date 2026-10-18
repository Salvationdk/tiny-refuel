# Visuel test i Home Assistant

GitHub Actions-workflowet **Visual Home Assistant** starter en midlertidig Home
Assistant 2026.10-installation og Chromium. Det installerer Tiny Refuel gennem
integrationen, opretter et Lovelace-dashboard og bruger det indbyggede
`katalog.json`. Ingen privat Home Assistant-adgang eller API-nøgler er nødvendige.

Priser, ladesteder og GPS-position er faste, fiktive testdata. Kun indsamlingen af
eksterne data erstattes i testmiljøet. Testen kontrollerer derfor visning og
betjening, ikke om leverandørernes hjemmesider kan hentes.

## Billeder og kontroller

Der tages billeder ved desktopbredde og 390 px mobilbredde, i lyst og mørkt tema:

- Benzin, diesel og kompakt kort med billigste pris.
- Ladeoversigt og popup med ladesteder.
- Plug-in-hybrid med flere køretøjer.
- Information og datagrundlag.
- Kildefejl med tidligere gemte data samt integrationens side i Home Assistant.
- Editorens oversigt, udbydere, køretøj og ekstra køretøjsfelter.

Browseren klikker også på **Vis 10 mere** / **Vis færre** og kontrollerer antallet
af rækker. I editoren skiftes mærke og model; gamle model- og tankværdier skal
forsvinde, og valg af en ny katalogmodel skal udfylde kapaciteten. Kataloget skal
indlæses, og browserfejl får testen til at fejle.

Kortet vises i det rigtige Lovelace-dashboard. Editorbillederne viser den rigtige
editor med Home Assistants `hass`-objekt og tema; testværktøjet monterer den direkte
på siden og sender konfigurationsændringer tilbage som Lovelace. Home Assistants
egne menuer til at åbne og gemme korteditoren testes ikke dermed.

Kort- og editorbilleder beskæres til komponenten. Home Assistants faste
værktøjslinje og midlertidige toastbeskeder skjules kun under selve billedtagningen,
så de ikke dækker indholdet. Integrationssiden fotograferes som en hel side.

## Hent eller gentag

1. Åbn repositoryets **Actions → Visual Home Assistant**.
2. Vælg en afsluttet kørsel og hent **Artifacts → tiny-refuel-visual**.
3. ZIP-filen indeholder PNG-billeder, `report.json` med teststatus og en
   Home Assistant-log til fejlsøgning. Ved en bestået test kan `index.html` åbnes
   som samlet billedoversigt.

Workflowet kører automatisk ved relevante ændringer i en PR og på de angivne
branches. Efter workflowet er på standardbranchen, kan **Run workflow** bruges.
Indtil da kan en tidligere kørsel gentages med **Re-run all jobs**. Der bruges
GitHub Actions-minutter; kørslen kan gentages direkte på GitHub.

## Kør lokalt

Brug et separat Python 3.14-miljø på Linux med adgang til netværkskort og lokal
port 8123. Start ikke testen oven i en eksisterende Home Assistant på den port.

```sh
python3.14 -m venv .venv
. .venv/bin/activate
pip install -r tests/visual/requirements.txt
python -m playwright install --with-deps chromium
sudo apt-get install -y ffmpeg libturbojpeg
python tests/visual/run.py
```

Resultater gemmes i `visual-results/`, som ikke trackes af git. Midlertidig
Home Assistant-konfiguration og testlogin slettes, når kørslen slutter. Traces
og loginoplysninger gemmes ikke i downloadpakken. Billeder er materiale til
visuel gennemgang, ikke automatisk pixel-sammenligning med godkendte referencebilleder.

## Gennemført kørsel

[GitHub-kørsel 39167301022](https://github.com/Salvationdk/tiny-refuel/actions/runs/39167301022) bestod med 49 screenshots og ingen browserfejl. Der er gennemgået billeder af kort, kompakt visning, ladepopup, kildefejl, information, editor og integrationsside. Testdata er fiktive.
