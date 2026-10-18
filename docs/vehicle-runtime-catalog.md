# Kompakt køretøjs-JSON til Tiny Refuel

`python -m scripts.build_enriched_vehicle_catalog --catalog FULL.json --candidates all-candidates.json --output tiny-refuel-koeretoejer.json` bygger en almindelig JSON, som Tiny Refuels eksisterende katalog_url kan læse direkte.

Filen indeholder mærke, model, drivmiddel når kendt, tank_l/batteri_kwh, logoer, hjælpetekst og korte kildehenvisninger. Varianter, årgangsinventarer og komplette evidensrækker udelades fra driftsfilen; originalerne ændres ikke. Eksisterende kapaciteter overskrives ikke. Kun et enkelt observeret kapacitetsniveau pr. felt kan udfylde en manglende modelstandard. Modeller med intern konflikt for samme angivne variant udelades fra berigelsen. Tvetydig brugbar batterikapacitet må ikke erstattes af en entydig bruttoværdi.

Nye værdier mærkes `source_dataset_default_not_manufacturer_verified`, og hjælpeteksten beder brugeren kontrollere den konkrete årgang/variant. Det er et praktisk kildebaseret udgangspunkt, ikke en fabrikantverifikation af hele modelserien. Manglende drivmiddel kan vælges manuelt. Kun modeller med positiv tank-/batteristørrelse medtages; motorredskaber udelades, hvor typen er kendt.

Den første fil giver 895 modeller fra 89 mærker (425 flere modeller end det tidligere udvalg med 470) og fylder cirka 2,56 MB inklusive logoer. 429 manglende kapacitetsfelter er tilføjet; fire ligger på allerede medfølgende modeller. Den leverede fil indeholder også datasætternes licenstekster. Ved ny distribution skal de medfølge igen; kildehenvisningerne og licens-URL'erne genereres af værktøjet.

Integrationen leverer nu filen som frontend/katalog.json, og den bruges automatisk med tom katalog_url. Der skal ikke installeres en ekstra fil i www. Vil du bygge din egen, så kopiér standardfilen, ret den, validér med scripts/validate_vehicle_catalog.py, og læg den i /config/www/katalog.json. Angiv derefter katalog_url: /local/katalog.json. Genindlæs browseren efter ændringen. Det kræver ingen ændring i configuration.yaml.
