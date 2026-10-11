"""Lightweight, cached extracts from providers' official benefit pages."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
import time

REFRESH_AFTER = 7 * 24 * 60 * 60
MAX_EXCERPT_WORDS = 20
EXTRACTOR_VERSION = 5

# One canonical public page per provider. Records are keyed to the card's brand
# keys so both the fuel and charging views can show the right source.
PROVIDER_PAGES = {
    "circle_k": ("Circle K", [
        "https://www.circlek.dk/extra",
        "https://www.circlek.dk/ubegraensetbilvask",
    ]),
    "ingo": ("Ingo", [
        "https://www.ingo.dk/ingokort/vores-kort/ingokort",
        "https://www.ingo.dk/gratisliter",
    ]),
    "f24": ("F24", [
        "https://www.q8.dk/kundeservice/bliv-q8-kunde/",
        "https://www.q8.dk/bilvask",
    ]),
    "q8": ("Q8", [
        "https://www.q8.dk/kundeservice/bliv-q8-kunde/",
        "https://www.q8.dk/bilvask",
    ]),
    "goon": ("Go'on", ["https://goon.nu/goon-kort/privat/loyalitet/"]),
    "shell": ("Shell", [
        "https://www.shell.dk/private-customers.html",
        "https://www.shell.dk/at-station/carwash.html",
    ]),
    "uno_x": ("Uno-X", [
        "https://landbrug.unox.dk/privat/produkter/kortlink",
        "https://erhverv.unox.dk/privat",
    ]),
    "ok": ("OK", [
        "https://www.ok.dk/privat/hjaelp/bilen/ok-kort/hvad-er-fordelene-ved-at-have-et-ok-kort",
        "https://www.ok.dk/privat/produkter/appen/vask",
        "https://www.ok.dk/privat/produkter/opladning/kampagner/laderabat",
    ]),
    "oil": ("OIL", ["https://www.oil-tankstationer.dk/betalingsformer/oil-loyalitetsaftale/"]),
    "clever": ("Clever", ["https://clever.dk/ladeloesninger/opladning-med-abonnement/"]),
    "eon": ("E.ON", ["https://www.eon.dk/privat/kundesupport/kontakt-opladning.html"]),
    "ionity": ("IONITY", ["https://www.ionity.eu/subscriptions"]),
}

_INTERESTING = re.compile(
    r"rabat|øre|kr\s*/\s*kwh|kwh|abonnement|app|kort|bonus|loyal|fordel|gratis|pris|betaling|charge",
    re.I,
)
_SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg", "iframe", "form", "blockquote"}
_BLOCK_TAGS = {"p", "li", "h2", "h3", "h4"}
_REVIEW_MARKER = re.compile(
    r"review|rating|testimonial|feedback|comment|customer[-_ ]?(?:review|comment|story|voice|quote)|"
    r"social[-_ ]?proof|quote[-_ ]?(?:card|block|slider)|review[-_ ]?(?:card|widget|slider|list)|"
    r"kunde[-_ ]?(?:anmeldelse|anmeldelser|kommentar|kommentarer|udtalelse|oplevelse|historie|citat)|"
    r"anmeldelse|anmeldelser|kommentar|kommentarer|kundeudtalelse|kundeoplevelse|udtalelse|udtalelser|"
    r"bedømmelse|trustpilot|ugc|user[-_ ]?content",
    re.I,
)
_CONTAINER_TAGS = {"div", "section", "article", "ul", "ol", "blockquote", "aside"}

# Customer quotes can be embedded in ordinary page paragraphs without useful class names.
_CUSTOMER_VOICE = re.compile(
    r"\b(?:jeg|mig|min|mit|mine|vi|os|vores|(?-i:\bI\b)|me|my|we|us|our)\b.{0,90}\b(?:synes|mener|oplevede|fik|har\s+brugt|"
    r"elsker|anbefaler|er\s+tilfreds|er\s+utilfreds|think|love|recommend|got|received|used|"
    r"tried|found|have\s+used|enjoyed|feel)\b|"
    r"\b(?:synes|mener|oplevede|anbefaler|fortæller|skriver|siger|says|writes|thinks|recommends|"
    r"loves|claims|reports)\b.{0,55}\b(?:kunde|bruger|customer|user|reviewer|member|formand)\b|"
    r"\b(?:kunde|bruger|customer|user|reviewer|member|formand)\b.{0,55}\b(?:synes|mener|oplevede|"
    r"anbefaler|fortæller|skriver|siger|says|writes|thinks|recommends|loves|claims|reports)\b|"
    r"\b(?:trustpilot|kundeanmeldelse|kundeudtalelse|testimonial|review|stjerner)\b",
    re.I,
)
_QUOTED_TESTIMONIAL = re.compile(r"[“„«][^”»]{12,}[”»]|“|”|„|«|»")
_QUESTION_BLOCK = re.compile(r"^\s*(?:hvad|hvordan|hvorfor|hvornår|hvem|hvor|kan\s+jeg|må\s+jeg|skal\s+jeg|how|what|why|when|where|can\s+i|do\s+i)\b|[?？]", re.I)


class _BenefitText(HTMLParser):
    """Collect provider copy while excluding marked customer-review sections."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.skip_depth = 0
        self.block = None
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        marker_values = [attrs.get(key, "") for key in ("class", "id", "aria-label", "data-testid", "itemprop", "role")]
        marker_values.extend(value for key, value in attrs.items() if key.startswith("data-"))
        marker_text = " ".join(str(value) for value in marker_values)
        skip = tag in _SKIP_TAGS or bool(_REVIEW_MARKER.search(marker_text))
        self.stack.append((tag, skip))
        if skip:
            self.skip_depth += 1
        if self.skip_depth == 0 and tag in _BLOCK_TAGS and self.block is None:
            self.block = [tag, []]

    def handle_startendtag(self, tag, attrs):
        # Treat void/self-closing elements without leaving a stack entry behind.
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.block is not None and tag == self.block[0]:
            value = re.sub(r"\s+", " ", " ".join(self.block[1])).strip()
            if len(value) >= 35 and _INTERESTING.search(value):
                self.blocks.append(value)
            self.block = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                removed = self.stack[index:]
                self.skip_depth -= sum(1 for _, skipped in removed if skipped)
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.skip_depth == 0 and self.block is not None:
            self.block[1].append(data)


def extract_excerpt(page):
    parser = _BenefitText()
    parser.feed(page)
    parser.close()
    # Old cached extracts are invalidated when the filter changes. Also reject
    # unlabelled testimonial copy that happens to mention an app or discount.
    eligible = [text for text in parser.blocks if not _CUSTOMER_VOICE.search(text) and not _QUOTED_TESTIMONIAL.search(text) and not _QUESTION_BLOCK.search(text)]
    if not eligible:
        return None
    # Prefer a concise block with concrete terms and avoid concatenating site text.
    ranked = sorted(eligible, key=lambda text: (
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
        key, (provider, urls) = item
        cached = previous.get(key)
        if not isinstance(cached, dict) or cached.get("extractor_version") != EXTRACTOR_VERSION:
            # Old extracts were not checked for review widgets; never keep showing them.
            cached = None
        if isinstance(cached, dict):
            try:
                if now - int(cached.get("fetched_ts", 0)) < REFRESH_AFTER:
                    return key, dict(cached), None
            except (TypeError, ValueError):
                pass
        excerpts, errors, empty_pages = [], [], 0
        for url in urls:
            try:
                page = fetch_text(url, timeout=12)
                excerpt = extract_excerpt(page)
                if excerpt and excerpt not in excerpts:
                    excerpts.append(excerpt)
                elif not excerpt:
                    empty_pages += 1
            except Exception as exc:
                errors.append(str(exc)[:100])
        if excerpts:
            summary = " · ".join(excerpts)
            words = summary.split()
            if len(words) > 48:
                summary = " ".join(words[:48]).rstrip(".,;:") + "…"
            return key, {"provider": provider, "summary": summary,
                         "source_url": urls[0], "source_urls": urls,
                         "fetched_at": fetched_at, "fetched_ts": now,
                         "extractor_version": EXTRACTOR_VERSION, "status": "ok"}, (
                             "; ".join(errors)[:140] if errors else None)
        if isinstance(cached, dict) and cached.get("summary"):
            stale = dict(cached)
            stale["status"] = "stale"
            error = "; ".join(errors)[:140] if errors else "no relevant provider benefit text found"
            return key, stale, error
        error = "; ".join(errors)[:140] if errors else None
        status = "unavailable" if errors else "source_only"
        return key, {"provider": provider, "summary": None, "source_url": urls[0],
                     "source_urls": urls, "fetched_at": fetched_at if not errors else None,
                     "fetched_ts": now if not errors else 0,
                     "extractor_version": EXTRACTOR_VERSION, "status": status}, error

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
