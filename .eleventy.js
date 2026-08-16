const categories = require("./blog-src/_data/categories.js");

/* Lookup table so the filters below never scan the array. */
const BY_SLUG = Object.fromEntries(categories.map(c => [c.slug, c]));

/* A post's category may be missing or unknown (a new topics.json value that
   nobody added to categories.js yet). Fall back to "general" so a template
   never has to guard against undefined. */
function resolveCategory(slug, lang) {
  const cat = BY_SLUG[slug] || BY_SLUG["general"];
  const copy = cat[lang === "es" ? "es" : "en"];
  return {
    slug: cat.slug,
    label: copy.label,
    blurb: copy.blurb,
    image: cat.image
  };
}

module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("css");
  eleventyConfig.addPassthroughCopy("js");
  eleventyConfig.addPassthroughCopy("images");

  /* Only `type: post` files are articles. Category pages and the blog index
     live in the same folders and must stay out of the listings. */
  const posts = (api, glob) =>
    api.getFilteredByGlob(glob).filter(item => item.data.type === "post");

  eleventyConfig.addCollection("blog_en", api => posts(api, "blog-src/en/*.njk"));
  eleventyConfig.addCollection("blog_es", api => posts(api, "blog-src/es/*.njk"));

  /* ---- category helpers ---- */

  eleventyConfig.addFilter("category", (slug, lang) => resolveCategory(slug, lang));

  /* Categories that actually have at least one published post, in the order
     they are declared in categories.js, each carrying its own post count.
     An empty category would link to an empty page, so it is dropped. */
  eleventyConfig.addFilter("usedCategories", (collection, lang) => {
    const counts = {};
    for (const post of collection || []) {
      const slug = resolveCategory(post.data.category, lang).slug;
      counts[slug] = (counts[slug] || 0) + 1;
    }
    return categories
      .filter(c => counts[c.slug])
      .map(c => Object.assign(resolveCategory(c.slug, lang), { count: counts[c.slug] }));
  });

  eleventyConfig.addFilter("inCategory", (collection, slug) =>
    (collection || []).filter(post => resolveCategory(post.data.category).slug === slug)
  );

  /* ---- "They Also Read" ----
     Same-category posts first (newest first), then the rest of the blog as
     filler, so a lone post in a young category still gets a full row. */
  eleventyConfig.addFilter("relatedPosts", (collection, current, limit) => {
    const max = limit || 4;
    const slug = resolveCategory(current.category).slug;
    const others = (collection || [])
      .filter(post => post.data.slug !== current.slug)
      .sort((a, b) => b.date - a.date);

    const sameCategory = others.filter(p => resolveCategory(p.data.category).slug === slug);
    const rest = others.filter(p => resolveCategory(p.data.category).slug !== slug);
    return sameCategory.concat(rest).slice(0, max);
  });

  /* ---- transitional: de-duplicate blocks the Python pipeline also emits ----
     blog_pipeline.py currently extracts the FAQ into `faq:` front matter *and*
     leaves the rendered <section class="blog-faq"> in the article body. The
     layout renders the FAQ from front matter — that is what keeps the visible
     copy and the FAQPage JSON-LD identical — so the body's copy has to go or
     the reader sees the FAQ twice.

     Delete this filter once the generator stops emitting the section; it is a
     no-op on any post that does not contain one. */
  eleventyConfig.addFilter("stripDuplicateFaq", content =>
    String(content || "").replace(/<section class="blog-faq">[\s\S]*?<\/section>/g, "")
  );

  /* ---- article meta ---- */

  /* 200 wpm over the rendered HTML, tags stripped. */
  eleventyConfig.addFilter("readingTime", content => {
    const words = String(content || "").replace(/<[^>]+>/g, " ").trim().split(/\s+/).length;
    return Math.max(1, Math.round(words / 200));
  });

  /* Accepts the Date that Eleventy builds from `date:` front matter, or a raw
     "YYYY-MM-DD" string. Returns "" rather than "Invalid Date". */
  const toDate = value => {
    if (value instanceof Date) return isNaN(value) ? null : value;
    const parsed = new Date(String(value) + (/^\d{4}-\d{2}-\d{2}$/.test(value) ? "T12:00:00Z" : ""));
    return isNaN(parsed) ? null : parsed;
  };

  eleventyConfig.addFilter("isoDate", value => {
    const date = toDate(value);
    return date ? date.toISOString().slice(0, 10) : "";
  });

  eleventyConfig.addFilter("displayDate", (value, lang) => {
    const date = toDate(value);
    if (!date) return "";
    return date.toLocaleDateString(lang === "es" ? "es-US" : "en-US", {
      year: "numeric", month: "long", day: "numeric", timeZone: "UTC"
    });
  });

  return {
    dir: {
      input: "blog-src",
      output: "_site",
      includes: "_includes",
      layouts: "_layouts",
      data: "_data"
    }
  };
};
