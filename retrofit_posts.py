"""
Re-runs the blog_pipeline pass over posts that were published before the
pipeline existed, so old posts get the same photo, links, CTAs, FAQ schema and
front matter as anything generated from now on. Rebuilds published.json from
what is on disk.

Idempotent: safe to run repeatedly. No API calls — existing prose is reused.
"""

import re
from pathlib import Path

import blog_pipeline as bp

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)
SCALAR_RE = re.compile(r'^([a-zA-Z_]+):\s*(.*)$')


def split_post(path):
    m = FM_RE.match(path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"{path}: no front matter")
    meta = {}
    for line in m.group(1).splitlines():
        km = SCALAR_RE.match(line)
        if not km:
            continue
        key, value = km.group(1), km.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1].replace("&quot;", '"')
        meta[key] = value
    return meta, m.group(2)


def strip_injected(body):
    """Remove blocks a previous retrofit added so re-running does not stack
    duplicates."""
    body = re.sub(r'<div class="blog-cta-inline">.*?</div>', "", body, flags=re.S)
    body = re.sub(r'<aside class="blog-related">.*?</aside>', "", body, flags=re.S)
    body = re.sub(r'</?section class="blog-faq">', "", body)
    body = re.sub(r"</section>\s*$", "", body.rstrip())
    # drop a service link paragraph appended by an earlier run
    body = re.sub(
        r'<p>(?:If you would rather hand the job|Si prefiere dejarlo en manos)'
        r'.*?</p>', "", body, flags=re.S)
    return body.strip()


def main():
    drafts = []
    for lang, lang_dir in (("en", bp.EN_DIR), ("es", bp.ES_DIR)):
        for path in sorted(lang_dir.glob("*.njk")):
            meta, body = split_post(path)
            if meta.get("type") != "post":
                continue
            category = meta.get("category", "general")
            slug = meta.get("slug") or path.stem
            title = meta.get("title", slug)

            image = bp.prepare_photo(category, slug)
            processed = bp.build_body(strip_injected(body), category, lang)
            # A stored seo_title that is just a prefix of the title came from
            # an earlier retrofit, not from the model — re-derive it so an
            # improved trimmer actually takes effect.
            stored = meta.get("seo_title", "")
            if stored and title.startswith(stored):
                stored = ""
            seo_title = bp.trim_seo_title(stored, title)

            print(f"{path}")
            print(f"  words {bp.word_count(processed['body'])} | "
                  f"FAQ {len(processed['faq'])} | "
                  f"seo_title {len(seo_title)} chars")
            for note in bp.copy_warnings(processed["body"], seo_title):
                print(f"  WARNING: {note}")
            if processed["external_removed"]:
                print(f"  Stripped: {processed['external_removed']}")

            drafts.append({
                "slug": slug, "lang": lang, "category": category,
                "date_str": meta.get("date", "2026-01-01"), "title": title,
                "seo_title": seo_title, "summary": meta.get("summary", ""),
                "keywords": meta.get("keywords", ""),
                "body": processed["body"], "faq": processed["faq"],
                "image": image,
                "image_alt": bp.photo_alt(category, lang, title),
            })

    # Build the index first, then assemble, so related links can see every post.
    index = []
    for d in drafts:
        index.append({
            "slug": d["slug"], "lang": d["lang"], "title": d["title"],
            "seo_title": d["seo_title"], "summary": d["summary"],
            "category": d["category"], "date": d["date_str"],
            "url": ("/es/blog/" if d["lang"] == "es" else "/blog/") + d["slug"] + "/",
            "image": d["image"] or "",
        })

    published = []
    for d in drafts:
        related = bp.related_posts(index, d["slug"], d["category"], d["lang"])
        if related:
            print(f"  {d['lang']}/{d['slug']} related -> {[r['url'] for r in related]}")
        path, entry = bp.assemble_post(related=related, **d)
        published = bp.record_published(published, entry)
        print(f"  Rewrote: {path}")

    bp.save_published(published)
    print(f"\npublished.json rebuilt with {len(published)} posts.")


if __name__ == "__main__":
    main()
