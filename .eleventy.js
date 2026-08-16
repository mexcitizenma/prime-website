module.exports = function(eleventyConfig) {
  eleventyConfig.addPassthroughCopy("css");
  eleventyConfig.addPassthroughCopy("js");
  eleventyConfig.addPassthroughCopy("images");

  eleventyConfig.addCollection("blog_en", function(collectionApi) {
    return collectionApi.getFilteredByGlob("blog-src/en/*.njk");
  });

  eleventyConfig.addCollection("blog_es", function(collectionApi) {
    return collectionApi.getFilteredByGlob("blog-src/es/*.njk").filter(
      item => item.data.type === "post"
    );
  });

  return {
    dir: {
      input: "blog-src",
      output: "_site",
      includes: "_includes",
      layouts: "_layouts"
    }
  };
};
