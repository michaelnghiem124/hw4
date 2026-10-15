# Campus Customs — Yale merch storefront with an AI shopping assistant

A React + Vite storefront over a 102-product Yale apparel catalogue, with **Handsome Dan**, a
PydanticAI agent behind FastAPI who answers questions about products, sizes, prices and live
stock — and renders the matching products as clickable cards inside the chat.

Built for MGT 409 "AI Foundations for Managers", Homework 4.

---

## The local-only data pack (not in git)

**This repository does not contain the database or the product images, and never will.**

The app needs a `data/` folder at `hw4/data/`:

```
hw4/data/
├── campus_customs.db          # catalogue, inventory, users, chat_messages
├── products/                  # 102 product photographs referenced by the catalogue
└── Handsome Dan.jpeg          # the mascot portrait used in the UI
```

It is excluded by `.gitignore` for two reasons:

- **`campus_customs.db` holds real personal data** — user accounts with real email addresses
  (including the course instructor's) and salted `pbkdf2_sha256` password hashes. None of that
  belongs on a public repo.
- **`products/` is course-supplied photography** — assets to run the assignment against, not
  mine to redistribute.

Drop the provided data pack in at `hw4/data/` before starting the backend. Without it the API
returns empty collections and the site renders empty frames rather than crashing — but nothing
useful will load.

---

## Running it

You need **Python 3.11+**, **Node 18+**, and an **Anthropic API key**.

### 1. Configure the API key

```bash
cd hw4
cp .env.example .env     # then edit .env and set ANTHROPIC_API_KEY
```

The backend reads `~/.config/mgt409/.env` first, then a local `.env`, without overriding
anything already exported in your shell — so either location works. `.env` is gitignored;
`.env.example` holds placeholders only.

### 2. Backend — FastAPI on port 8000

```bash
cd hw4/backend
python3 -m venv .venv
.venv/bin/pip install -r ../requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
```

Run it **from `hw4/backend/`**. `agent.py` resolves `prompts/prompt.md` and
`../data/campus_customs.db` relative to its own location, and the plain-module imports
(`from agent import run_chat`) assume `backend/` is the import root.

### 3. Frontend — Vite on port 5174

In a second terminal:

```bash
cd hw4/frontend
npm install
npm run dev
```

Open the URL Vite prints (http://localhost:5174). The chat widget is the bulldog button in the
bottom-right corner, on every page.

---

## Layout

```
hw4/
├── AI_prompts.md              every prompt used to build this, verbatim, with outcomes
├── requirements.txt           Python dependencies
├── .env.example               placeholders only — copy to .env
├── .gitignore
├── README.md
├── frontend/                  Vite + React + TypeScript app
├── backend/
│   ├── main.py                FastAPI app — products, auth, chat, static images
│   ├── agent.py               PydanticAI agent entry point and wiring
│   ├── models.py              Pydantic / PydanticAI structured types
│   ├── tools.py               the four read-only tools the agent can call
│   ├── audit.py               append-only audit-trail writer
│   ├── security.py            session tokens, rate limiting, reply scrubbing
│   └── prompts/
│       └── prompt.md          the system prompt
└── output/
    ├── harness.md             how the whole system works — start here
    ├── design.md              visual design system
    ├── usability.md           usability pass
    ├── app_check.html         three checks of the running app, with screenshots
    ├── app_check_images/      screenshots linked from app_check.html
    └── audit_trail.json       append-only log of agent-loop activity (JSON Lines)
```

The agent itself is four files under `backend/`: `prompts/prompt.md`, `agent.py`, `tools.py`
and `models.py`.

---

## The agent in one paragraph

Four **read-only** tools — `search_products`, `get_product_inventory`, `get_page_product`,
`list_garment_types` — each opening its own `mode=ro` SQLite connection, so there is no code
path by which the agent can write to the database. It knows who it is talking to (resolved
server-side from an HMAC-signed session token, never from a client-supplied id) and what page is
open, so "do you have this in pink?" resolves to the product actually on screen. Every claim
about a price or a stock level comes from a live query; the API layer re-reads every displayed
field from the catalogue before responding, so a hallucinated product id renders nothing. Each
turn runs under a soft budget of 8 tool calls, hard ceilings of 12 model requests / 12 tool
calls / 60k tokens, and a 45-second timeout, and writes itself to an append-only audit trail.

**[`output/harness.md`](output/harness.md) is the full control summary** — model fields and why
they are shaped that way, tools and abilities, safety rules, and every limit with its value.

---

## Security notes

- Passwords: `PBKDF2-HMAC-SHA256`, 120,000 iterations, salted, compared in constant time.
- Chat sessions: HMAC-SHA256 bearer tokens (`user_id.expiry.signature`), verified with
  `secrets.compare_digest`. Identity is proved, never claimed — a client-supplied `user_id` is
  ignored.
- The signing key comes from `CAMPUS_CUSTOMS_SECRET`, or is generated on first run into
  `backend/.session_secret` (mode 0600, gitignored).
- Outbound replies are scrubbed for emails, card numbers and password hashes before being sent
  or saved; the audit trail is redacted on the way in.
- `/api/chat` is rate-limited to 20 requests per 5 minutes per client, with a 1,000-character
  message cap.

This is coursework, not a production deployment: it runs over HTTP on localhost, and the bearer
token is kept in `localStorage`. A real deployment would need HTTPS and an httpOnly cookie.
