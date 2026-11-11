# Repository statistics and badges

This repository uses the same README badge pattern as other Salvationdk repositories.

## Public badges

- **Release downloads:** count downloads of uploaded release assets, not source code ZIP archives, GitHub Actions artifacts, or installations from HACS.
- **Stars / forks:** GitHub counters that update automatically via Shields.io.
- **Open issues / open pull requests:** live issue and pull-request totals.
- **Last commit:** activity indicator, not a unique contributor counter.
- A version badge is optional and should be added only where actual GitHub Releases exist.

The README block is delimited by `BEGIN: Salvationdk repository metrics` and `END: Salvationdk repository metrics` to make future updates straightforward. Replace the repository name in the links when copying it.

## Traffic analytics (not part of the public badges)

GitHub's [Traffic graph](https://github.com/Salvationdk/tiny-refuel/graphs/traffic) displays a rolling **14 days** of page views and full clones. A history beyond 14 days requires collecting and storing daily snapshots before the data expires. The repository traffic REST endpoints require a credential with **Administration: read** permission on the selected repository; the normal Actions `GITHUB_TOKEN` should not be assumed to have this privilege.

If traffic collection is enabled later, use a fine-grained, expiring token scoped only to the intended repositories. Store it as a repository secret, never in README, source, workflow logs or generated public data. Do not expose private-repository metrics in a public dashboard without a deliberate privacy decision. Deduplicate daily snapshots by UTC date because consecutive 14-day windows overlap.

## Privacy

Public-repository badges use third-party Shields.io. Private repositories should use only authenticated GitHub Insights links until a private badge solution is explicitly configured.

## Source

- [GitHub repository traffic documentation](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository)
- [GitHub traffic REST API](https://docs.github.com/en/rest/metrics/traffic)
- [Shields.io downloads badge](https://shields.io/badges/git-hub-downloads-all-releases)

## Copy-and-paste template for a new public repository

Replace `OWNER/REPO` with the repository's exact GitHub path. The counters update without running any GitHub Actions:

```markdown
<!-- BEGIN: Salvationdk repository metrics -->
[![Release downloads](https://img.shields.io/github/downloads/OWNER/REPO/total?label=Release%20downloads&style=flat-square)](https://github.com/OWNER/REPO/releases)
[![Stars](https://img.shields.io/github/stars/OWNER/REPO?style=flat-square)](https://github.com/OWNER/REPO/stargazers)
[![Forks](https://img.shields.io/github/forks/OWNER/REPO?style=flat-square)](https://github.com/OWNER/REPO/forks)
[![Issues](https://img.shields.io/github/issues/OWNER/REPO?style=flat-square)](https://github.com/OWNER/REPO/issues)
[![Pull requests](https://img.shields.io/github/issues-pr/OWNER/REPO?style=flat-square)](https://github.com/OWNER/REPO/pulls)
[![Last commit](https://img.shields.io/github/last-commit/OWNER/REPO?style=flat-square)](https://github.com/OWNER/REPO/commits)
<!-- END: Salvationdk repository metrics -->
```

For **private** repositories do not embed third-party badge images. Instead link to their GitHub-native Issues, Pull requests, Actions, Releases and Insights → Traffic pages, which require the reader's GitHub access.

## Before adding a historical traffic collector

- Decide where the collected information may be stored and who may see it.
- Create a fine-grained, expiry-limited access token with `Administration: read` on only the intended repositories.
- Store the token as a GitHub Actions secret, never as a committed file. Installing the collector is a separate, explicit action after that secret is available.
- Collect the per-day UTC breakdown and merge by date; never add the 14-day rolling totals to a historical grand total as that double-counts visits and clones.
- If a token is not configured, the traffic collector must report "not configured", not a misleading zero.
