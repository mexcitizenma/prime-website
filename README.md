# Prime Paint & Home Services — website

Static, mobile-first site in English and Spanish. No build step, no frameworks,
no dependencies. Open `index.html` in a browser, or deploy the folder to Netlify
(the contact forms need Netlify to receive submissions — see below).

Live domain: **primeprowork.com**

## Files

| File | Purpose |
|---|---|
| `index.html` | Home — hero, services grid, why-us, process, service area, FAQ |
| `services.html` | All nine services in detail, anchored from the home page cards |
| `gallery.html` | Filterable project grid |
| `contact.html` | Contact methods + Netlify estimate-request form |
| `es/*.html` | Spanish versions of all four pages |
| `css/style.css` | Whole site's styling (navy / white / gold, mobile-first) |
| `js/main.js` | Mobile menu, gallery filter, form validation + submit, photo fallback |
| `robots.txt`, `sitemap.xml` | Search engine basics; sitemap lists all 8 URLs with hreflang |
| `images/gallery/` | Drop project photos here — see the README in that folder |

The Spanish pages share the same CSS and JS as the English ones (`../css/style.css`,
`../js/main.js`, `../images/...`), so a styling change applies to both languages.

## Contact forms (Netlify)

Both contact pages post to **Netlify Forms**:

| Page | Form name in the Netlify dashboard |
|---|---|
| `contact.html` | `estimate-request` |
| `es/contact.html` | `estimate-request-es` |

Two separate names so you can tell at a glance which language a lead came in on.

- Netlify detects the forms at deploy time from the `data-netlify="true"` markup —
  nothing to configure, but the site **must be deployed to Netlify** for
  submissions to arrive. Opening the file locally will show the error message
  instead, which is expected.
- Spam is filtered by a `bot-field` honeypot (`netlify-honeypot="bot-field"`).
- Submitting does not leave the page: JS validates, posts in the background, then
  swaps the form for an inline thank-you panel. Without JS the form posts
  normally and Netlify shows its own confirmation page.
- Turn on email notifications in **Netlify → Forms → Form notifications** so
  leads land in an inbox instead of only the dashboard.
- Call and Messenger remain the loudest buttons on the page; the form is secondary.

Spanish error and status wording lives in `data-msg-*` attributes on the Spanish
`<form>` tag — edit the text there, no JS changes needed. English uses the
defaults built into `js/main.js`.

## Language switching

Every page has an `EN | ES` switcher in the header nav that links to the same
page in the other language, plus `hreflang` tags (`en`, `es`, `x-default`) in the
`<head>` and alternates in `sitemap.xml`, so Google serves the right version to
each searcher.

## Still to do before/after launch

1. **Mailing address / ZIP.** Structured data uses Westfield, MA 01085 with
   approximate coordinates. Update to the real address, or remove the `address`
   and `geo` blocks if you would rather not publish one.
2. **Photos.** Two kinds of placeholder are on the site right now:
   - **Stock photos** on the home and services pages (hero, four service cards,
     four service blocks). These are licensed-look placeholders, not Prime Paint
     jobs — every one is marked with an `STOCK PHOTO (placeholder)` HTML comment
     right above the `<img>`. Replace them with real job photos as they come in.
   - **Gallery tiles**, which show a neutral "Photo coming soon" /
     "Foto próximamente" hatch until files land in `images/gallery/` — filenames
     are listed in that folder.

   Also add `images/prime-paint-og.jpg` (1200×630) for Facebook link previews;
   the structured data already points at it.
3. **Social proof.** No reviews or testimonials are included, and nothing claims
   years in business. Add real reviews once you have them.

## Photos and image sizes

Originals live in `images/stock/` untouched (27 MB of camera-resolution files —
never link to these directly). The site serves web-sized copies from
`images/stock/web/`, generated with macOS `sips`:

    sips -Z 1400 -s format jpeg -s formatOptions 68 "images/stock/single house.jpg" \
         --out images/stock/web/hero-house.jpg

| Web file | From | Used for |
|---|---|---|
| `hero-house.jpg` | single house.jpg | home hero, both languages |
| `exterior-painting.jpg` | blue single house.jpg | Exterior Painting card + block |
| `cabinet-painting.jpg` | kitchen cabine.jpg | Cabinet Painting card + block |
| `pressure-washing.jpg` | pressure washer.jpg | Pressure Washing card + block |
| `handyman.jpg` | handyman renovation.jpg | Handyman card + block |

`handy man repair.jpg` is not used anywhere yet — it is a window-caulking shot
that would suit the Interior Painting card if you want that slot filled.

The two portrait photos are cropped by CSS `object-position` (set inline on those
`<img>` tags) so the subject stays in frame — pressure washing at `center 69%`,
handyman at `center 43%`. Adjust those percentages if a swap changes the framing.

Keep any replacement photo under ~250 KB and around 1100–1400px on its long edge.

## Footer copyright year

The footer year is hardcoded to **2025** on all eight pages. `js/main.js` still
contains an `initYear()` helper that rewrites any element carrying a `data-year`
attribute to the current year — no element uses it now, so it does nothing. If
you ever want the year to update itself again, put the attribute back:
`<span data-year>2025</span>`.

## Business hours

Hours appear in two places and must be changed in both if they ever move:

- the visible list on `contact.html` and `es/contact.html` (12-hour, `<ul class="hours">`)
- `openingHoursSpecification` in the `HousePainter` structured data on all eight
  pages (24-hour, per day)

Current hours — Mon 8:00 AM–8:30 PM, Tue 8:00 AM–9:30 PM, Wed 8:00 AM–8:30 PM,
Thu 8:00 AM–8:30 PM, Fri 8:00 AM–7:00 PM, Sat 9:00 AM–6:00 PM, Sun 11:00 AM–5:00 PM.
All Eastern. Schema.org has no timezone field for opening hours, so the times are
published as-is and read as local to the business address (Westfield, MA).

## Local SEO already in place

- Unique title + meta description per page and per language, all naming the towns
- Canonical URLs, hreflang pairs, Open Graph and Twitter card tags
- `HousePainter` (LocalBusiness) structured data with phone, email, areas served,
  service catalog and Facebook profile — the Spanish pages reuse the same
  business `@id` with translated text, so both count as one business
- `FAQPage` on both home pages, `ItemList` of services, `ContactPage` on contact
- Town names in headings and body copy, `robots.txt` and `sitemap.xml`

Next step off-site: claim the Google Business Profile for the same name, phone
number and service area, and keep the name/phone identical everywhere.
