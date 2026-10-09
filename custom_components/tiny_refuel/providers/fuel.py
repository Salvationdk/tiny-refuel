"""Petrol and diesel provider fetches, kept separate from EV locations."""


def collect(api, errors, progress_callback=None):
    """Fetch fuel records through the scraper's shared parser/helper namespace."""
    report = api._report_progress
    report(progress_callback, "benzin/diesel", "Circle K og Ingo")
    ck_ingo, ck_ok = api.fetch_ck_ingo(errors)
    report(progress_callback, "benzin/diesel", "F24 og Q8")
    f24q8, fq_ok = api.fetch_f24q8(errors)
    report(progress_callback, "benzin/diesel", "Go'on")
    goon, go_ok = api.fetch_goon(errors)
    report(progress_callback, "benzin/diesel/el", "Uno-X")
    (unox, unox_chargers), ux_ok = api.fetch_unox(errors)
    report(progress_callback, "benzin/diesel", "Shell")
    shell, sh_ok = api.fetch_shell(errors)
    report(progress_callback, "benzin/diesel/el", "OK")
    ok_list, ok_ev, ok_list_ok = api.fetch_ok(errors)
    report(progress_callback, "benzin/diesel", "OK")
    ok_rows, ok_ok = api.fetch_ok_fuel(errors)
    if not ok_rows:
        ok_rows = ok_list
    report(progress_callback, "benzin/diesel", "OIL")
    oil_rows, oil_ok = api.fetch_oil_fuel(errors)
    oil_list_ok = True
    if not oil_rows:
        oil_rows, oil_list_ok = api.fetch_oil(errors)
    return {
        "stations": ck_ingo + f24q8 + goon + unox + shell + ok_rows + oil_rows,
        "source_ok": {
            "api.circlek.com": ck_ok, "f24.dk": fq_ok,
            "goon.nu": go_ok, "unoxmobility.dk": ux_ok,
            "shellservice.dk": sh_ok, "ok.dk": ok_list_ok,
            "mobility-prices.ok.dk": ok_ok, "oil-fuel-api": oil_ok,
            "oil-tankstationer.dk": oil_list_ok,
        },
        "unox_chargers": unox_chargers,
        "ok_tariffs": ok_ev,
    }
