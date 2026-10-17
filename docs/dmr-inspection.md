# DMR: kontrollér tekniske felter og køretøjstyper

Brug den eksisterende ZIP direkte. XML-filen skal ikke pakkes ud. Python 3.10 eller nyere kan bruges. Hent den nyeste udgave af `scripts/dmr_catalog.py` sammen med `scripts/vehicle_catalog.py`.

En prøve på de første 100.000 poster:

```bat
python scripts/dmr_catalog.py inspect --input "E:\DRM\ESStatistikListeModtag\ESStatistikListeModtag-20261007-160843.zip" --limit 100000 --output "E:\DRM\dmr-teknik-test.json"
```

Hele filen, med fremdrift for hver 100.000 poster:

```bat
python scripts/dmr_catalog.py inspect --input "E:\DRM\ESStatistikListeModtag\ESStatistikListeModtag-20261007-160843.zip" --output "E:\DRM\dmr-teknik-alle.json"
```

Rapporten indeholder antal poster pr. kombination af køretøjsartens kode og navn samt højst 20 forskellige rå eksempelværdier pr. teknisk felt. En prøve kan ikke vise alle typer eller alle værdier. Rapporten skrives, når gennemløbet er afsluttet. Hele gennemløbet skal stadig læse den store XML-strøm og kan tage lang tid.

Nummerplader, stelnumre, køretøjs-ID'er, kilometertal og fritekst eksporteres ikke. Eksempelværdierne er ikke hele køretøjsposter. Rapporten fastslår ikke måleenheder eller relationer mellem indlejrede målenormer; de skal verificeres, før forbrugstal bruges i beregninger.

`build` bevarer rå kombinationer i modellens `dmr_profiles`, herunder variantnavn, EU-variant/version, modelår, drivmidler, motoreffekt, slagvolumen og forbrugs-/normfelter, når de findes. Identiske kombinationer samles. Der dannes ikke kombinationer på tværs af poster. Flere værdier i samme kildepost bevares som lister, uden at en bestemt norm antages at høre til en bestemt måling. De rå profiler anvendes endnu ikke som bekræftede specifikationer i kortet. Eksisterende kuraterede tank- og batteriværdier bevares.

Køretøjsart 1–4 og genkendte navne på motorcykler, knallerter, traktorer, motorredskaber, motorkøretøjer og ATV medtages. Ukendte navne/koder kræver gennemgang af rapporten. Påhængs-, sætte- og campingvogne samt sidevogne udelades; et brændstoffelt alene er ikke bevis for egen fremdrift. Det fulde katalog med alle relevante typer kræver en ny `build` fra ZIP-filen efter gennemgang af typerne. Det gamle JSON-katalog indeholder ikke de nye felter eller tidligere frasorterede typer.
