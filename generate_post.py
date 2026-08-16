"""
Generates one blog post (EN + ES) per run from topics.json.

The model writes prose only. Every URL on the page — external sources, the
service-page link, related-post links, both CTAs — and the FAQ JSON-LD are
produced by blog_pipeline.py from hardcoded data, so a hallucinated link can
never reach the site.
"""

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
                    "max_tokens": 8000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=240,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
    return None


def parse_json_response(raw):
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-zA-Z]*\s*", "", clean)
        clean = re.sub(r"```\s*$", "", clean).strip()
    return json.loads(clean)


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

SEO TITLE
- Also return "seo_title": a {bp.SEO_TITLE_MIN}-{bp.SEO_TITLE_MAX} character title
  with the primary keyword in the first few words. Count the characters.
- Write naturally. Do not repeat the primary keyword more than 2-3 times in the
  whole article — no keyword stuffing.

REQUIRED FAQ SECTION (second to last thing in the article)
- End the article with: <h2 id="faq">{faq_head}</h2>
- Then {bp.FAQ_MIN} to {bp.FAQ_MAX} question/answer pairs, each formatted exactly as
  <h3>The question?</h3><p>A direct 2-4 sentence answer.</p>
- Answer the question in the first sentence. No lists inside FAQ answers.

EXTERNAL LINKS — STRICT
- You may cite 1-2 sources, and ONLY from this list:
{sources}
- Link to the domain root or the exact URL shown above. NEVER build a deeper URL
  by guessing a path — those break.
- Never link to another painting company, contractor, or home-services business.
- Maximum 2 external links in the entire article.

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

Return ONLY valid JSON (no markdown fences, no commentary):
{{
  "title": "{title}",
  "seo_title": "{bp.SEO_TITLE_MIN}-{bp.SEO_TITLE_MAX} character SEO title",
  "summary": "150-200 character meta description",
  "keywords": "kw1, kw2, kw3, kw4, kw5",
  "social_hook": "Engaging 1-2 sentence social media caption",
  "detail": "<full HTML article — <h2>, <h3>, <p>, <ul>, <ol>, <a> tags only>"
}}"""


# ---------------------------------------------------------------- generate ---

def generate_article(title, lang, category, max_attempts=2):
    """Draft, run the deterministic pass, and retry once on a hard failure."""
    correction = None
    last = None
    for attempt in range(1, max_attempts + 1):
        raw = call_claude(build_prompt(title, lang, category, correction))
        if not raw:
            return None
        try:
            data = parse_json_response(raw)
        except json.JSONDecodeError as e:
            print(f"  JSON parse error ({lang}): {e}")
            print(f"  {raw[:400]}")
            correction = "your response was not valid JSON"
            continue

        processed = bp.build_body(data.get("detail", ""), category, lang)
        seo_title = bp.trim_seo_title(data.get("seo_title"), title)
        last = (data, processed, seo_title)

        problem = bp.needs_regeneration(processed["body"], seo_title,
                                        len(processed["faq"]))
        if not problem:
            return last
        print(f"  Draft {attempt} rejected: {problem}")
        correction = problem
        if attempt < max_attempts:
            time.sleep(5)

    if last:
        print("  Using the last draft despite the issue above.")
    return last


def build_and_write(topic, slug, lang, category, date_str, image, published):
    title = topic["en"] if lang == "en" else topic["es"]
    print(f"Generating {lang.upper()} post...")

    result = generate_article(title, lang, category)
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
    print(f"  FAQ pairs: {len(faq)} | words: {bp.word_count(body)}")

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


def main():
    topics = load_topics()
    topic = pick_topic(topics)
    if not topic:
        print("No topics remaining.")
        return

    slug = slugify(topic["en"])
    category = topic.get("category", "general")
    date_str = datetime.now().strftime("%Y-%m-%d")
    published = bp.load_published()

    print(f"Selected topic: {topic['en']}  [{category}]")
    image = bp.prepare_photo(category, slug)

    if not is_published(slug, EN_DIR):
        published = build_and_write(topic, slug, "en", category, date_str,
                                    image, published)
        time.sleep(10)
    if not is_published(slug, ES_DIR):
        published = build_and_write(topic, slug, "es", category, date_str,
                                    image, published)

    bp.save_published(published)
    print(f"published.json now lists {len(published)} posts.")


if __name__ == "__main__":
    main()
