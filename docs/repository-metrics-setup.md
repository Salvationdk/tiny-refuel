# Automatisk repository-statistik

Denne opsætning er kun til Salvationdks egne, selvstændigt udviklede projekter. Den installerer ikke telemetri i apps eller Home Assistant. Den læser alene GitHubs repository-statistik.

## Funktioner

- Hver dag kl. **04:17 UTC** tælles downloads for hvert GitHub Release-asset.
- Det samlede antal eksisterende release-asset-downloads gemmes som et dagligt snapshot.
- Med separat adgangstoken hentes GitHubs seneste 14 dages **sidevisninger** og **kloninger**, opdelt efter dato. Når samme dato senere returneres, **opdateres** den tidligere registrering i stedet for at blive lagt til igen.
- Diagrammer, data og dashboard gemmes på branch \`metrics-history\`, så appens kode og release-historik ikke får daglige statistik-commits.
- På offentlige projekter vises SVG-badges med historiske visninger og kloninger. De viser "afventer token", indtil der faktisk er data. Private projekter viser kun adgangskontrollerede GitHub-links.

## Besøgs- og kloningshistorik: den eneste manglende opsætning

GitHub kræver en **fine-grained personal access token** for trafiktællere.

1. På GitHub: **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. Vælg ejeren \`Salvationdk\` og **Only select repositories**. Vælg kun dette repository. Sæt en udløbsdato.
3. Under **Repository permissions** skal **Administration: Read-only** være aktiv. Vælg ikke write-adgang til Administration.
4. Gå til dette repository: **Settings → Secrets and variables → Actions → New repository secret**.
5. Opret secret med navnet præcist \`METRICS_TRAFFIC_TOKEN\` og værdien fra GitHubs nye token. Indsæt **aldrig** token i README, et issue eller chatten.
6. Åbn **Actions → Repository metrics history → Run workflow** for at starte den første komplette trafikmåling.

Der kan oprettes et separat token til hvert repository, så adgangsomfanget holdes mindst muligt. Hvis et token udløber, oprettes et nyt, og repository-secret opdateres.

**Uden token:** Release-downloads fortsætter; views/clones bliver ikke rapporteret som nul. Tidligere gemt historie bevares ved fejl. Ved første opsætning kan GitHub højst levere trafik fra sit aktuelle **14-dages** vindue.

## Præcise fortolkninger

- **Besøg:** sidevisninger på GitHub, ikke app-brugere. En bruger kan tælle flere gange. Summen af dagligt unikke besøgende er ikke et antal unikke personer i hele perioden.
- **Kloninger:** Git-kloninger, ikke HACS-installationer og ikke Code → Download ZIP.
- **Downloads:** historiske snapshots af GitHubs downloadtæller for eksisterende release-assets. De er ikke det samme som downloads i løbet af én dag. Et slettet asset kan reducere et fremtidigt samlet tal.
- **GitHub Actions-artefakter og HACS:** ikke dækket af GitHubs release-downloadtal.
- **Opsamling:** scheduler kan være forsinket eller undlade kørsler. Hvis der går mere end 14 dage uden succesfuld trafikmåling, kan der opstå huller, som ikke kan genskabes.

## Hvor findes data?

- Dashboard: [metrics-history/metrics/dashboard.md](../../blob/metrics-history/metrics/dashboard.md)
- Historiske data: [metrics-history/metrics/history.json](../../blob/metrics-history/metrics/history.json) (oprettes ved første Action-kørsel)
- Workflow: [repository-metrics.yml](../.github/workflows/repository-metrics.yml)

## Sikkerhed

Collector bruger kun Python-standardbiblioteket og GitHubs officielle REST API. Workflow kører kun efter push af de to collector-filer på main, efter en manuel start eller efter daglig tidsplan – **ikke** på pull requests. \`GITHUB_TOKEN\` har kun \`contents:write\` til at gemme historik. Den særskilte \`METRICS_TRAFFIC_TOKEN\` bruges kun til at læse trafik-API; workflow logger ikke værdien. Et privat repositories data holdes på det private repository og offentliggøres ikke gennem Shields.io eller tredjepart.
