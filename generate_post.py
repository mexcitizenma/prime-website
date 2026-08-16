import json
import os
import re
import time
import requests
from datetime import datetime
from pathlib import Path

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TOPICS_FILE = "topics.json"
EN_DIR = Path("blog-src/en")
ES_DIR = Path("blog-src/es")

def load_topics():
    with open(TOPICS_FILE) as f:
        return json.load(f)

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text.strip())
    return text[:80]

def is_published(slug, lang_dir):
    return (lang_dir / f"{slug}.njk").exists()

def pick_topic(topics):
    partial = []
    fresh = []
    for topic in topics:
        slug = slugify(topic["en"])
        en_done = is_published(slug, EN_DIR)
        es_done = is_published(slug, ES_DIR)
        if en_done and es_done:
            continue
        if en_done or es_done:
            partial.append(topic)
        else:
            fresh.append(topic)
    # seasonal priority for fresh topics
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
            time.sleep(delays[attempt-1])
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-6",
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

def build_prompt(title, lang, category):
    lang_label = "English" if lang == "en" else "Spanish (neutral Latin American)"
    return f"""You are a home improvement content specialist writing for Prime Paint & Home Services, a local painting and home services company serving Western Massachusetts (Westfield, Agawam, Springfield, West Springfield, Southampton, Holyoke).

Write a comprehensive, SEO-optimized blog article in {lang_label}.

Title: {title}
Category: {category}
Service area: Western Massachusetts / New England

Requirements:
- 1000-1400 words
- H2 and H3 subheadings
- FAQ section at the end (3-5 questions with direct answers)
- Mention specific Western MA cities naturally where relevant
- Reference New England climate/seasons where relevant
- Do NOT mention the company name in the article body
- Use "our team" / "nuestro equipo" sparingly, max once
- Practical, actionable tips homeowners can use
- AI-optimized: answer questions directly, use clear structure

Return ONLY valid JSON (no markdown, no backticks):
{{
  "title": "{title}",
  "summary": "150-200 character meta description",
  "keywords": "kw1, kw2, kw3, kw4, kw5",
  "social_hook": "Engaging 1-2 sentence social media caption",
  "detail": "<full HTML article — use <h2>, <h3>, <p>, <ul>, <ol> tags only>"
}}"""

def write_post(slug, data, lang, category, date_str):
    lang_dir = EN_DIR if lang == "en" else ES_DIR
    lang_dir.mkdir(parents=True, exist_ok=True)
    filepath = lang_dir / f"{slug}.njk"
    if lang == "en":
        permalink = f"blog/{slug}/index.html"
    else:
        permalink = f"es/blog/{slug}/index.html"
    content = f"""---
layout: post.njk
lang: {lang}
title: "{data['title'].replace('"', '&quot;')}"
summary: "{data['summary'].replace('"', '&quot;')}"
keywords: "{data['keywords']}"
category: "{category}"
date: "{date_str}"
slug: "{slug}"
permalink: {permalink}
type: post
---
{data['detail']}
"""
    filepath.write_text(content, encoding="utf-8")
    print(f"Written: {filepath}")

def main():
    topics = load_topics()
    topic = pick_topic(topics)
    if not topic:
        print("No topics remaining.")
        return
    slug = slugify(topic["en"])
    category = topic.get("category", "general")
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"Selected topic: {topic['en']}")
    # EN
    if not is_published(slug, EN_DIR):
        print("Generating EN post...")
        prompt = build_prompt(topic["en"], "en", category)
        raw = call_claude(prompt)
        if raw:
            try:
                clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                data = json.loads(clean)
                write_post(slug, data, "en", category, date_str)
            except json.JSONDecodeError as e:
                print(f"JSON parse error (EN): {e}")
                print(raw[:500])
        time.sleep(10)
    # ES
    if not is_published(slug, ES_DIR):
        print("Generating ES post...")
        prompt = build_prompt(topic["es"], "es", category)
        raw = call_claude(prompt)
        if raw:
            try:
                clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                data = json.loads(clean)
                write_post(slug, data, "es", category, date_str)
            except json.JSONDecodeError as e:
                print(f"JSON parse error (ES): {e}")
                print(raw[:500])

if __name__ == "__main__":
    main()
