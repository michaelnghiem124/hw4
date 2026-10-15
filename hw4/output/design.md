# Design (Problem 10)

The brief: make the site feel like a real Campus Customs storefront, blending Yale Club of New
York City's cinematic movement with a retail sensibility borrowed from J.Press. What follows is
what changed and why each change should help a shopper stay and buy.

One constraint shaped everything: **nothing in `data/` is ever committed**, and there's no
image-generation tool in this setup. So no new binary art was added to the repo. Every "big
picture" moment is **composed at runtime from the 102 real catalogue photographs**; the crest and
pennant are **hand-drawn SVG** in `components/Heraldry.tsx`; and the one real photograph on the
site — Handsome Dan — is served through the same `/static` mount the product images already use.
The site looks art-directed while the repo stays clean.

---

## 1. A type and colour system instead of defaults

**Before.** System sans-serif throughout, a coral `#f04f36` accent, rounded 8px cards — generic
SaaS, not a clothier.

**After.** Three typefaces with distinct jobs: **Bodoni Moda** (display headlines — the didone
contrast that reads as heritage), **Oswald** (condensed uppercase labels, eyebrows, nav, buttons
— the wide-tracked rail type both reference sites use), **Jost** (body). Palette: Yale blue
`#00356b` with two darker steps for depth, **burgundy `#56112A`** lifted from J.Press, **brass
`#c8a951`** for rules and accents, and a warm **paper `#faf8f3`** ground instead of white.
Corner radius dropped to `2px`.

**Why it helps.** For apparel, perceived quality *is* the product page. A storefront that looks
like a catalogue rather than a dashboard raises what a visitor expects to pay and how long
they'll browse before deciding. The paper ground also makes garment photography — mostly on
white backgrounds — sit in a frame instead of bleeding into the page.

---

## 2. A cinematic hero built from real inventory

**Before.** A flat blue box with a headline and three decorative chips.

**After.** `HeroWall` tiles 18 live catalogue images into six columns, which drift slowly under a
`hero-drift` Ken Burns keyframe (46s, alternating) behind a Yale-blue veil and a 2px blur. Over
it: the `CrestMark`, an "New Haven, Connecticut" eyebrow, **"Ivy Heritage, Worn Well."**, two
CTAs, the three segment pills, and an animated scroll cue.

**Why it helps.** This is the Yale Club's moving banner achieved without a video file — and it's
better for retail, because the motion is made of things you can actually buy. It communicates
catalogue depth in the first second ("this place has a lot of Yale stuff") and the blur keeps it
atmosphere rather than competition for the headline. The scroll cue exists because a full-bleed
hero can read as the whole page; it tells people there's more below.

---

## 3. Scrolling becomes the experience: alternating bands

**Before.** One page, one background colour, three stacked sections.

**After.** The home page is six **bands** that alternate ground — hero → dark marquee → paper
→ blue editorial → paper featured → blue Handsome Dan band → footer. The `Marquee` component
duplicates the product track and translates it `-50%` over 60s for a seamless infinite scroll
(paused on hover, each tile a link). Editorial bands alternate image-left / image-right via
`.editorial-reverse`. Everything enters on an IntersectionObserver `Reveal` that fades and lifts
content once, then unobserves itself.

**Why it helps.** This is the "different buns as you scroll" the brief asked for. Alternating
grounds give the page rhythm and a sense of progress, which is what keeps people scrolling past
the fold; the reveal animations reward that scrolling instead of dumping everything at once. The
marquee specifically is a low-commitment browse surface — you see twenty products without
choosing a category, and any one of them is one click from a detail page.

---

## 4. A masthead and footer that frame the store

**After.** A two-tier header: a burgundy service rail ("Complimentary shipping over $75 ·
Shipped from New Haven") above a brand bar with the crest, wordmark, and "Ivy Heritage" tagline.
It is **transparent over the home hero** (with a top-down scrim so the wordmark stays legible on
whatever photo tiles behind it) and solidifies to a blurred blue bar the moment you scroll,
shrinking 76px → 62px. Nav links get a brass underline that scales in on hover/active. A new
footer carries the crest, "New Haven · Worn Well", four link columns, and the legal line.

**Why it helps.** The service rail puts the two facts that most often decide a cart — shipping
threshold and where it ships from — above everything else, and disappears once you're shopping
so it doesn't eat vertical space. The sticky, shrinking header keeps navigation one click away
through a long scroll. A real footer signals a real store; its absence is one of the fastest
trust-killers on an unfamiliar site.

---

## 5. Calmer, more confident shopping surfaces

**Products.** Section head with a brass rule and "The Collection" eyebrow, a heading that reacts
to the active segment, and a quiet `.result-count` line instead of three competing subtitles.
Images lazy-load.

**Product detail.** A `← All products` back link, colours rendered as actual **swatch dots**, and
size pills that show just the letter (count moved to the `title` attribute) — with sold-out sizes
struck through. Below them a plain-English `size-note`: *"Every size is in stock right now."* or
*"2 sizes are sold out — struck through above. Ask Handsome Dan in the chat for exact counts."*

**Why it helps.** On the grid, less chrome per card means more products visible per screen and a
faster scan. On the detail page, size availability is the single most common reason someone
bounces; a legible pill row plus one sentence answers it without making anyone count. The note
also hands the shopper to the chat at exactly the moment they have a question the page can't
answer — which is the cheapest path from browsing to a conversion.

---

## 6. Handsome Dan gets a face — a real one

**Before.** A 🐶 emoji on the chat toggle and in the panel header.

**After.** An actual photograph of Handsome Dan in a Yale sweater, used four ways from one file
via `BulldogPhoto`: cropped to his face for the round chat toggle and the 34px avatar in the
panel header (`transform-origin` + `scale`, so no second image is needed), and full-frame in tall
editorial panels on the home and about pages, where a slow 26s push-in keeps the band from
sitting still. The crest, still vector, carries the nav and footer.

**Why it helps.** The chat is this store's real advantage, and a live photo of the actual mascot
is a far stronger invitation to open it than an emoji that renders differently on every device.
The editorial panels matter more: the brief asked for lifestyle imagery, and until now the only
photography on the site was garments on blank backgrounds. One picture of a dog in a sweater in
a wood-panelled room does more to establish what "Ivy heritage" means here than any amount of
copy — it tells a visitor what world the clothes belong to, which is the thing that makes someone
browse rather than bounce.

---

## 7. Motion has an off switch

Every animation on the site — hero drift, marquee, reveals, scroll cue, chat panel entrance, the
push-in on Dan's portrait — is disabled under `@media (prefers-reduced-motion: reduce)`, and
`.reveal` elements resolve to visible rather than staying hidden.

**Why it helps.** Motion sickness and vestibular disorders are common enough that "ambitious
animation" and "unusable for some customers" are the same decision unless you build the escape
hatch. Nothing is behind the animation — the content is identical either way.

---

## Files

**New:** `components/Heraldry.tsx` (CrestMark, BulldogPhoto, PennantMark),
`components/Motion.tsx` (Reveal, Marquee, HeroWall), `components/Footer.tsx`.
**Rewritten:** `index.css` (design tokens, bands, hero, marquee, editorial, reveal, motion
queries), `components/NavBar.tsx` + `NavBar.css`, `pages/Home.tsx`, `pages/AboutUs.tsx`,
`index.html` (font links, title, meta description).
**Edited:** `pages/Products.tsx`, `pages/ProductDetail.tsx`, `pages/Login.tsx`,
`pages/CreateAccount.tsx`, `components/ChatWidget.tsx`, `App.tsx`.

## Verification

`npx tsc --noEmit` clean; no browser console errors. Checked live at 1280px — home (all six
bands, drifting hero, running marquee, segment cards, featured strip, Dan band, footer),
`/products` (102 items, filter bar), `/products/2025-yale-vs-harvard-t-shirt` (image, $32.00,
swatches, six size pills, "Every size is in stock right now."), `/about`, `/login` — and at 390px,
where pills, hero, and editorial bands stack to one column. Asked the live widget as a guest
*"What sizes are in stock for the Boola Boola T Shirt?"* and got plain prose plus a correctly
rendered product card, confirming the restyle didn't disturb Problems 5–9. All reveal elements
were confirmed to reach `.is-visible`, and the reduced-motion block confirmed to disable every
loop.
