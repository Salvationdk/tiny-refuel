# Lokal gennemgang af indsamlede køretøjsforslag

Kør uden LLM eller netværk:

```sh
python scripts/review_vehicle_specs.py --input resultater/all-candidates.json --output review-results
```

Originalfilen og integrationens katalog ændres ikke. Identiske navne normaliseres kun for store/små bogstaver og mellemrum. Årgang, årgangsinterval, generation, variant, trim og markeder indgår i grupperingen. Manglende oplysninger betyder ukendt anvendelse, ikke at en værdi gælder alle varianter. Brutto-, brugbar og uspecificeret batterikapacitet sammenlignes som forskellige felter.

Filerne er:
- `summary.json`: optælling og SHA-256 for inputfilen.
- `variant-import-proposal.json`: forslag pr. angivet variant/årgang uden intern værdikonflikt. Alle har `approved_for_import: false` og skal gennemgås.
- `scope-conflicts.json`: forskellige værdier for samme angivne kombination. Det kan skyldes fejl eller oplysninger, som kilden ikke skelner, fx marked eller karrosserilængde.
- `model-summary.json`: observerede værdier pr. model og felter med flere forskellige værdier. En enkelt observeret værdi er ikke en verificeret modelstandard.
- `provenance.json`: kilde, licens, inputposition og evidens pr. kandidat-ID.
- `rejected.json`: afviste felter/poster, fx negative eller ugyldige kapaciteter.

Kontrollerne opdager syntaks-, format- og interne værdiproblemer. De beviser ikke, at en specifikation er korrekt. Værdier fra fællesskabsdatasæt skal stadig efterprøves mod en konkret kilde før godkendelse. Forslagene er ikke et format, som det aktuelle frontendkatalog kan indlæse direkte. De forbereder en senere gennemgået import, uden at tildele en hel modelserie én variants kapacitet.

Gennemgangen af brugerens fil den 18. oktober 2026 gav 8.257 poster til 694 modeller: 8.238 angivne kombinationer, hvoraf 19 har forskellige værdier inden for kombinationen. 426 modeller har kun én observeret værdi pr. indsamlet felt; 268 har variation. 8.219 kombinationer ligger i importforslaget til videre gennemgang, og ingen er automatisk godkendt. De 19 tilfælde er ikke blevet fjernet fra originalen.

Koden anvender projektets licens; de indsamlede data har fortsat deres egne kilde-/datasætlicenser. Bevar især ODbL- og CDLA-oplysninger ved senere brug og deling.
