# Repository-statistik – tiny-refuel

**Status: Klar til første automatiske indsamling.**

Release-downloads registreres ved den første kørsel af [Repository metrics history](https://github.com/Salvationdk/tiny-refuel/actions/workflows/repository-metrics.yml).

Besøgs- og kloningstal kræver et *fine-grained personal access token* med **Administration: read**, gemt som repository-secret **METRICS_TRAFFIC_TOKEN**. Uden token vises ingen falske nuller. Historiske trafikdata kan ikke rekonstrueres længere tilbage end GitHubs aktuelle 14-dages vindue.

Dette er et internt projekt-dashboard: Data lagres på den særskilte `metrics-history`-branch og ændrer ikke programmets kode eller udgivelser.
