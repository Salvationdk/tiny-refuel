# Byg et katalog med unikke modeller

Brug Python 3.10 eller nyere. Kør kommandoerne fra roden af den udpakkede Tiny Refuel-kildekode, hvor `scripts` og `custom_components` ligger. ZIP-filen med DMR-data skal ikke pakkes ud.

## Prøve: første 100.000 poster

```bat
python scripts/dmr_catalog.py build --input "E:\DRM\ESStatistikListeModtag\ESStatistikListeModtag-20261007-160843.zip" --source-date 2026-10-07 --limit 100000 --output "E:\DRM\catalog-test\bilkatalog.json" --report "E:\DRM\catalog-test\import-report.json"
```

## Hele udtrækket

```bat
python scripts/dmr_catalog.py build --input "E:\DRM\ESStatistikListeModtag\ESStatistikListeModtag-20261007-160843.zip" --source-date 2026-10-07 --output "E:\DRM\catalog-candidate\bilkatalog.json" --report "E:\DRM\catalog-candidate\import-report.json"
```

Fremdrift vises for hver 100.000 poster. Resultatet skrives, når gennemløbet er afsluttet. Den fulde kørsel kan tage lang tid. XML læses som en strøm, men hukommelsesforbruget vokser med antallet af forskellige modeller og tekniske kombinationer i resultatet. Det er ikke en konstant grænse på eksempelvis 24 MB.

Den medfølgende katalogfil er grundlaget, så logoer, kuraterede specifikationer og egne metadata bevares. De nye filer er kandidater; de erstatter ikke automatisk integrationens katalog.

## Hvad er en dublet?

Store/små bogstaver, overflødige mellemrum og forskellige Unicode-kodninger af samme bogstav ignoreres. Kun udtrykkeligt angivne fabrikantaliasser, eksempelvis VW og Volkswagen, samles. Tegnsætning og accenter fjernes ikke: `C4` og `C 4`, eller `AB` og `A-B`, forbliver forskellige. Lignende navne kræver manuel gennemgang.

En fabrikant/model vises som én katalogrække. Variantnavne og alle observerede drivmidler bevares. `model_years` og `fuel_types` giver et råt overblik pr. model; ved detaljeret eksport bevarer `dmr_profiles` kombinationerne fra de enkelte kildeposter, så et forbrugstal fra én årgang ikke blandes med motoren fra en anden. Flere værdier fra samme kildepost forbliver lister; scriptet gætter ikke deres indbyrdes relation. Flere drivmidler på modelniveau betyder ikke automatisk hybrid.

Profilerne er rå registeroplysninger og anvendes endnu ikke som bekræftede årgangs-/specifikationsvalg i kortets editor. Tank- og batterikapacitet udledes ikke. Eksisterende verificerede værdier bevares. Konflikter mellem eksisterende oplysninger gemmes i `deduplication_alternatives` og rapporten med `requires_review: true`. Ingen af de modstridende værdier bortkastes.

Den separate rapport viser antal kildeposter, frasorterede poster, mærker, modeller og unikke profiler samt sammenlægninger og konflikter fra grundkataloget. Katalogets `source_names` bevarer alternative modelstavemåder. Der bruges ingen fuzzy matching.

## Oprydning i et allerede dannet JSON-katalog

```bat
python scripts/dmr_catalog.py deduplicate --input "E:\DRM\catalog-candidate\bilkatalog.json" --output "E:\DRM\catalog-clean\bilkatalog.json" --report "E:\DRM\catalog-clean\oprydningsrapport.json"
```

Dette går hurtigt, men kan kun samle oplysninger, som allerede findes i JSON-filen. Det kan ikke tilføje de køretøjstyper eller tekniske felter, der blev udeladt af en ældre import, og kan heller ikke genskabe tidligere sammenlagte modelbetegnelser.

## Hvis kataloget allerede fylder flere hundrede MB

Det detaljerede udtræk kan gemme næsten en million forskellige `dmr_profiles`.
De skal ikke sendes til kortets editor. Behold originalen som forskningsgrundlag,
og lav en kompakt kopi uden at genlæse DMR-arkivet:

```bat
python scripts/compact_vehicle_catalog.py --input "E:\DRM\catalog-candidate\bilkatalog.json" --output "E:\DRM\catalog-candidate\bilkatalog-kompakt.json"
```

Scriptet bruger kun standardbiblioteket i Python 3.10+, læser JSON som en strøm
og skriver til en midlertidig fil før erstatning af resultatet. Hele den store
fil indlæses ikke i hukommelsen. Det validerer også de fjernede profilfelters
JSON-syntaks. Originalen overskrives ikke. Modeller, varianter, drivmidler,
årgangslister, egne metadata og logoer bevares; kun `dmr_profiles` under en model
fjernes, og indrykning komprimeres. De detaljerede relationer mellem årgang,
motor og forbrug ligger fortsat i originalen og kan ikke genskabes fra den
kompakte kopi alene. Kildens importstatistik i kopien beskriver originalimporten.
Scriptet viser faktisk input-/outputstørrelse og antal fjernede profiler.

Nye CLI-kørsler af `build` udelader nu de tunge profiler som standard. Tilføj
`--include-technical-profiles`, hvis et detaljeret forskningsudtræk ønskes.
Denne valgmulighed ændrer ikke den eksisterende store fil.

## Rensning efter import

```bat
python scripts/clean_vehicle_catalog.py --input "E:\DRM\catalog-candidate\bilkatalog-kompakt.json" --output-dir "E:\DRM\catalog-clean"
```

Scriptet bevarer originalen og skriver et separat katalog, en oprydningsrapport
og de udskilte originalposter. Det retter kun en lille udtrykkelig liste af
stavefejl, samler store/små bogstaver og mellemrum og bevarer øvrige modelnavne.
Rene tal er ugyldige som fabrikantnavne, men kan være gyldige modelnavne.
Historiske mærker, opbyggere og usikre forkortelser bevares. Ingen fuzzy matching.
Alle oprindelige SVG-/PNG-payloads bevares. Eksakte mærkealiasser forbindes med
eksisterende logoer, men sammensatte mærker får ikke blot chassismærkets logo.
Logodækningen genberegnes for hele det rensede katalog. Dette er en teknisk
oprydning, ikke en fuld historisk verifikation af alle fabrikantbetegnelser.

Kontrollen af brugerens fulde kompakte udtræk gav 1.829 mærkebetegnelser,
27.425 modeller og 98.937 variantposter. Fire ugyldige mærker med i alt 46
modelrækker blev udskilt: `-`, `10279`, `TESTKØRSEL` og `USPEC.MÆRKE`.
Sammenlægningerne gav ingen konflikter. Tank-/batteriværdier, årgangslister,
drivmidler og variantdrivmidler blev sammenholdt med alle bevarede kildeposter;
logoernes indhold blev sammenlignet direkte med originalen.
Kataloget er leveret separat til gennemgang og erstatter endnu ikke det
medfølgende katalog i integrationens frontend.
