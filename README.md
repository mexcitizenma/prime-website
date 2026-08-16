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
| `index.html` (quick form under the hero) | `quick-estimate` |
| `es/index.html` (quick form under the hero) | `quick-estimate-es` |
| `contact.html` | `estimate-request` |
| `es/contact.html` | `estimate-request-es` |

Four separate names so you can tell at a glance which page and which language a
lead came in on. All four use the same markup pattern and the same JS handler in
`js/main.js` — a form is wired up automatically if it has `data-netlify`, a
`.form-status` inside it and a `data-thanks="<id>"` pointing at its thank-you
panel. The home-page quick form requires name + phone; the contact form accepts
a phone **or** an email.

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

## Home page section order

1. Hero (photo + CTAs)
2. **Quick estimate form** — `quick-estimate`, card style on the alt background
3. Services grid (photo cards)
4. **Why Homeowners Choose Prime Paint & Home Services** — six value tiles
5. How it works (four steps)
6. Service area (navy band with town chips)
7. FAQ
8. **Towns We Serve in Western Massachusetts** — explicit town list for local SEO
9. Closing CTA band

Sections 6 and 8 both cover the service area — see the note at the end of this
file.

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

Originals live in `images/stock/<service>/` at camera resolution — never link to
them directly. The site serves resized copies from `images/stock/web/` (service
and hero photos) and `images/gallery/` (gallery tiles), generated with `sips`:

    # keep the whole frame (landscape sources)
    sips -Z 1100 -s format jpeg -s formatOptions 68 "images/stock/siding/Siding.JPG" \
         --out images/stock/web/siding-cleaning.jpg

    # crop a portrait source to the tile ratio (4:3 gallery, 16:9 service block)
    sips --resampleWidth 1100 "images/stock/cabinet-painting/IMG_3463.JPG" --out /tmp/t.jpg
    sips -c 825 1100 -s format jpeg -s formatOptions 68 /tmp/t.jpg \
         --out images/gallery/cabinets-vanity.jpg

Gallery tiles are 4:3 (1100×825), service-block photos 16:9 (1100×619), card
photos 16:10. Cropping to the target ratio beats letting CSS crop a portrait
source, which throws away half the frame.

### Comment conventions

Two markers appear above `<img>` tags and they mean opposite things:

- `<!-- REAL JOB PHOTO -->` — actual Prime Paint work. Leave it alone.
- `<!-- STOCK PHOTO (placeholder) — replace with a real Prime Paint job photo -->`
  — licensed stock standing in until a real photo exists.

Only two stock photos are left on the site: pressure washing and handyman, on
the home and services pages.

### Still missing a photo

Gallery tiles awaiting a file (they show the hatched "Photo coming soon" tile
until one appears — no markup change needed, just drop the file in):

- `epoxy-basement.jpg`
- `exterior-deck-stain.jpg`
- `fence-stain.jpg`
- `pressure-wash-driveway.jpg`
- `siding-clean-before-after.jpg`
- `tv-mount.jpg`

On the services page, **Fence Painting** is the only block still text-only —
there is no fence photo in `images/stock/`.

`images/stock/crew-team/` and `images/stock/general/` hold the crew and personal
photos; only the crew exterior shot is in use (hero slideshow). See the notes at
the end of this file.

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

## Known overlaps worth a decision

- **Service area appears twice** on the home page: the navy band mid-page and the
  explicit town list above the footer. Both list the same seven towns. Keeping
  both is normal for local SEO, but the navy band could become a one-line
  mention instead.
- The hero badge row (Free estimates / Locally owned / Fast response / Clean,
  tidy work) still echoes four of the six "Why Homeowners Choose…" tiles. That
  repetition is mild and fairly standard — the badges are a glance, the tiles the
  explanation.

## Claims on the site

Nothing claims years in business, and **no insurance claim appears anywhere** —
"Fully Insured" was removed at the owner's instruction because the business does
not currently carry a policy. If that changes, add it back as a seventh value
tile on the home page, in both languages.
