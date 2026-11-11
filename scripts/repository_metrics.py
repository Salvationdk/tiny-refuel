#!/usr/bin/env python3
"""Daily GitHub release and traffic history, using only the Python standard library."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UTC = dt.timezone.utc


def get_api(path, token):
    req = Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Salvationdk-repository-metrics/1.0",
    })
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def get_releases(repo, token):
    releases = []
    for page in range(1, 101):
        batch = get_api(f"/repos/{repo}/releases?per_page=100&page={page}", token)
        if not isinstance(batch, list):
            raise ValueError("Unexpected release API response")
        for rel in batch:
            if rel.get("draft"):
                continue
            assets = rel.get("assets") or []
            releases.append({
                "tag": str(rel.get("tag_name") or "untagged"),
                "published_at": rel.get("published_at"),
                "assets": len(assets),
                "downloads": sum(int(asset.get("download_count") or 0) for asset in assets),
                "prerelease": bool(rel.get("prerelease")),
            })
        if len(batch) < 100:
            break
    return releases


def update_traffic(state, key, repo, token, today):
    try:
        payload = get_api(f"/repos/{repo}/traffic/{key}?per=day", token)
        values = payload.get(key)
        if not isinstance(values, list):
            raise ValueError("Unexpected traffic API response")
        history = state.setdefault("traffic", {}).setdefault(key, {})
        for item in values:
            day = item["timestamp"][:10]
            if day < today:  # Do not persist partial UTC days
                history[day] = {
                    "count": int(item.get("count") or 0),
                    "daily_uniques": int(item.get("uniques") or 0),
                }
        return "ok"
    except (HTTPError, URLError, ValueError, KeyError, TimeoutError) as err:
        code = getattr(err, "code", None)
        return "API error" + (f" ({code})" if code else "")


def svg_badge(label, value, color="#277d86"):
    label, value = str(label), str(value)
    w1, w2 = max(86, len(label) * 7 + 18), max(64, len(value) * 7 + 18)
    w = w1 + w2
    esc = html.escape
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="22" '
        f'viewBox="0 0 {w} 22" role="img" aria-label="{esc(label + ": " + value, quote=True)}">'
        f'<rect width="{w1}" height="22" fill="#394352" rx="3"/>'
        f'<rect x="{w1}" width="{w2}" height="22" fill="{color}" rx="3"/>'
        f'<text x="{w1/2:.0f}" y="15" text-anchor="middle" font-family="Arial" '
        f'font-size="11" fill="white">{esc(label)}</text>'
        f'<text x="{w1+w2/2:.0f}" y="15" text-anchor="middle" font-family="Arial" '
        f'font-size="11" fill="white">{esc(value)}</text></svg>\n'
    )


def svg_chart(rows, title, color):
    w, h = 780, 180
    maximum = max((n for _, n in rows), default=0) or 1
    xy = [(48 + i * 714 / max(1, len(rows)-1), 145 - n * 119 / maximum)
          for i, (_, n) in enumerate(rows)]
    coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    dates = (rows[0][0] + " – " + rows[-1][0]) if rows else "Ingen registrerede data"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{html.escape(title, quote=True)}">'
        f'<rect width="{w}" height="{h}" rx="8" fill="#151b26"/>'
        f'<text x="16" y="18" fill="white" font-family="Arial" font-size="13">'
        f'{html.escape(title)}</text>'
        f'<path d="M48,26 V145 H762" stroke="#788391" fill="none"/>'
        f'<text x="5" y="33" fill="white" font-size="10">{maximum}</text>'
        + (f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3"/>' if rows else '')
        + f'<text x="390" y="169" fill="#cdd5e1" text-anchor="middle" '
          f'font-family="Arial" font-size="11">{html.escape(dates)}</text></svg>\n'
    )


def write_metrics(out, repo, state):
    out.mkdir(parents=True, exist_ok=True)
    (out / "badges").mkdir(exist_ok=True)
    (out / "charts").mkdir(exist_ok=True)
    (out / "history.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    traffic = state.get("traffic", {})
    summaries = {}
    for key, alias, color in (("views", "visits", "#38acc5"), ("clones", "clones", "#a685e4")):
        series = traffic.get(key, {})
        total = sum(x.get("count", 0) for x in series.values())
        summaries[key] = (total, min(series) if series else "ikke registreret",
                          max(series) if series else "ikke registreret", len(series))
        value = str(total) if series else "afventer token"
        (out / "badges" / (alias + ".svg")).write_text(
            svg_badge("Views" if key == "views" else "Clones", value,
                      "#277d86" if series else "#91737b"), encoding="utf-8"
        )
        today = dt.datetime.now(UTC).date()
        dates = [(today - dt.timedelta(days=i)).isoformat() for i in range(30, 0, -1)]
        points = [(d, series[d]["count"]) for d in dates if d in series]
        (out / "charts" / (key + ".svg")).write_text(
            svg_chart(points, "Daglige " + key, color), encoding="utf-8"
        )
    releases = state.get("releases", [])
    count = sum(x["downloads"] for x in releases)
    (out / "badges" / "downloads.svg").write_text(
        svg_badge("Release downloads",
                  str(count) if state.get("release_status") == "ok" else "API fejl"),
        encoding="utf-8",
    )
    snaps = state.get("release_snapshots", {})
    points = [(d, snaps[d]) for d in sorted(snaps)[-30:]]
    (out / "charts" / "downloads.svg").write_text(
        svg_chart(points, "Release-filer: samlede optalte downloads", "#67b78d"),
        encoding="utf-8",
    )
    lines = [
        "# Repository-statistik: " + repo, "",
        "Senest kørt (UTC): **" + state.get("updated_at", "ukendt") + "**", "",
        "| Måling | Antal | Dækning |", "|---|---:|---|",
        f"| Besøg / sidevisninger | **{summaries['views'][0]}** | "
        f"{summaries['views'][1]} – {summaries['views'][2]} ({summaries['views'][3]} registrerede dage) |",
        f"| Kloninger | **{summaries['clones'][0]}** | "
        f"{summaries['clones'][1]} – {summaries['clones'][2]} ({summaries['clones'][3]} registrerede dage) |",
        f"| Downloadede eksisterende release-assets | **{count}** | "
        f"{state.get('release_status', 'ukendt')} |",
        f"| Trafik-API | **{state.get('traffic_status', 'ukendt')}** | "
        "Kræver METRICS_TRAFFIC_TOKEN |", "",
        "**Vigtigt:** GitHub leverer trafikdata for de seneste 14 dage. "
        "Historikken starter først, når et token med Administration: read er konfigureret. "
        "Ved fejl beholdes tidligere data. Summer af dagligt unikke besøgende må ikke "
        "opfattes som unikke personer på tværs af hele perioden.", "",
        "## Diagrammer", "",
        "![Daglige sidevisninger](charts/views.svg)", "",
        "![Daglige kloninger](charts/clones.svg)", "",
        "![Release-downloads](charts/downloads.svg)", "",
        "## Downloads pr. release", "",
        "| Release | Filer | Downloads |", "|---|---:|---:|",
    ]
    for rel in releases:
        tag = rel["tag"].replace("|", "\\|")
        lines.append(f"| {tag} | {rel['assets']} | {rel['downloads']} |")
    if not releases:
        lines.append("| Ingen registrerede releases | 0 | 0 |")
    lines += ["", "Release-downloads tæller **kun filer knyttet til GitHub Releases** – "
              "ikke Code ZIP, HACS, Actions-artefakter eller installationer. "
              "Slettede assets kan ændre totalen. Daglige tal for downloads er "
              "snapshots af totalen, ikke nye downloads den dag.", "",
              "[Tilbage til repository](https://github.com/" + repo + ")", ""]
    (out / "dashboard.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: repository_metrics.py OUTPUT_DIR")
    out = Path(sys.argv[1])
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    traffic_token = os.environ.get("METRICS_TRAFFIC_TOKEN", "").strip()
    now = dt.datetime.now(UTC)
    today = now.date().isoformat()
    old = out / "history.json"
    if old.is_file():
        state = json.loads(old.read_text(encoding="utf-8"))
        if state.get("repository") != repo:
            sys.exit("History belongs to a different repository")
    else:
        state = {"schema_version": 1, "repository": repo, "traffic": {"views": {}, "clones": {}},
                 "release_snapshots": {}}
    try:
        state["releases"] = get_releases(repo, token)
        total = sum(x["downloads"] for x in state["releases"])
        state.setdefault("release_snapshots", {})[today] = total
        state["release_status"] = "ok"
    except (HTTPError, URLError, ValueError, KeyError, TimeoutError) as error:
        code = getattr(error, "code", None)
        state["release_status"] = "API error" + (f" ({code})" if code else "")
        state.setdefault("releases", [])
    if traffic_token:
        statuses = [update_traffic(state, kind, repo, traffic_token, today)
                    for kind in ("views", "clones")]
        state["traffic_status"] = "ok" if statuses == ["ok", "ok"] else ", ".join(statuses)
    else:
        state["traffic_status"] = "ikke konfigureret"
    state["updated_at"] = now.strftime("%Y-%m-%d %H:%M UTC")
    write_metrics(out, repo, state)
    print("Metrics collected for " + repo + ": traffic=" + state["traffic_status"]
          + ", releases=" + state["release_status"])


if __name__ == "__main__":
    main()
