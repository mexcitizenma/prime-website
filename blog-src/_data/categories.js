/* ---------------------------------------------------------------------------
   Blog category registry.

   One entry per `category` value used in topics.json. Everything the blog
   needs to render a category — its bilingual label, its short blurb and the
   thumbnail used in card grids — lives here, so a new category is a single
   edit rather than a hunt through templates.

   `slug` doubles as the URL segment: /blog/category/<slug>/ (EN) and
   /es/blog/categoria/<slug>/ (ES).
--------------------------------------------------------------------------- */

module.exports = [
  {
    slug: "interior-painting",
    en: { label: "Interior Painting", blurb: "Color, prep and finish advice for the rooms you live in." },
    es: { label: "Pintura Interior", blurb: "Color, preparación y acabados para los cuartos donde vive." },
    image: "images/stock/web/interior-painting.jpg"
  },
  {
    slug: "exterior-painting",
    en: { label: "Exterior Painting", blurb: "Protecting siding and trim through the New England seasons." },
    es: { label: "Pintura Exterior", blurb: "Cómo proteger el siding y los marcos en el clima de Nueva Inglaterra." },
    image: "images/stock/web/exterior-painting.jpg"
  },
  {
    slug: "cabinet-painting",
    en: { label: "Cabinet Painting", blurb: "Kitchen refreshes that cost far less than new cabinetry." },
    es: { label: "Pintura de Gabinetes", blurb: "Renovar la cocina por mucho menos que cambiar los gabinetes." },
    image: "images/stock/web/cabinet-painting.jpg"
  },
  {
    slug: "epoxy-floors",
    en: { label: "Epoxy Floors", blurb: "Garage and basement floors built for salt, snow and traffic." },
    es: { label: "Pisos de Epoxi", blurb: "Pisos de garaje y sótano que aguantan sal, nieve y tráfico." },
    image: "images/stock/web/epoxy-floors.jpg"
  },
  {
    slug: "laminate-flooring",
    en: { label: "Laminate Flooring", blurb: "Choosing, installing and caring for laminate and LVP." },
    es: { label: "Pisos Laminados", blurb: "Cómo elegir, instalar y cuidar pisos laminados y LVP." },
    image: "images/stock/web/laminate-flooring.jpg"
  },
  {
    slug: "pressure-washing",
    en: { label: "Pressure Washing", blurb: "Getting driveways, decks and walkways clean without damage." },
    es: { label: "Lavado a Presión", blurb: "Limpiar entradas, terrazas y aceras sin causar daño." },
    image: "images/stock/web/pressure-washing.jpg"
  },
  {
    slug: "siding-cleaning",
    en: { label: "Siding Cleaning", blurb: "Removing mildew, algae and winter grime from your siding." },
    es: { label: "Limpieza de Siding", blurb: "Quitar moho, algas y suciedad del invierno de su siding." },
    image: "images/stock/web/siding-cleaning.jpg"
  },
  {
    slug: "fence",
    en: { label: "Fences & Decks", blurb: "Staining, sealing and repairing outdoor wood that takes a beating." },
    es: { label: "Cercas y Terrazas", blurb: "Teñir, sellar y reparar la madera exterior que más sufre." },
    image: "images/stock/deck-patio/IMG_2265.JPG"
  },
  {
    slug: "handyman",
    en: { label: "Handyman & Repairs", blurb: "The small fixes that keep a house from turning into a big job." },
    es: { label: "Reparaciones y Handyman", blurb: "Los arreglos pequeños que evitan trabajos grandes después." },
    image: "images/stock/web/handyman.jpg"
  },
  {
    slug: "general",
    en: { label: "Home Care Tips", blurb: "Seasonal checklists and planning advice for Western MA homes." },
    es: { label: "Consejos para el Hogar", blurb: "Listas por temporada y consejos de planeación para su casa." },
    image: "images/stock/web/hero-crew-exterior.jpg"
  }
];
