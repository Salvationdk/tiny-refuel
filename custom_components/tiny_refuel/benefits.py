"""Lightweight, cached extracts from providers' official benefit pages."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
import time

REFRESH_AFTER = 7 * 24 * 60 * 60
MAX_EXCERPT_WORDS = 20

# One canonical public page per provider. Records are keyed to the card's brand
# keys so both the fuel and charging views can show the right source.
PROVIDER_PAGES = {
    "circle_k": ("Circle K", "https://www.circlek.dk/extra/faq"),
    "ingo": ("Ingo", "https://www.ingo.dk/app"),
    "f24": ("F24", "https://www.f24.dk/"),
    "q8": ("Q8", "https://www.q8.dk/kundeservice/bliv-q8-kunde/"),
    "goon": ("Go'on", "https://goon.nu/goon-kort/privat/loyalitet/"),
    "shell": ("Shell", "https://www.shell.dk/private-customers.html"),
    "uno_x": ("Uno-X", "https://www.unox.dk/el/"),
    "ok": ("OK", "https://www.ok.dk/privat/produkter/opladning/kampagner/laderabat"),
    "oil": ("OIL", "https://www.oil-tankstationer.dk/betalingsformer/oil-loyalitetsaftale/"),
    "clever": ("Clever", "https://clever.dk/ladeloesninger/clever-go/"),
    "eon": ("E.ON", "https://www.eon.dk/privat/kundesupport/kontakt-opladning.html"),
    "tesla": ("Tesla", "https://www.tesla.com/da_dk/support/charging/supercharging"),
    "ionity": ("IONITY", "https://www.ionity.eu/subscriptions"),
}

_INTERESTING = re.compile(
    r"rabat|øre|kr\s*/\s*kwh|kwh|abonnement|app|kort|bonus|loyal|fordel|gratis|pris|betaling|charge",
    re.I,
)
_SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg"}
_BLOCK_TAGS = {"p", "li", "h2", "h3", "h4"}


class _BenefitText(HTMLParser):
    """Collect visible, meaningful text blocks and ignore page chrome."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.block = None
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self.skip_depth += 1
        if self.skip_depth == 0 and tag in _BLOCK_TAGS and self.block is None:
            self.block = [tag, []]

    def handle_endtag(self, tag):
        if self.skip_depth and tag in _SKIP_TAGS:
            self.skip_depth -= 1
        if self.block is not None and tag == self.block[0]:
            value = re.sub(r"\s+", " ", " ".join(self.block[1])).strip()
            if len(value) >= 35 and _INTERESTING.search(value):
                self.blocks.append(value)
            self.block = None

    def handle_data(self, data):
        if self.skip_depth == 0 and self.block is not None:
            self.block[1].append(data)


def extract_excerpt(page):
    parser = _BenefitText()
    parser.feed(page)
    parser.close()
    if not parser.blocks:
        return None
    # Prefer a concise block with concrete terms and avoid concatenating site text.
    ranked = sorted(parser.blocks, key=lambda text: (
        -len(re.findall(r"rabat|øre|abonnement|kwh|gratis|kort", text, re.I)), len(text)))
    words = ranked[0].split()
    if len(words) > MAX_EXCERPT_WORDS:
        words = words[:MAX_EXCERPT_WORDS]
        words[-1] = words[-1].rstrip(".,;:") + "…"
    return " ".join(words)


def update(fetch_text, load_json, save_json, cache_path, progress_callback=None, now=None, fallback=None):
    """Refresh provider excerpts weekly; keep the last good value on source errors."""
    now = int(time.time()) if now is None else int(now)
    fetched_at = datetime.fromtimestamp(now, timezone.utc).isoformat()
    previous = load_json(cache_path, {})
    if not isinstance(previous, dict):
        previous = {}
    if isinstance(fallback, dict):
        previous = {**fallback, **previous}
    result, failures = {}, []

    def fetch_one(item):
        key, (provider, url) = item
        cached = previous.get(key)
        if isinstance(cached, dict):
            try:
                if now - int(cached.get("fetched_ts", 0)) < REFRESH_AFTER:
                    return key, dict(cached), None
            except (TypeError, ValueError):
                pass
        try:
            page = fetch_text(url, timeout=12)
            excerpt = extract_excerpt(page)
            if excerpt:
                return key, {"provider": provider, "summary": excerpt,
                             "source_url": url, "fetched_at": fetched_at,
                             "fetched_ts": now, "status": "ok"}, None
            if isinstance(cached, dict) and cached.get("summary"):
                stale = dict(cached)
                stale["status"] = "stale"
                return key, stale, "no relevant benefit text found"
            return key, {"provider": provider, "summary": None, "source_url": url,
                         "fetched_at": fetched_at, "fetched_ts": now,
                         "status": "source_only"}, None
        except Exception as exc:  # Each provider is independent; keep the rest fresh.
            if isinstance(cached, dict):
                stale = dict(cached)
                stale["status"] = "stale"
                return key, stale, str(exc)[:140]
            return key, {"provider": provider, "summary": None, "source_url": url,
                         "fetched_at": None, "fetched_ts": 0, "status": "unavailable"}, str(exc)[:140]

    if progress_callback:
        progress_callback({"phase": "fordele", "provider": "officielle udbydersider",
                           "station": "Fordele og vilkår", "current": None, "total": None})
    items = list(PROVIDER_PAGES.items())
    with ThreadPoolExecutor(max_workers=5) as executor:
        for key, record, error in executor.map(fetch_one, items):
            result[key] = record
            if error:
                failures.append({"provider": record["provider"], "error": error})
    save_json(cache_path, result)
    return result, failures
