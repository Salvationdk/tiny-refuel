# Lokal katalogkørsel

Python 3.10 eller nyere. Ingen ekstra Python-pakker, konti eller betalte API-nøgler kræves. Hent projektets ZIP fra den aktuelle PR-branch og pak den ud. Åbn PowerShell i projektmappen og kør:

```powershell
python scripts/run_local_catalog.py --input "C:\sti\til\bilkatalog-med-typer.json"
```

Programmet renser mærke/modelnavne konservativt, bevarer køretøjstyper og kendte specifikationer og laver kategori- og mangelrapporter. Det indsamler derefter kandidater fra de gennemgåede producentkilder, OpenEV, det åbne motordatasæt og engelske Wikipedia-infobokse. Wikipedia bruger præcise navne og enheder; uklare intervaller, familieredirects og ukendt gallon-type accepteres ikke som en enkelt kapacitet. Lastbiler, busser, motorcykler, knallerter og traktorer slås op før personbiler.

Kørslen arbejder lokalt og behøver ikke en åben chat. Internetopslag kan tage lang tid. Der vises fremdrift i terminalen. Genstart med samme kommando og outputmappe for at genbruge cachen. Ved tre mislykkede Wikipedia-batches i træk stoppes den kilde, og resten af resultatpakken skrives. Netværksfejl og manglende fund er ikke dokumentation for, at en model ikke findes.

Når terminalen skriver **FÆRDIG**, ligger `send-til-gennemgang.zip` i `tiny-refuel-resultat`. Den indeholder katalogkladde, unikke modeller pr. kategori, kapacitetsmangler, mulige typeoverlap, kildehenvisninger og forslag/konflikter. Cache og downloadede rå datasæt kommer ikke med i pakken. Kildekataloget overskrives ikke, og ingen onlinekandidat importeres automatisk. Pakken er til gennemgang, ikke en færdig release.

## Ekstra muligheder

Kun lokal rensning og rapporter:

```powershell
python scripts/run_local_catalog.py --input "C:\sti\til\bilkatalog-med-typer.json" --skip-online
```

Genbrug tidligere indsamlede kandidater:

```powershell
python scripts/run_local_catalog.py --input "C:\sti\til\bilkatalog-med-typer.json" --candidates "C:\sti\til\all-candidates.json"
```

`--offline` bruger kun eksisterende caches. `--wiki-limit 200` begrænser Wikipedia til de første 200 prioriterede modeller. Standardværdien 0 forsøger alle modeller med manglende data. Afbryd med Ctrl+C og kør samme kommando igen for at fortsætte med cachen.

Onlinekandidater skal gennemgås for korrekt identitet, årgang/variant, marked samt nominel kontra brugbar batterikapacitet. DMR-kategorier kan indeholde historiske eller usædvanlige registreringer; overlaprapporten gør dem synlige uden at gætte en ny type.
