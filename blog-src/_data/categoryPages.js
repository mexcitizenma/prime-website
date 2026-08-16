/* ---------------------------------------------------------------------------
   Which category pages should exist, per language.

   Eleventy resolves `pagination.data` from the data cascade, which runs before
   collections exist — so a paginated template cannot ask "does this category
   have any posts?". This file answers that by reading the post files off disk
   itself, which is safe because generate_post.py is the only thing that writes
   them and it always writes the same front matter block.

   A category with no posts in a language gets no page in that language: an
   empty listing is thin content and a dead link from the sidebar.
--------------------------------------------------------------------------- */

const fs = require("fs");
const path = require("path");
const categories = require("./categories.js");

const KNOWN = new Set(categories.map(c => c.slug));

/* Reads one scalar out of a YAML front matter block. The generator quotes its
   values (`type: "post"`), but hand-written front matter may not, so accept
   either form. */
function scalar(front, key) {
  const match = front.match(new RegExp(`^${key}:[ \\t]*(.*)$`, "m"));
  if (!match) return null;
  return match[1].trim().replace(/^["'](.*)["']$/, "$1");
}

function countPosts(dir) {
  const counts = {};
  let files = [];
  try {
    files = fs.readdirSync(dir).filter(name => name.endsWith(".njk"));
  } catch {
    return counts; // language folder not created yet
  }
  for (const name of files) {
    const front = fs.readFileSync(path.join(dir, name), "utf8").split(/^---\s*$/m)[1];
    if (!front || scalar(front, "type") !== "post") continue;
    const category = scalar(front, "category");
    const slug = KNOWN.has(category) ? category : "general";
    counts[slug] = (counts[slug] || 0) + 1;
  }
  return counts;
}

module.exports = function () {
  const root = path.join(__dirname, "..");
  const counts = {
    en: countPosts(path.join(root, "en")),
    es: countPosts(path.join(root, "es"))
  };

  const build = lang =>
    categories
      .filter(cat => counts[lang][cat.slug])
      .map(cat => ({
        slug: cat.slug,
        label: cat[lang].label,
        blurb: cat[lang].blurb,
        image: cat.image,
        count: counts[lang][cat.slug],
        has_en: Boolean(counts.en[cat.slug]),
        has_es: Boolean(counts.es[cat.slug])
      }));

  return { en: build("en"), es: build("es") };
};
