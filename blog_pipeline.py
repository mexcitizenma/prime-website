"""
Shared post-processing pipeline for Prime Paint blog posts.

Everything the model is NOT trusted with lives here: external-link whitelisting,
internal service links, related-post links, CTA blocks, FAQ extraction and the
hero photo. generate_post.py calls this after the model returns prose;
retrofit_posts.py calls the same functions over already-published posts so old
and new posts come out identical.
"""

import html as htmllib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

SITE = "https://primeprowork.com"

EN_DIR = Path("blog-src/en")
ES_DIR = Path("blog-src/es")
PUBLISHED_FILE = Path("published.json")

STOCK_DIR = Path("images/stock")
WEB_DIR = Path("images/stock/web")
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic"}
PHOTO_W, PHOTO_H = 1100, 619  # 16:9, matches .blog-post__hero

# --------------------------------------------------------------- externals ---
# Domain ROOTS only. Deep URLs rot; the model is never allowed to invent one.
ALLOWED_SOURCES = [
    "https://www.epa.gov/",
    "https://www.cdc.gov/",
    "https://ag.umass.edu/",  # UMass Extension home
    "https://www.sherwin-williams.com/",
    "https://www.benjaminmoore.com/",
    "https://www.nahb.org/",
    "https://www.energy.gov/",
]
ALLOWED_HOSTS = {
    "epa.gov",
    "cdc.gov",
    "umass.edu",
    "sherwin-williams.com",
    "benjaminmoore.com",
    "nahb.org",
    "energy.gov",
}
MAX_EXTERNAL_LINKS = 2

# ---------------------------------------------------------- internal links ---
# topics.json category -> anchor id on services.html (verified to exist on both
# services.html and es/services.html). None = link the page with no anchor.
SERVICE_ANCHORS = {
    "interior-painting": "interior-painting",
    "exterior-painting": "exterior-painting",
    "cabinet-painting": "cabinet-painting",
    "epoxy-floors": "epoxy-floors",
    "laminate-flooring": "laminate-flooring",
    "pressure-washing": "pressure-washing",
    "siding-cleaning": "siding-cleaning",
    "fence": "fence-painting",
    "handyman": "handyman",
    "general": None,
}

SERVICE_LINK_TEXT = {
    "interior-painting": ("our interior painting service", "nuestro servicio de pintura interior"),
    "exterior-painting": ("our exterior painting service", "nuestro servicio de pintura exterior"),
    "cabinet-painting": ("our cabinet painting service", "nuestro servicio de pintura de gabinetes"),
    "epoxy-floors": ("our epoxy floor coating service", "nuestro servicio de pisos epóxicos"),
    "laminate-flooring": ("our laminate flooring service", "nuestro servicio de pisos laminados"),
    "pressure-washing": ("our pressure washing service", "nuestro servicio de lavado a presión"),
    "siding-cleaning": ("our siding cleaning service", "nuestro servicio de limpieza de siding"),
    "fence": ("our fence painting and staining service", "nuestro servicio de pintura de cercas"),
    "handyman": ("our handyman services", "nuestros servicios de handyman"),
    "general": ("the services we offer", "los servicios que ofrecemos"),
}

CATEGORY_LABELS = {
    "interior-painting": ("Interior Painting", "Pintura Interior"),
    "exterior-painting": ("Exterior Painting", "Pintura Exterior"),
    "cabinet-painting": ("Cabinet Painting", "Pintura de Gabinetes"),
    "epoxy-floors": ("Epoxy Floors", "Pisos Epóxicos"),
    "laminate-flooring": ("Laminate Flooring", "Pisos Laminados"),
    "pressure-washing": ("Pressure Washing", "Lavado a Presión"),
    "siding-cleaning": ("Siding Cleaning", "Limpieza de Siding"),
    "fence": ("Fence Painting", "Pintura de Cercas"),
    "handyman": ("Handyman", "Handyman"),
    "general": ("Home Improvement", "Mejoras del Hogar"),
}

# topics.json category -> images/stock/<dir> to search, in order.
# "general" is always appended as the last resort.
CATEGORY_PHOTO_DIRS = {
    "interior-painting": ["interior-painting"],
    "exterior-painting": ["exterior-painting"],
    "cabinet-painting": ["cabinet-painting"],
    "epoxy-floors": ["garage-epoxy"],
    "laminate-flooring": ["flooring-laminate"],
    "pressure-washing": ["pressure-washing"],
    "siding-cleaning": ["siding"],
    "fence": ["deck-patio", "exterior-painting"],
    "handyman": ["handyman"],
    "general": [],
}

PHOTO_ALT = {
    "interior-painting": (
        "Freshly painted interior room in a Western Massachusetts home",
        "Habitación recién pintada en una casa del oeste de Massachusetts",
    ),
    "exterior-painting": (
        "Exterior of a repainted New England home",
        "Exterior de una casa de Nueva Inglaterra recién pintada",
    ),
    "cabinet-painting": (
        "Repainted kitchen cabinets in a Western Massachusetts kitchen",
        "Gabinetes de cocina repintados en una cocina del oeste de Massachusetts",
    ),
    "epoxy-floors": (
        "Finished epoxy garage floor coating",
        "Piso de garaje terminado con recubrimiento epóxico",
    ),
    "laminate-flooring": (
        "Newly installed laminate flooring in a living space",
        "Piso laminado recién instalado en una sala",
    ),
    "pressure-washing": (
        "Pressure washing an exterior surface",
        "Lavado a presión de una superficie exterior",
    ),
    "siding-cleaning": (
        "Clean house siding after washing",
        "Siding de casa limpio después del lavado",
    ),
    "fence": (
        "Painted wood fence in a Western Massachusetts yard",
        "Cerca de madera pintada en un patio del oeste de Massachusetts",
    ),
    "handyman": (
        "Handyman repair work in progress on a home",
        "Trabajo de reparación en progreso en una casa",
    ),
    "general": (
        "Home improvement work on a Western Massachusetts house",
        "Trabajo de mejoras en una casa del oeste de Massachusetts",
    ),
}

PHOTO_ALT_INLINE = {
    "interior-painting": (
        "Cut-in work along trim during an interior repaint",
        "Trabajo de bordes en molduras durante un repintado interior",
    ),
    "exterior-painting": (
        "Exterior siding mid-repaint on a New England home",
        "Siding exterior a medio pintar en una casa de Nueva Inglaterra",
    ),
    "cabinet-painting": (
        "Kitchen cabinet doors prepped for a new finish",
        "Puertas de gabinete preparadas para un nuevo acabado",
    ),
    "epoxy-floors": (
        "Epoxy coating being applied to a garage floor",
        "Aplicación de recubrimiento epóxico en un piso de garaje",
    ),
    "laminate-flooring": (
        "Laminate planks being fitted along a wall",
        "Tablones laminados colocándose a lo largo de una pared",
    ),
    "pressure-washing": (
        "Dirt lifting off a surface under a pressure washer",
        "Suciedad desprendiéndose de una superficie con lavadora a presión",
    ),
    "siding-cleaning": (
        "Siding part-way through a wash, clean and dirty side by side",
        "Siding a medio lavar, lado limpio y sucio uno junto al otro",
    ),
    "fence": (
        "Fence boards being stained in a back yard",
        "Tablas de cerca siendo teñidas en un patio trasero",
    ),
    "handyman": (
        "Close-up of a home repair being carried out",
        "Primer plano de una reparación del hogar en curso",
    ),
    "general": (
        "Home maintenance work underway on a New England property",
        "Trabajo de mantenimiento en una propiedad de Nueva Inglaterra",
    ),
}

# Citation markers. The model writes [[SOURCE:epa]] and never a URL or an <a>
# tag -- same rule as the service link and the CTA. Besides guaranteeing the URL
# is whitelisted, this keeps double quotes out of the JSON string the model
# returns: an href attribute inside `detail` breaks the response every time.
SOURCE_LINKS = {
    "epa": ("https://www.epa.gov/", "the EPA", "la EPA"),
    "cdc": ("https://www.cdc.gov/", "the CDC", "los CDC"),
    "umass": ("https://ag.umass.edu/", "UMass Extension", "UMass Extension"),
    "sherwin-williams": ("https://www.sherwin-williams.com/",
                         "Sherwin-Williams", "Sherwin-Williams"),
    "benjamin-moore": ("https://www.benjaminmoore.com/",
                       "Benjamin Moore", "Benjamin Moore"),
    "nahb": ("https://www.nahb.org/",
             "the National Association of Home Builders",
             "la Asociación Nacional de Constructores de Viviendas"),
    "energy": ("https://www.energy.gov/",
               "the U.S. Department of Energy",
               "el Departamento de Energía de EE. UU."),
}

SOURCE_MARKER_RE = re.compile(r"\[\[SOURCE:([a-z-]+)\]\]", re.I)

MARKER_SERVICE = "[[SERVICE_LINK]]"
MARKER_CTA = "[[CTA]]"

WORDS_MIN, WORDS_MAX = 800, 1200
WORDS_HARD_MIN, WORDS_HARD_MAX = 700, 1400
SEO_TITLE_MIN, SEO_TITLE_MAX = 50, 60
FAQ_MIN, FAQ_MAX = 3, 5


def li(lang):
    """Index into the (en, es) tuples above."""
    return 1 if lang == "es" else 0


def base_path(lang):
    return "/es/" if lang == "es" else "/"


# ------------------------------------------------------------------ helpers --

def strip_tags(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    text = htmllib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def word_count(html_body):
    return len(strip_tags(html_body).split())


def reading_minutes(html_body):
    return max(1, round(word_count(html_body) / 225))


def neutralize_template_syntax(html_body):
    """Posts are .njk files — a stray {{ or {% from the model would crash the
    Eleventy build. Turn any into harmless entities."""
    return (
        html_body.replace("{{", "&#123;&#123;")
        .replace("}}", "&#125;&#125;")
        .replace("{%", "&#123;&#37;")
        .replace("%}", "&#37;&#125;")
    )


# ------------------------------------------------------- 2. external links ---

def expand_source_markers(html_body, lang, already_kept=0):
    """Turn [[SOURCE:key]] into a real anchor. Unknown keys are dropped rather
    than guessed at, and the cap is enforced here too.

    Runs AFTER sanitize_external_links so the anchors created here are never
    fed back through the sanitizer, which would unwrap them once the budget was
    already spent."""
    kept, unknown = [], []
    budget = MAX_EXTERNAL_LINKS - already_kept

    def repl(match):
        key = match.group(1).lower()
        entry = SOURCE_LINKS.get(key)
        if not entry:
            unknown.append(key)
            return ""
        if len(kept) >= budget:
            return entry[1 + li(lang)]  # over the cap: keep the words, drop the link
        url = entry[0]
        kept.append(url)
        return (f'<a href="{url}" target="_blank" rel="noopener nofollow">'
                f"{entry[1 + li(lang)]}</a>")

    return SOURCE_MARKER_RE.sub(repl, html_body), kept, unknown


def _host_allowed(url):
    m = re.match(r"https?://([^/?#]+)", url, re.I)
    if not m:
        return False
    host = m.group(1).lower().split(":")[0]
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def sanitize_external_links(html_body, already_kept=0):
    """Unwrap every external <a> that is not on the whitelist, force the rest to
    the domain root, and keep at most MAX_EXTERNAL_LINKS. Link text is always
    preserved as plain prose, so removing a link never loses a sentence."""
    kept = []
    removed = []
    budget = MAX_EXTERNAL_LINKS - already_kept

    def repl(match):
        href = htmllib.unescape(match.group(1)).strip()
        inner = match.group(2)
        if not re.match(r"https?://", href, re.I):
            return match.group(0)  # internal / mailto / sms / tel — leave alone
        if not _host_allowed(href) or len(kept) >= budget:
            removed.append(href)
            return inner
        root = _domain_root(href)
        kept.append(root)
        return (
            f'<a href="{htmllib.escape(root, quote=True)}" target="_blank" '
            f'rel="noopener nofollow">{inner}</a>'
        )

    out = re.sub(r'''<a\b[^>]*?href=["']([^"']*)["'][^>]*>(.*?)</a>''', repl,
                 html_body, flags=re.I | re.S)
    return out, kept, removed


def _domain_root(url):
    """Collapse any URL to the whitelisted root we actually publish."""
    m = re.match(r"(https?://[^/?#]+)", url, re.I)
    host_root = m.group(1) if m else url
    host = host_root.split("://", 1)[-1].lower()
    for allowed in ALLOWED_SOURCES:
        a_host = allowed.split("://", 1)[-1].rstrip("/").lower()
        if host == a_host or host.endswith("." + a_host.split("www.", 1)[-1]):
            return allowed
    return host_root + "/"


# ------------------------------------------------------- 3. internal links ---

def service_url(category, lang):
    anchor = SERVICE_ANCHORS.get(category, SERVICE_ANCHORS["general"])
    url = base_path(lang) + "services.html"
    return url + ("#" + anchor if anchor else "")


def service_link_html(category, lang):
    text = SERVICE_LINK_TEXT.get(category, SERVICE_LINK_TEXT["general"])[li(lang)]
    return f'<a href="{service_url(category, lang)}">{text}</a>'


def inject_service_link(html_body, category, lang):
    """Exactly one link to the matching services.html anchor. The model marks a
    spot; if it forgot, drop it into the first paragraph of the article."""
    link = service_link_html(category, lang)
    if MARKER_SERVICE in html_body:
        html_body = html_body.replace(MARKER_SERVICE, link, 1)
        return html_body.replace(MARKER_SERVICE, ""), True

    sentence = (
        f"Si prefiere dejarlo en manos de un profesional, vea {link} "
        f"para el oeste de Massachusetts."
        if lang == "es"
        else f"If you would rather hand the job to a professional, see {link} "
             f"for Western Massachusetts homeowners."
    )
    m = re.search(r"</p>", html_body, re.I)
    if m:
        i = m.end()
        return html_body[:i] + f"<p>{sentence}</p>" + html_body[i:], False
    return html_body + f"<p>{sentence}</p>", False


# ------------------------------------------------------------- 4. CTA block --

def inline_cta_html(lang):
    """Fixed markup — identical on every post. Never model-authored."""
    if lang == "es":
        line = "¿Prefiere que lo hagamos nosotros? Los estimados son gratis."
        label = "Solicite un Estimado Gratis"
    else:
        line = "Would you rather we handled it? Estimates are always free."
        label = "Get a Free Estimate"
    url = base_path(lang) + "contact.html#estimate-form"
    return (
        '<div class="blog-cta-inline">'
        f"<p>{line}</p>"
        f'<a class="btn btn--gold" href="{url}">{label}</a>'
        "</div>"
    )


def inject_inline_cta(html_body, lang, faq_start=None):
    """One CTA roughly mid-article. Model marks the spot; otherwise it goes
    before the <h2> closest to the middle of the article (never inside the FAQ,
    never before the first section)."""
    cta = inline_cta_html(lang)
    if MARKER_CTA in html_body:
        html_body = html_body.replace(MARKER_CTA, cta, 1)
        return html_body.replace(MARKER_CTA, ""), True

    limit = faq_start if faq_start is not None else len(html_body)
    heads = [m.start() for m in re.finditer(r"<h2\b", html_body, re.I)
             if m.start() < limit]
    if len(heads) < 2:
        return html_body + cta, False
    mid = limit / 2
    pos = min(heads[1:], key=lambda p: abs(p - mid))
    return html_body[:pos] + cta + html_body[pos:], False


# --------------------------------------------------------------- 5. FAQ ------

FAQ_HEADING_RE = re.compile(
    r'<h2\b[^>]*(?:id="faq"|>\s*(?:frequently asked|faq|preguntas frecuentes))',
    re.I,
)


def find_faq_start(html_body):
    for m in re.finditer(r"<h2\b[^>]*>.*?</h2>", html_body, re.I | re.S):
        head = m.group(0)
        if re.search(r'id="faq"', head, re.I) or re.search(
            r"frequently asked|\bfaq\b|preguntas frecuentes", strip_tags(head), re.I
        ):
            return m.start()
    return None


def extract_faq(html_body):
    """Pull the H3/P pairs out of the FAQ section and wrap the section for
    styling. The JSON-LD is built from what is returned here, so the schema and
    the visible copy can never drift apart."""
    start = find_faq_start(html_body)
    if start is None:
        return html_body, []

    section = html_body[start:]
    pairs = []
    for m in re.finditer(
        r"<h3\b[^>]*>(.*?)</h3>\s*((?:<p\b[^>]*>.*?</p>\s*)+)", section, re.I | re.S
    ):
        q = strip_tags(m.group(1))
        a = strip_tags(m.group(2))
        if q and a:
            pairs.append({"q": q, "a": a})

    if not pairs:
        return html_body, []

    wrapped = (
        html_body[:start]
        + '<section class="blog-faq">'
        + section
        + "</section>"
    )
    return wrapped, pairs[:FAQ_MAX]


# ------------------------------------------------------------- 6. photos -----

def _photos_in(dirname):
    d = STOCK_DIR / dirname
    if not d.is_dir():
        return []
    return sorted(
        p for p in d.iterdir()
        if p.is_file() and p.suffix.lower() in PHOTO_EXTS and not p.name.startswith(".")
    )


def _first_photo(dirname):
    files = _photos_in(dirname)
    return files[0] if files else None


def _resize(src, dst):
    """Resize + centre-crop to 16:9. sips on macOS, ImageMagick or Pillow in CI,
    plain copy as a last resort so a post never loses its photo."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.jpg")

    if shutil.which("sips"):
        try:
            subprocess.run(["sips", "--resampleWidth", str(PHOTO_W), str(src),
                            "--out", str(tmp)],
                           check=True, capture_output=True)
            subprocess.run(["sips", "-c", str(PHOTO_H), str(PHOTO_W),
                            "-s", "format", "jpeg", "-s", "formatOptions", "68",
                            str(tmp), "--out", str(dst)],
                           check=True, capture_output=True)
            tmp.unlink(missing_ok=True)
            return "sips"
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"  sips failed ({e}); trying next resizer")
            tmp.unlink(missing_ok=True)

    for tool in ("magick", "convert"):
        if shutil.which(tool):
            try:
                subprocess.run(
                    [tool, str(src), "-resize", f"{PHOTO_W}x{PHOTO_H}^",
                     "-gravity", "center", "-extent", f"{PHOTO_W}x{PHOTO_H}",
                     "-quality", "68", str(dst)],
                    check=True, capture_output=True)
                return tool
            except (subprocess.CalledProcessError, OSError) as e:
                print(f"  {tool} failed ({e}); trying next resizer")

    try:
        from PIL import Image, ImageOps  # noqa: PLC0415
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            ImageOps.fit(im, (PHOTO_W, PHOTO_H), method=Image.LANCZOS,
                         centering=(0.5, 0.5)).save(dst, "JPEG", quality=68)
        return "pillow"
    except Exception as e:  # noqa: BLE001 - any Pillow/codec problem falls through
        print(f"  Pillow failed ({e}); falling back to copy")

    if src.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        shutil.copyfile(src, dst)
        return "copy"
    return None


def prepare_photos(category, slug):
    """Hero + one in-body photo, both from the first stock folder that has
    anything. The in-body photo is a *different* file from that same folder, so
    a post never shows the same image twice; folders holding a single photo
    (garage-epoxy, deck-patio) simply get no second image.

    Each output is cached independently -- an existing hero must not stop a
    missing in-body photo from being generated."""
    hero_dst = WEB_DIR / f"blog-{slug}.jpg"
    inline_dst = WEB_DIR / f"blog-{slug}-2.jpg"

    sources = []
    for dirname in CATEGORY_PHOTO_DIRS.get(category, []) + ["general"]:
        files = _photos_in(dirname)
        if files:
            sources = files
            print(f"  Photo folder: images/stock/{dirname}/ ({len(files)} file(s))")
            break

    def ensure(dst, index):
        if dst.exists():
            return str(dst)
        if len(sources) <= index:
            return None
        if _resize(sources[index], dst):
            print(f"  {sources[index]} -> {dst}")
            return str(dst)
        print(f"  Could not process {sources[index]}")
        return None

    hero = ensure(hero_dst, 0)
    if not hero:
        print(f"  No photo for category '{category}' or general/ — skipping")
        return None, None
    inline = ensure(inline_dst, 1)
    if not inline:
        print("  No second photo in that folder — no in-body image")
    return hero, inline


def photo_alt(category, lang, title):
    pair = PHOTO_ALT.get(category)
    return pair[li(lang)] if pair else title


def photo_alt_inline(category, lang, title):
    pair = PHOTO_ALT_INLINE.get(category)
    return pair[li(lang)] if pair else photo_alt(category, lang, title)


def inject_inline_photo(html_body, image, alt, faq_start=None):
    """Place the second photo inside the article, right after the second <h2>
    so it illustrates that section rather than floating between topics. Skipped
    when there is no photo or the post is too short to have a second section
    outside the FAQ."""
    if not image:
        return html_body, False
    limit = faq_start if faq_start is not None else len(html_body)
    heads = [m for m in re.finditer(r"<h2\b[^>]*>.*?</h2>", html_body, re.I | re.S)
             if m.start() < limit]
    if len(heads) < 2:
        return html_body, False
    at = heads[1].end()
    fig = (
        f'<figure class="blog-figure">'
        f'<img src="/{image}" alt="{htmllib.escape(alt, quote=True)}" '
        f'width="{PHOTO_W}" height="{PHOTO_H}" loading="lazy" decoding="async">'
        f"</figure>"
    )
    return html_body[:at] + fig + html_body[at:], True


# ---------------------------------------------------------- published.json ---

def load_published():
    if PUBLISHED_FILE.exists():
        try:
            return json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"published.json unreadable ({e}); starting a fresh index")
    return []


def save_published(records):
    records.sort(key=lambda r: (r.get("date", ""), r.get("lang", ""), r.get("slug", "")))
    PUBLISHED_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def record_published(records, entry):
    records = [r for r in records
               if not (r.get("slug") == entry["slug"] and r.get("lang") == entry["lang"])]
    records.append(entry)
    return records


def related_posts(records, slug, category, lang, limit=2):
    """Same category, same language, already published — chosen here, never by
    the model, so a post can't link to something that does not exist."""
    matches = [
        r for r in records
        if r.get("lang") == lang
        and r.get("category") == category
        and r.get("slug") != slug
    ]
    matches.sort(key=lambda r: r.get("date", ""), reverse=True)
    return [{"title": r["title"], "url": r["url"]} for r in matches[:limit]]


# --------------------------------------------------------- 7. copy policing --

BANNED_PATTERNS = [
    (r"\bA\.?I\.?\b(?![a-z])", "mentions AI"),
    (r"\bartificial intelligence\b", "mentions artificial intelligence"),
    (r"\binteligencia artificial\b", "mentions inteligencia artificial"),
    (r"\b\d+\+?\s*(?:years|años)\s+(?:of\s+)?(?:experience|in business|de experiencia)\b",
     "claims years of experience"),
    (r"\b(?:decades|décadas)\s+of\s+experience\b", "claims decades of experience"),
    (r"\bsince\s+(?:19|20)\d{2}\b", "claims a founding year"),
]


def copy_warnings(html_body, seo_title):
    """Rules the model is told about but is not trusted to follow."""
    text = strip_tags(html_body)
    problems = [why for pat, why in BANNED_PATTERNS if re.search(pat, text, re.I)]

    wc = word_count(html_body)
    if not WORDS_MIN <= wc <= WORDS_MAX:
        problems.append(f"word count {wc} outside {WORDS_MIN}-{WORDS_MAX}")

    h2s = len(re.findall(r"<h2\b", html_body, re.I))
    if not 3 <= h2s <= 7:  # 3-6 body sections + the FAQ heading
        problems.append(f"{h2s} H2 sections (want 3-6 plus an FAQ heading)")

    brand = len(re.findall(r"Prime Paint", text, re.I))
    if brand:
        problems.append(f"repeats the brand name {brand}x in body copy")

    if seo_title and not SEO_TITLE_MIN <= len(seo_title) <= SEO_TITLE_MAX:
        problems.append(
            f"seo_title is {len(seo_title)} chars (want {SEO_TITLE_MIN}-{SEO_TITLE_MAX})"
        )
    return problems


def needs_regeneration(html_body, seo_title, faq_count, external_count=None):
    """Only the hard failures justify burning another API call.

    external_count is the number of whitelisted source links that survived
    sanitising. Unlike the service link and the CTA, a citation has no
    injectable fallback -- if the model omits it there is nothing to insert in
    its place, so it has to be caught here or the post ships without sources."""
    text = strip_tags(html_body)
    if any(re.search(pat, text, re.I) for pat, _ in BANNED_PATTERNS[:3]):
        return "the draft mentions AI"
    wc = word_count(html_body)
    if not WORDS_HARD_MIN <= wc <= WORDS_HARD_MAX:
        return f"word count {wc} far outside {WORDS_MIN}-{WORDS_MAX}"
    if faq_count < FAQ_MIN:
        return f"only {faq_count} FAQ pairs (need {FAQ_MIN}-{FAQ_MAX})"
    if external_count is not None and external_count < 1:
        return ("no citation from the approved source list survived "
                "(either none was included, or every link was off-whitelist)")
    return None


# --------------------------------------------------------------- assembly ----

# Words a title must never end on once it has been cut short.
_DANGLING = {
    "a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "or", "the",
    "to", "with", "your", "el", "la", "los", "las", "de", "del", "en", "para",
    "por", "y", "o", "un", "una", "su", "con",
}

# Past SEO_TITLE_MAX a title just gets clipped in the SERP; past this it looks
# broken, so we cut. An intact 63-character title beats a mangled 54.
SEO_TITLE_TOLERATED = 65


def trim_seo_title(candidate, fallback):
    title = (candidate or "").strip() or fallback.strip()
    if len(title) <= SEO_TITLE_TOLERATED:
        return title
    cut = title[:SEO_TITLE_TOLERATED]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    words = cut.rstrip(" ,;:-–—").split()
    while len(words) > 3 and words[-1].lower().strip(",;:") in _DANGLING:
        words.pop()
    return " ".join(words).rstrip(" ,;:-–—")


def build_body(raw_html, category, lang, inline_image=None, inline_alt=None):
    """The full deterministic pass: model prose in, publishable body out."""
    body = neutralize_template_syntax(raw_html.strip())
    # Sanitize first: any <a> the model wrote by hand goes through the whitelist.
    # Expansion comes second so its anchors are never re-sanitized.
    body, kept, removed = sanitize_external_links(body)
    body, sourced, unknown_sources = expand_source_markers(
        body, lang, already_kept=len(kept))
    kept = kept + sourced
    body, service_marked = inject_service_link(body, category, lang)
    body, photo_placed = inject_inline_photo(
        body, inline_image, inline_alt, faq_start=find_faq_start(body))
    body, cta_marked = inject_inline_cta(body, lang, faq_start=find_faq_start(body))
    body, faq = extract_faq(body)
    return {
        "body": body,
        "faq": faq,
        "external_kept": kept,
        "external_removed": removed,
        "unknown_sources": unknown_sources,
        "service_marker_used": service_marked,
        "cta_marker_used": cta_marked,
        "inline_photo_placed": photo_placed,
    }


def front_matter(fields):
    """JSON scalars are valid YAML, so json.dumps handles all the escaping."""
    order = ["layout", "lang", "title", "seo_title", "summary", "keywords",
             "category", "category_label", "date", "date_iso", "date_display",
             "reading_minutes", "slug", "image", "image_alt", "permalink",
             "type", "faq", "related"]
    lines = ["---"]
    for key in order:
        if key not in fields:
            continue
        value = fields[key]
        if key == "layout":
            lines.append(f"layout: {value}")
        elif key == "permalink":
            lines.append(f"permalink: {value}")
        elif isinstance(value, (list, dict)):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def format_date(date_str, lang):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    if lang == "es":
        months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                  "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        return f"{d.day} de {months[d.month - 1]} de {d.year}"
    return d.strftime("%B %-d, %Y")


def assemble_post(*, slug, lang, category, date_str, title, seo_title, summary,
                  keywords, body, faq, image, image_alt, related):
    lang_dir = ES_DIR if lang == "es" else EN_DIR
    permalink = (f"es/blog/{slug}/index.html" if lang == "es"
                 else f"blog/{slug}/index.html")
    fields = {
        "layout": "post.njk",
        "lang": lang,
        "title": title,
        "seo_title": seo_title,
        "summary": summary,
        "keywords": keywords,
        "category": category,
        "category_label": CATEGORY_LABELS.get(
            category, CATEGORY_LABELS["general"])[li(lang)],
        "date": date_str,
        "date_iso": date_str,
        "date_display": format_date(date_str, lang),
        "reading_minutes": reading_minutes(body),
        "slug": slug,
        "permalink": permalink,
        "type": "post",
        "faq": faq,
        "related": related,
    }
    if image:
        fields["image"] = image
        fields["image_alt"] = image_alt

    lang_dir.mkdir(parents=True, exist_ok=True)
    path = lang_dir / f"{slug}.njk"
    path.write_text(front_matter(fields) + "\n" + body + "\n", encoding="utf-8")

    entry = {
        "slug": slug,
        "lang": lang,
        "title": title,
        "seo_title": seo_title,
        "summary": summary,
        "category": category,
        "date": date_str,
        "url": ("/es/blog/" if lang == "es" else "/blog/") + slug + "/",
        "image": image or "",
    }
    return path, entry
