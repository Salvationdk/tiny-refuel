"""EV tariff and charging-location fetches, kept separate from fuel prices."""


def collect(api, previous_ev, errors, progress_callback=None):
    """Fetch EV providers through the scraper's shared parser/helper namespace."""
    report = api._report_progress
    report(progress_callback, "el", "Q8")
    q8_tariffs = api.fetch_q8_el(errors)
    report(progress_callback, "el", "Circle K")
    circlek_tariffs = api.fetch_circlek_ev_prices(errors)
    report(progress_callback, "el", "E.ON")
    eon_tariffs = api.fetch_eon_ev_tariffs(errors)
    report(progress_callback, "el", "IONITY")
    ionity_tariffs = api.fetch_ionity_ev_tariffs(errors)

    report(progress_callback, "el", "Clever")
    clever, clever_status = api.fetch_public_ev_locations(
        api.CLEVER_LOCATIONS_URL, api.normalize_clever_locations, "clever.dk", previous_ev, errors)
    report(progress_callback, "el", "E.ON")
    eon, eon_status = api.fetch_public_ev_locations(
        api.EON_LOCATIONS_URL, api.normalize_eon_locations, "edri.com", previous_ev, errors)
    report(progress_callback, "el", "Tesla")
    tesla, tesla_status = api.fetch_public_ev_locations(
        api.TESLA_LOCATIONS_URL, api.normalize_tesla_locations, "tesla.com", previous_ev, errors,
        json_feed=False)
    api.enrich_tesla_prices(tesla, tesla_status, previous_ev, errors, progress_callback)
    report(progress_callback, "el", "IONITY")
    ionity, ionity_status = api.fetch_public_ev_locations(
        api.IONITY_LOCATIONS_URL, api.normalize_ionity_locations, "ionity.eu", previous_ev, errors)
    report(progress_callback, "el", "OK")
    ok, ok_status = api.fetch_public_ev_locations(
        api.OK_LOCATIONS_API, api.normalize_ok_locations, "geo-emobility.okcloud.dk", previous_ev, errors,
        payload_loader=api.load_ok_locations)
    report(progress_callback, "el", "OIL")
    oil, oil_status = api.fetch_public_ev_locations(
        api.OIL_STATIONS_PAGE, api.normalize_oil_charging, "oil-charging", previous_ev, errors,
        payload_loader=api.load_oil_charging)
    report(progress_callback, "el", "Shell Recharge")
    shell, shell_status = api.fetch_public_ev_locations(
        api.SHELL_CHARGING_API, api.normalize_shell_charging, "shell-charging", previous_ev, errors,
        payload_loader=api.load_shell_charging)
    report(progress_callback, "el", "Circle K")
    circlek, circlek_status = api.fetch_public_ev_locations(
        api.CK_CHARGING_API, api.normalize_circlek_charging, "circlek-charging", previous_ev, errors,
        payload_loader=lambda: api.load_circlek_charging(progress_callback))

    return {
        "tariffs": q8_tariffs + circlek_tariffs + eon_tariffs + ionity_tariffs,
        "q8_tariffs": q8_tariffs,
        "circlek_tariffs": circlek_tariffs,
        "eon_tariffs": eon_tariffs,
        "ionity_tariffs": ionity_tariffs,
        "locations": clever + eon + tesla + ionity + ok + oil + shell + circlek,
        "tesla": tesla,
        "statuses": {"clever": clever_status, "eon": eon_status, "tesla": tesla_status,
                     "ionity": ionity_status, "ok": ok_status, "oil": oil_status,
                     "shell": shell_status, "circle_k": circlek_status},
    }
