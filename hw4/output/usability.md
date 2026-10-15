# Usability improvements (Problem 9)

Four improvements — two on the front end, two in the agent/backend. All four are visible in the
running app.

---

## Front end 1 — "Featured This Week" shows the real products

**Before.** The home page's featured strip was a hardcoded array of four names with emoji
placeholders (👕, 🧥, 🧣) and prices typed in as strings.

**After.** `Home.tsx` calls `GET /api/products?limit=4` on mount and renders the actual
catalogue rows — real product photography from `/static/products/*.jpg`, the real name, and the
real price formatted from the DB `REAL` column. Each card is a `<Link>` into that product's
detail page, so the strip is now a shopping entry point rather than decoration.

**Why it helps.**
- *Shopper:* a photo of the garment tells you more in a half-second than the word "hoodie" and
  a clipart jacket. People buy apparel with their eyes, and the featured strip is the first
  thing on the page. Being clickable also removes a dead end — previously the only way out of
  the home page was the nav bar.
- *Business:* the hardcoded list was a correctness risk. It said `$32` and `$98` as literal
  strings, so if a price changed or a product was discontinued the home page would quietly
  advertise something untrue. Pulling from the API means the storefront's most prominent
  surface can never disagree with the catalogue — the same live-data guardrail the rest of the
  site already follows.

**Files:** `frontend/src/pages/Home.tsx`, `frontend/src/lib/api.ts`,
`backend/main.py` (`limit` parameter on `GET /api/products`).

---

## Front end 2 — Students / Alumni / Family pills are clickable, curated collections

**Before.** The hero had three `<span className="pill">` chips — Students, Alumni, Family &
Relatives. They looked like buttons and did nothing.

**After.** Each pill is a `<Link to="/products?segment=…">` into a curated slice of the
catalogue. `Products.tsx` reads the `segment` query param, swaps in that segment's heading and
blurb, shows an item count, and renders a filter bar (Everything / Students / Alumni / Family &
Relatives) so a shopper can switch collections or back out to all 102 items without losing their
place. The URL carries the filter, so a segment view is shareable and back-button-safe.

**Curation lives in the backend**, next to the data, in `SEGMENTS` in `backend/main.py`:

| Segment | What's in it | Items |
| --- | --- | --- |
| Students | Residential colleges (Branford, Saybrook, Morse, Pierson, Davenport, Hopper, Benjamin Franklin, Jonathan Edwards, Timothy Dwight, Trumbull, Berkeley), varsity "Left Chest" team gear, Boola Boola | 52 |
| Alumni | Graduate schools (Management, Law, Medicine, Engineering, Architecture, Art, Music, Nursing, Public Health, Divinity), heritage crests and vintage shields, Harvard–Yale "The Game", premium Champion / Brooks Brothers pieces | 26 |
| Family & Relatives | Yale Mom / Dad / Grandma / Grandpa / Aunt / Uncle / Brother / Cousin, and Handsome Dan bulldog graphics | 16 |

Two implementation notes worth recording, because both were wrong on the first attempt:

- Matching runs against the **product name only**, not `search_tags`. Nearly every row carries a
  generic `"college apparel"` / `"college merch"` tag, so matching tags swept 99 of 102 products
  into "Students". Names in this catalogue are deliberate (`Yale Mom Hoodie`,
  `School Of Medicine 1 4 Zip`); the tags are not.
- Matching is **word-bounded** (`\bbrother\b`). A plain substring match put *Brooks **Brothers**
  Bomber Jacket* in the family-gift segment.

Segments deliberately overlap a little (a Benjamin Franklin quarter-zip is plausible for a
student and an alum). They're a merchandising lens, not a partition.

**Why it helps.**
- *Shopper:* 102 undifferentiated products is a wall. These three audiences want genuinely
  different things — a sophomore wants their residential college crewneck, a visiting grandmother
  wants a "Yale Grandma" hoodie, and neither wants to scroll past the other's items. The pills
  already described those audiences; now they act on it.
- *Business:* this is the cheapest kind of merchandising. The home page already segments
  visitors in its own copy ("students… alumni… family and relatives"), and acting on that
  self-identification at the first click is the highest-intent moment in the session. Because
  the rules live server-side in one dict, merchandising can be retuned without a frontend
  deploy, and the chosen segment is in the URL so it's measurable in analytics.

**Files:** `backend/main.py` (`SEGMENTS`, `row_matches_segment()`, `GET /api/segments`,
`segment`/`limit` params on `GET /api/products`), `frontend/src/pages/Home.tsx`,
`frontend/src/pages/Products.tsx`, `frontend/src/lib/api.ts`, `frontend/src/index.css`.

---

## Agent 1 — stock reads like a person, not a symbol key

**Before.** Asked about sizes, the agent produced a Markdown bullet list with an emoji status
key. The chat panel renders plain text, so it landed on the page as literal clutter:

```
- **S** — 8 in stock ✅ - **L** — Out of stock ❌ - **XL** — 2 in stock ✅
```

Unreadable, and the raw counts (`8`, `20`) are inventory data a shopper has no use for.

**After.** The phrasing is generated in the backend from the live quantities, so the agent is
handed words instead of having to invent a notation:

- `SizeStock.availability` — a phrase per size, from `_availability_phrase(quantity)`:
  `"sold out"` (0), `"last one left"` (1), `"only N left"` (≤ 3), `"in stock"` (> 3).
- `ProductInventory.stock_summary` — one ready-to-say sentence covering every size, e.g.
  *"Available in XS, S, M, XL and XXL. Running low on XL (only 2 left). Sold out in L."*

`prompt.md` gained two rules: a **"How your replies are rendered"** section (the panel is plain
text — no asterisks, bullets, headers or backticks) and a **"Saying stock out loud"** section
(reuse `stock_summary`, answer in sentences, quote an exact number only when it's useful).

Live result for the same question:

> Good news — XS, S, M, and XXL all have plenty in stock. XL is running low with only 2 left.
> L is sold out for now, so if that's your size, grab an XL quick before those go too!

**Why it helps.**
- *Shopper:* one sentence, scannable, no legend to decode, and it reads the same whether you're
  on a phone or a laptop. Out-of-stock sizes are still stated plainly — that rule didn't change.
- *Business:* "only 2 left" is a genuine scarcity signal that a bare `2` buries, and it's
  honest because the threshold is computed from the real quantity rather than improvised by the
  model. More importantly, phrasing stock in Python instead of in the prompt means it's
  deterministic: the agent can't drift into a new format next week, and exact inventory depth
  (`20 units of XL`) isn't volunteered to customers or competitors.

**Files:** `backend/models.py` (`SizeStock.availability`, `ProductInventory.stock_summary`),
`backend/tools.py` (`_availability_phrase()`, `_join_sizes()`, `_stock_summary()`),
`backend/prompt/prompt.md`.

---

## Agent 2 — the assistant is Handsome Dan

**Before.** "Campus Customs Assistant" — accurate, forgettable, indistinguishable from the
chat widget on any other store.

**After.** The assistant is **Handsome Dan**, Yale's bulldog mascot since 1889. This is a real
persona, not just a renamed header:

- `prompt.md` opens by establishing the character and instructs him to introduce himself by
  name, and a rewritten **Tone** section licenses humour — dog jokes, mascot swagger, a
  professional opinion of Harvard — with hard limits: *one light touch per reply at most*,
  **helpfulness outranks comedy**, never joke about a customer's body, size or money, and drop
  the humour entirely if the shopper is frustrated or something is sold out.
- The widget header shows `🐶 Handsome Dan` with "Campus Customs shopping assistant" as a
  subtitle, the greeting is in his voice, the input placeholder reads "Ask Handsome Dan about a
  product…", the pending state says "Sniffing around…", and the toggle's `aria-label` names him
  for screen-reader users.

Live result:

> Woof! I'm Handsome Dan — the one, the only, Yale's official bulldog mascot since 1889! I've
> been patrolling this campus longer than most of the buildings…

**Why it helps.**
- *Shopper:* a named character sets expectations — people ask a mascot for a recommendation in a
  way they don't ask "Assistant", and the warmth makes the widget feel like part of the store
  instead of a bolted-on support bot. The subtitle keeps it honest about what he actually does.
- *Business:* Handsome Dan is the single most recognisable piece of Yale iconography and already
  appears on four products in this catalogue. Borrowing him costs nothing and makes the chat
  memorable and on-brand. The guardrails matter as much as the persona: humour is explicitly
  subordinated to accuracy, so the brand upside doesn't come at the cost of a shopper getting a
  joke instead of a straight answer about stock.

**Files:** `backend/prompt/prompt.md`, `frontend/src/components/ChatWidget.tsx`,
`frontend/src/index.css`, `frontend/src/pages/Home.tsx`.

---

## Verification

All four were checked in the running app, not just in code:

- `GET /api/segments` returns the three segments; `?segment=students|alumni|family` returns
  52 / 26 / 16 products, each list spot-checked by name for false positives.
- Home page screenshot shows four real product photographs in "Featured This Week".
- Clicked the "Family & Relatives" pill in the hero → landed on `/products?segment=family`,
  heading "For Family & Relatives", 16 items, filter bar with Family active, grid showing the
  Yale Mom / Dad / Grandparent and vintage-bulldog pieces.
- Asked the live widget as a guest "What sizes are in stock for the Boola Boola T Shirt?" →
  plain-prose answer, no bullets, no ✅/❌, with L correctly reported as sold out and XL flagged
  as low — matching the database.
- Asked "Who am I talking to?" → full Handsome Dan introduction.
- Product cards in chat and the single-item detail page (Problems 3 and 7) still work; no
  browser console errors.
