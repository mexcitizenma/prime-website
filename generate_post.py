"""
Generates one blog post (EN + ES) per run from topics.json.

The model writes prose only. Every URL on the page — external sources, the
service-page link, related-post links, both CTAs — and the FAQ JSON-LD are
produced by blog_pipeline.py from hardcoded data, so a hallucinated link can
never reach the site.
"""

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests

import blog_pipeline as bp

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TOPICS_FILE = "topics.json"
EN_DIR = bp.EN_DIR
ES_DIR = bp.ES_DIR
MODEL = "claude-sonnet-4-6"
# A 1200-word article plus metadata runs well under this; the old 8000
# left little headroom. Staying at/below ~16k keeps non-streaming
# requests clear of SDK/HTTP timeouts.
MAX_TOKENS = 16000


def load_topics():
    with open(TOPICS_FILE) as f:
        return json.load(f)


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:80]


def is_published(slug, lang_dir):
    return (lang_dir / f"{slug}.njk").exists()


def pick_topic(topics):
    partial, fresh = [], []
    for topic in topics:
        slug = slugify(topic["en"])
        en_done = is_published(slug, EN_DIR)
        es_done = is_published(slug, ES_DIR)
        if en_done and es_done:
            continue
        (partial if (en_done or es_done) else fresh).append(topic)

    month = datetime.now().month
    if month in [3, 4, 5]:
        season = "spring"
    elif month in [6, 7, 8]:
        season = "summer"
    elif month in [9, 10, 11]:
        season = "fall"
    else:
        season = "winter"
    fresh.sort(key=lambda t: (t.get("season") != season, t.get("season") != "all"))
    queue = partial + fresh
    return queue[0] if queue else None


def call_claude(prompt, retries=3):
    """Returns (text, stop_reason) so the caller can tell a truncated response
    apart from a malformed one. A None text means every attempt failed."""
    delays = [30, 60, 120]
    for attempt in range(retries):
        if attempt > 0:
            print(f"Retry {attempt}, sleeping {delays[attempt-1]}s...")
            time.sleep(delays[attempt - 1])
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=240,
            )
            resp.raise_for_status()
            payload = resp.json()

            stop_reason = payload.get("stop_reason")
            usage = payload.get("usage", {})
            blocks = [b for b in payload.get("content", []) if b.get("type") == "text"]
            text = blocks[0]["text"] if blocks else ""

            print(f"  API: stop_reason={stop_reason} "
                  f"output_tokens={usage.get('output_tokens')} "
                  f"chars={len(text)}")
            if stop_reason == "max_tokens":
                print(f"  The response hit the {MAX_TOKENS}-token ceiling and was cut off.")
            elif stop_reason == "refusal":
                print("  The model declined this prompt.")
            if not text:
                print(f"  No text block in the response (stop_reason={stop_reason}).")
                continue
            return text, stop_reason
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
    return None, None


DEBUG_DIR = Path("_debug")


def parse_json_response(raw):
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-zA-Z]*\s*", "", clean)
        clean = re.sub(r"```\s*$", "", clean).strip()
    return json.loads(clean)


def dump_raw(raw, slug, lang, attempt):
    """Write the unparsed response to disk. Guessing at a JSON failure from a
    400-char excerpt wastes a run; the whole thing costs nothing to keep."""
    DEBUG_DIR.mkdir(exist_ok=True)
    path = DEBUG_DIR / f"{slug}-{lang}-attempt{attempt}.txt"
    path.write_text(raw, encoding="utf-8")
    return path


def describe_json_error(raw, err):
    """Say whether the JSON was cut short or simply malformed, and point at the
    field it died in — a truncated response and a bad escape need different fixes."""
    pos = getattr(err, "pos", None)
    detail = f"{err.msg} at char {pos}" if pos is not None else str(err)
    if pos is None:
        return detail
    field = None
    for m in re.finditer(r'"(\w+)"\s*:', raw[:pos]):
        field = m.group(1)
    where = f" (inside the \"{field}\" field)" if field else ""
    tail = " — response ends here, so it was cut off" if pos >= len(raw) - 2 else ""
    return f"{detail}{where}{tail}; {len(raw)} chars received"


# ------------------------------------------------------------------ prompt ---

def build_prompt(title, lang, category, correction=None):
    lang_label = "English" if lang == "en" else "Spanish (neutral Latin American)"
    sources = "\n".join(f"  - {u}" for u in bp.ALLOWED_SOURCES)
    faq_head = "Preguntas Frecuentes" if lang == "es" else "Frequently Asked Questions"
    team = "nuestro equipo" if lang == "es" else "our team"

    fix = ""
    if correction:
        fix = (
            f"\nIMPORTANT — your previous draft was rejected because: {correction}. "
            f"Fix that specific problem in this draft.\n"
        )

    return f"""You are a home improvement content specialist writing for a local painting and home services company serving Western Massachusetts (Westfield, Agawam, Springfield, West Springfield, Southampton, Holyoke).

Write an SEO-optimized blog article in {lang_label}.

Topic: {title}
Category: {category}
Service area: Western Massachusetts / New England
{fix}
LENGTH AND STRUCTURE
- 800-1200 words of body copy. This is a hard requirement — count as you write.
- 3 to 6 <h2> sections, each covering one distinct sub-topic. Use <h3> for
  sub-points inside a section.
- Write for a homeowner deciding what to do next: practical, specific, actionable.
- Mention Western MA cities and New England seasons/climate naturally where they
  genuinely add information. Do not force them into every paragraph.

SEO TITLE AND METADATA
- Also return "seo_title": a {bp.SEO_TITLE_MIN}-{bp.SEO_TITLE_MAX} character title
  with the primary keyword in the first few words. Count the characters.
- Keep the metadata fields tight — they are not where the value is. "keywords" is
  exactly 5 comma-separated phrases and no more than 100 characters in total;
  "summary" is 150-200 characters; "social_hook" is one or two sentences. Put your
  effort into "detail".
- Write naturally. Do not repeat the primary keyword more than 2-3 times in the
  whole article — no keyword stuffing.

REQUIRED FAQ SECTION (second to last thing in the article)
- End the article with: <h2 id="faq">{faq_head}</h2>
- Then {bp.FAQ_MIN} to {bp.FAQ_MAX} question/answer pairs, each formatted exactly as
  <h3>The question?</h3><p>A direct 2-4 sentence answer.</p>
- Answer the question in the first sentence. No lists inside FAQ answers.

EXTERNAL LINKS — REQUIRED, AND STRICT
- You MUST cite at least 1 and at most 2 sources, and ONLY from this list:
{sources}
- Use the URL exactly as written above. Do NOT add a path, query or fragment —
  a deeper URL you infer will 404, and the build will strip the link.
  Correct:   <a href="https://www.epa.gov/">the EPA</a>
  Rejected:  <a href="https://www.epa.gov/lead/rrp-rule">the EPA RRP rule</a>
- Put each citation inside a sentence where it supports a factual claim
  (a regulation, a health guideline, a material spec). Do not add a link list.
- Never link to another painting company, contractor, or home-services business.
- A draft with zero links from this list is rejected and regenerated.

PLACEHOLDERS — insert these two markers, exactly as written, once each
- {bp.MARKER_SERVICE} — put this inside a sentence where it is natural to point the
  reader at the company's own service page for this topic. The build replaces it
  with the correct link and link text, so write the sentence around it, e.g.
  "For a job this size, {bp.MARKER_SERVICE} may be the faster route." Do NOT write
  your own <a> tag for it and do not add any URL.
- {bp.MARKER_CTA} — put this on its own, between two <h2> sections near the middle
  of the article. The build replaces it with a call-to-action block. Do not write
  any CTA text yourself.

VOICE RULES — these are absolute
- Never mention AI, artificial intelligence, automation, or how this was written.
- Never claim years in business, experience, "decades", or a founding year.
- Never write the company name anywhere in the body.
- Use "{team}" at most once in the whole article.

Return ONLY valid JSON (no markdown fences, no commentary). Every double quote
and newline inside a string value must be escaped, and the HTML in "detail" must
be a single line with no raw line breaks:
{{
  "title": "{title}",
  "seo_title": "{bp.SEO_TITLE_MIN}-{bp.SEO_TITLE_MAX} character SEO title",
  "summary": "150-200 character meta description",
  "keywords": "exactly 5 comma-separated keywords, 100 characters total at most",
  "social_hook": "Engaging 1-2 sentence social media caption",
  "detail": "<full HTML article — <h2>, <h3>, <p>, <ul>, <ol>, <a> tags only>"
}}"""


# ---------------------------------------------------------------- generate ---

def generate_article(title, lang, category, inline_image=None, max_attempts=3,
                     slug="post"):
    """Draft, run the deterministic pass, and retry on a hard failure.

    A truncated response and a malformed one look identical to json.loads but
    need different corrections, so they are diagnosed separately here."""
    correction = None
    last = None
    for attempt in range(1, max_attempts + 1):
        raw, stop_reason = call_claude(build_prompt(title, lang, category, correction))
        if not raw:
            return None
        try:
            data = parse_json_response(raw)
        except json.JSONDecodeError as e:
            path = dump_raw(raw, slug, lang, attempt)
            print(f"  JSON parse error ({lang}): {describe_json_error(raw, e)}")
            print(f"  Full response saved to {path}")
            if stop_reason == "max_tokens":
                # The ceiling cut the JSON off. Asking for valid JSON won't help;
                # asking for less text will.
                correction = (
                    f"your previous response was cut off at the {MAX_TOKENS}-token "
                    "limit before the JSON closed. Write a SHORTER article — stay at "
                    "the low end of the word range — and keep every field compact"
                )
            else:
                correction = (
                    "your response was not valid JSON. Escape every double quote and "
                    "newline inside string values, and return nothing but the JSON object"
                )
            continue

        processed = bp.build_body(
            data.get("detail", ""), category, lang,
            inline_image=inline_image,
            inline_alt=bp.photo_alt_inline(category, lang, title))
        seo_title = bp.trim_seo_title(data.get("seo_title"), title)
        last = (data, processed, seo_title)

        problem = bp.needs_regeneration(processed["body"], seo_title,
                                        len(processed["faq"]),
                                        len(processed["external_kept"]))
        if not problem:
            return last
        print(f"  Draft {attempt} rejected: {problem}")
        correction = problem
        if attempt < max_attempts:
            time.sleep(5)

    if last:
        print("  Using the last draft despite the issue above.")
    return last


def build_and_write(topic, slug, lang, category, date_str, image, inline_image,
                    published):
    title = topic["en"] if lang == "en" else topic["es"]
    print(f"Generating {lang.upper()} post...")

    result = generate_article(title, lang, category,
                              inline_image=inline_image, slug=slug)
    if not result:
        print(f"  Giving up on the {lang.upper()} post.")
        return published

    data, processed, seo_title = result
    body, faq = processed["body"], processed["faq"]

    for note in bp.copy_warnings(body, seo_title):
        print(f"  WARNING: {note}")
    if processed["external_removed"]:
        print(f"  Stripped {len(processed['external_removed'])} off-whitelist "
              f"link(s): {processed['external_removed']}")
    if processed["external_kept"]:
        print(f"  Kept sources: {processed['external_kept']}")
    if not processed["service_marker_used"]:
        print("  Service-link marker missing — link appended after the intro.")
    if not processed["cta_marker_used"]:
        print("  CTA marker missing — CTA placed at the mid-article heading.")
    if inline_image and not processed["inline_photo_placed"]:
        print("  In-body photo skipped — no second section outside the FAQ.")
    print(f"  FAQ pairs: {len(faq)} | words: {bp.word_count(body)} | "
          f"in-body photo: {processed['inline_photo_placed']}")

    related = bp.related_posts(published, slug, category, lang)
    if related:
        print(f"  Related posts: {[r['url'] for r in related]}")

    path, entry = bp.assemble_post(
        slug=slug, lang=lang, category=category, date_str=date_str,
        title=title, seo_title=seo_title,
        summary=data.get("summary", "").strip(),
        keywords=data.get("keywords", "").strip(),
        body=body, faq=faq,
        image=image, image_alt=bp.photo_alt(category, lang, title),
        related=related,
    )
    print(f"  Written: {path}")
    return bp.record_published(published, entry)


def write_topic(topic, published, force=False, langs=("en", "es")):
    slug = slugify(topic["en"])
    category = topic.get("category", "general")
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"Topic: {topic['en']}  [{category}]")
    image, inline_image = bp.prepare_photos(category, slug)

    for i, lang in enumerate(langs):
        lang_dir = EN_DIR if lang == "en" else ES_DIR
        if is_published(slug, lang_dir) and not force:
            continue
        if i:
            time.sleep(10)
        published = build_and_write(topic, slug, lang, category, date_str,
                                    image, inline_image, published)
    return published


def main():
    ap = argparse.ArgumentParser(description="Generate or regenerate a blog post.")
    ap.add_argument("--slug", action="append", default=[],
                    help="regenerate this slug instead of picking a new topic "
                         "(repeatable; implies --force)")
    ap.add_argument("--all", action="store_true",
                    help="with --slug omitted, regenerate every published slug")
    ap.add_argument("--lang", choices=["en", "es"],
                    help="restrict to one language (default: both)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a post that already exists")
    args = ap.parse_args()

    topics = load_topics()
    langs = (args.lang,) if args.lang else ("en", "es")
    published = bp.load_published()

    if args.slug or args.all:
        by_slug = {slugify(t["en"]): t for t in topics}
        wanted = args.slug or sorted({r["slug"] for r in published})
        missing = [s for s in wanted if s not in by_slug]
        if missing:
            print(f"Not in topics.json, skipping: {missing}")
        for slug in [s for s in wanted if s in by_slug]:
            published = write_topic(by_slug[slug], published, force=True, langs=langs)
    else:
        topic = pick_topic(topics)
        if not topic:
            print("No topics remaining.")
            return
        published = write_topic(topic, published, force=args.force, langs=langs)

    bp.save_published(published)
    print(f"published.json now lists {len(published)} posts.")


if __name__ == "__main__":
    main()
