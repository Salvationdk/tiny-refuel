# Kontrollér et eksisterende køretøjskatalog lokalt

Python 3.10 eller nyere, ingen ekstra pakker. Kør fra projektmappen:

```powershell
python scripts/verify_vehicle_catalog.py --input "C:\sti\bilkatalog_online_beriget.json"
```

Værktøjet kontrollerer også allerede udfyldte værdier. Det bruger projektets liste
med producentkilder og to åbne datasæt. Wikipedia kontaktes ikke. Datasættet med
motorvarianter fylder cirka 85 MB. Kilderne dækker kun en del af kataloget;
programmet foretager ikke en fri websøgning efter alle modeller.

Originalfilen ændres ikke. Resultater ligger i `tiny-refuel-kontrol`:

- `summary.json`: antal, kildefejl og status.
- `verification.json`: sammenligning pr. model og felt med kilder og variantoplysninger.
- `suspicious.json`: poster til prioriteret kontrol; flag er ikke bevis på fejl.
- `kontrol-resultat.zip`: rapporter til gennemgang, uden downloadcache.

Genbrug samme outputmappe ved næste kørsel. Producentersider og datasæt caches.
`--offline` bruger kun cachen. Ved HTTP 403, 429 eller 503 pauses producentens
vært resten af kørslen; rapporten indeholder eventuel Retry-After. Vent til
serverens angivne tidspunkt før en ny onlinekørsel. Ingen omgåelse af blokeringer.

Kun lokal kontrol og tidligere indsamlede kandidater:

```powershell
python scripts/verify_vehicle_catalog.py --input "bilkatalog_online_beriget.json" --skip-online --candidates "all-candidates.json"
```

Enighed om et tal er ikke automatisk verifikation af alle årgange og varianter.
Alle resultater kræver gennemgang af model, variant, årgang og marked.
Batterier sammenlignes kun direkte, når begge kilder angiver samme grundlag
(`battery_basis`: `usable` eller `gross`). Manglende kilder betyder uafklaret.
Generelle mærkestandarder anvendes ikke. Ingen værdier importeres automatisk.
Åbne datasæt er sekundære kilder; deres licens og kildehistorik følger kandidaterne.

## DMR

Bevar den oprindelige ZIP. Det eksisterende udtræk `bilkatalog-med-typer.json`
kan genbruges til registeridentitet og kategorier. De tidligere undersøgte DMR-felter
indeholder ikke dokumenterede tank- og batterikapaciteter. Et DMR-modelmatch
bekræfter derfor ikke katalogets kapacitet. Registrerede årgange, varianter og
drivmidler kan hjælpe med at afgrænse den eksterne specifikation; historiske
registreringstyper kan overlappe og kræver særskilt gennemgang.

Tilføj registerkontrol med det eksisterende udtræk (ingen genlæsning af ZIP):

```powershell
python scripts/verify_vehicle_catalog.py --input "bilkatalog_online_beriget.json" --dmr-catalog "bilkatalog-med-typer.json"
```

`dmr-check.json` indeholder præcise modelmatch og de registrerede drivmidler,
typer og årgangsoplysninger. At en model mangler i udtrækket beviser ikke, at den
ikke eksisterer. DMR-kontrollen godkender ingen kapaciteter.
