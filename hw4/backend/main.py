import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

import audit
import security
from agent import AgentRunError, run_chat
from models import (
    MAX_HISTORY_TURNS,
    MAX_MESSAGE_CHARS,
    ChatHistoryResponse,
    ChatProductCard,
    ChatRequest,
    ChatResponse,
    ChatTurn,
    CustomerContext,
    ProductRef,
    StoredChatTurn,
)

HISTORY_TURN_LIMIT = 40

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 120_000

app = FastAPI(title="Campus Customs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(DATA_DIR)), name="static")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def catalogue_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "price": row["price"],
        "image_url": f"/static/{row['image_file_path']}",
    }


# Audience segments shown on the home page. Curated here, next to the data, so the
# browser never hardcodes which products belong to which shopper.
SEGMENTS: dict[str, dict] = {
    "students": {
        "label": "Students",
        "blurb": "Residential college gear, varsity team pride, and everyday tees and "
        "hoodies that survive a New Haven winter.",
        "keywords": [
            "college",
            "left chest",
            "sports",
            "branford",
            "saybrook",
            "morse",
            "berkeley",
            "trumbull",
            "pierson",
            "davenport",
            "hopper",
            "benjamin franklin",
            "jonathan edwards",
            "timothy dwight",
            "boola",
        ],
    },
    "alumni": {
        "label": "Alumni",
        "blurb": "Heritage crests, vintage shields, graduate-school quarter-zips, and "
        "The Game — the pieces that say you were here.",
        "keywords": [
            "school of",
            "divinity",
            "law school",
            "harvard",
            "vintage",
            "crest",
            "shield",
            "brooks brothers",
            "champion",
            "reverse weave",
            "bomber",
            "fleece sweater",
            "arched yale",
        ],
    },
    "family": {
        "label": "Family & Relatives",
        "blurb": "Yale Mom, Dad, Grandparent and sibling classics, plus Handsome Dan "
        "bulldog graphics that make easy gifts.",
        "keywords": [
            "mom",
            "dad",
            "grandma",
            "grandpa",
            "aunt",
            "uncle",
            "brother",
            "cousin",
            "bulldog",
        ],
    },
}


def row_matches_segment(row: sqlite3.Row, keywords: list[str]) -> bool:
    """Curation is keyword-based because `garment_type` alone can't express intent.

    The catalogue has no audience column, so a segment is a hand-picked keyword set
    matched case-insensitively against the product *name*. Names are deliberate
    (`Yale Mom Hoodie`, `School Of Medicine 1 4 Zip`); `search_tags` are not — nearly
    every row carries a generic "college apparel" tag, which would sweep the whole
    catalogue into one segment. Matching is word-bounded so "Brooks Brothers" doesn't
    land in the "brother" gift segment.
    """
    haystack = row["name"].lower()
    return any(
        re.search(rf"\b{re.escape(keyword)}\b", haystack) for keyword in keywords
    )


@app.get("/api/segments")
def list_segments():
    return [
        {"id": seg_id, "label": seg["label"], "blurb": seg["blurb"]}
        for seg_id, seg in SEGMENTS.items()
    ]


@app.get("/api/products")
def list_products(segment: str | None = None, limit: int | None = None):
    if segment is not None and segment not in SEGMENTS:
        raise HTTPException(status_code=404, detail="Unknown segment")

    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        if segment is not None:
            keywords = SEGMENTS[segment]["keywords"]
            rows = [row for row in rows if row_matches_segment(row, keywords)]
        if limit is not None:
            rows = rows[:limit]
        return [catalogue_row_to_dict(row) for row in rows]
    finally:
        conn.close()


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")

        product = catalogue_row_to_dict(row)
        product["search_tags"] = json.loads(row["search_tags"])

        sizes = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY "
            "CASE size WHEN 'XS' THEN 1 WHEN 'S' THEN 2 WHEN 'M' THEN 3 "
            "WHEN 'L' THEN 4 WHEN 'XL' THEN 5 WHEN 'XXL' THEN 6 END",
            (product_id,),
        ).fetchall()
        product["sizes"] = [
            {"size": s["size"], "quantity": s["quantity"]} for s in sizes
        ]
        return product
    finally:
        conn.close()


# ---- Auth ----


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), HASH_ITERATIONS
    ).hex()
    return f"{HASH_ALGORITHM}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    parts = stored_hash.split("$")
    if len(parts) != 3 or parts[0] != HASH_ALGORITHM:
        return False
    _, salt, expected_digest = parts
    computed_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), HASH_ITERATIONS
    ).hex()
    return hmac.compare_digest(computed_digest, expected_digest)


def user_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "name": row["name"],
        "email": row["email"],
    }


def authenticated_response(row: sqlite3.Row) -> dict:
    """The user plus a signed session token.

    The token is the only thing that later proves who is chatting — the `id`
    field is for display, and the chat endpoints deliberately ignore any
    user_id a client sends.
    """
    return {**user_row_to_dict(row), "token": security.issue_session_token(row["id"])}


def require_user_id(authorization: str | None) -> int:
    """Resolve the caller from their Bearer token, or refuse to serve them."""
    user_id = security.verify_session_token(security.bearer_token(authorization))
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sign in again to continue.")
    return user_id


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/api/auth/signup", status_code=201)
def signup(payload: SignupRequest):
    if not payload.password:
        raise HTTPException(status_code=400, detail="Password is required")
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (payload.email,)
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=409, detail="An account with this email already exists")

        password_hash = hash_password(payload.password)
        full_name = f"{payload.first_name} {payload.last_name}"
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (full_name, payload.email, password_hash, payload.first_name, payload.last_name, created_at),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return authenticated_response(row)
    finally:
        conn.close()


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (payload.email,)
        ).fetchone()
        if row is None or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return authenticated_response(row)
    finally:
        conn.close()


# ---- Chat ----


def build_product_cards(refs: list[ProductRef]) -> list[ChatProductCard]:
    """Turn the product_ids the agent named into renderable cards.

    Only the product_id is taken from the agent — name, price, image, and
    stock are re-read from the catalogue here. A product_id the agent made up
    simply has no row and is dropped, so the page never renders a fake card.
    """
    cards: list[ChatProductCard] = []
    conn = get_connection()
    try:
        for ref in refs:
            row = conn.execute(
                "SELECT * FROM catalogue WHERE product_id = ?", (ref.product_id,)
            ).fetchone()
            if row is None:
                continue
            total_stock = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) AS total FROM inventory WHERE product_id = ?",
                (ref.product_id,),
            ).fetchone()["total"]
            product = catalogue_row_to_dict(row)
            cards.append(
                ChatProductCard(
                    product_id=product["product_id"],
                    name=product["name"],
                    garment_type=product["garment_type"],
                    description=product["description"],
                    price=product["price"],
                    image_url=product["image_url"],
                    in_stock=total_stock > 0,
                )
            )
        return cards
    finally:
        conn.close()


def load_customer_context(user_id: int) -> CustomerContext | None:
    """Resolve the signed-in shopper from the DB. Unknown id -> treated as a guest."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return CustomerContext(user_id=row["id"], name=row["name"], email=row["email"])
    finally:
        conn.close()


def load_stored_history(user_id: int) -> list[StoredChatTurn]:
    """Read a signed-in shopper's saved turns back out of `chat_messages`.

    Only the product *ids* are kept from what was stored; the card fields are
    rebuilt from the catalogue so a replayed conversation shows today's prices
    and stock rather than whatever they were on the day it was saved.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT role, content, products_json FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, HISTORY_TURN_LIMIT),
        ).fetchall()
    finally:
        conn.close()

    turns: list[StoredChatTurn] = []
    for row in reversed(rows):
        refs: list[ProductRef] = []
        if row["products_json"]:
            for item in json.loads(row["products_json"]):
                product_id = item.get("product_id")
                if product_id:
                    refs.append(ProductRef(product_id=product_id, name="", price=0.0))
        turns.append(
            StoredChatTurn(
                role=row["role"], content=row["content"], products=build_product_cards(refs)
            )
        )
    return turns


def save_chat_message(
    user_id: int, role: str, content: str, products: list[ChatProductCard] | None = None
) -> None:
    products_json = (
        json.dumps([{"product_id": p.product_id} for p in products]) if products else None
    )
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                role,
                content,
                products_json,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


@app.get("/api/chat/history", response_model=ChatHistoryResponse)
def chat_history(authorization: str | None = Header(default=None)):
    """Replay the caller's own saved conversation.

    Whose history this is comes from the signed token and nothing else. There
    is deliberately no `user_id` parameter — when there was one, it was an
    unauthenticated handle on any customer's chat log.
    """
    user_id = require_user_id(authorization)
    if load_customer_context(user_id) is None:
        return ChatHistoryResponse(messages=[])
    return ChatHistoryResponse(messages=load_stored_history(user_id))


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    authorization: str | None = Header(default=None),
):
    """One chat turn, behind the request-shape and rate checks.

    Order matters: everything that can refuse the request cheaply runs before
    the model is called, so an abusive caller costs a regex rather than a
    completion. Each refusal is audited, because "what did the system decline
    to do" is as much a part of the trail as what it did.
    """
    client = _client_key(request)

    # Identity comes from the token. A `user_id` in the body is ignored — it is
    # still in the schema only so older clients get a normal guest session
    # instead of a validation error.
    token_user_id = security.verify_session_token(security.bearer_token(authorization))
    customer = load_customer_context(token_user_id) if token_user_id else None

    def reject(status: int, reason: str, detail: str):
        audit.record(
            "request_rejected",
            reason=reason,
            authenticated=customer is not None,
            user_id=customer.user_id if customer else None,
            status=status,
            message_chars=len(payload.message or ""),
        )
        return HTTPException(status_code=status, detail=detail)

    if not security.chat_rate_limiter.check(client):
        raise reject(
            429,
            "rate_limited",
            "You're sending messages very quickly — give Handsome Dan a moment.",
        )

    message = (payload.message or "").strip()
    if not message:
        raise reject(400, "empty_message", "Type a question first.")
    if len(message) > MAX_MESSAGE_CHARS:
        raise reject(
            413,
            "message_too_long",
            f"That message is too long — keep it under {MAX_MESSAGE_CHARS} characters.",
        )

    # For a signed-in shopper the saved conversation is the source of truth, so
    # memory survives a page reload or a visit next week. Guests get only the
    # turns their own browser is holding, and nothing is written to the DB —
    # and that browser-supplied history is truncated here, since it is the one
    # part of the request a client fully controls.
    if customer is not None:
        history = [
            ChatTurn(role=turn.role, content=turn.content)
            for turn in load_stored_history(customer.user_id)
        ]
    else:
        history = payload.history[-MAX_HISTORY_TURNS:]

    try:
        reply = await run_chat(message, history, customer, payload.page_context)
    except AgentRunError as exc:
        # The run is already in the audit trail with its stop reason; the
        # shopper gets one sentence and no internals.
        raise HTTPException(
            status_code=504 if exc.stop_reason == "timeout" else 502,
            detail="The shopping assistant is temporarily unavailable.",
        ) from exc

    # Last line of defence before anything reaches a browser. The prompt
    # forbids the agent from reading an email or credential back; this makes it
    # so regardless of what the model decided.
    safe_message, was_scrubbed = security.scrub_reply(reply.message)
    if was_scrubbed:
        audit.record(
            "reply_scrubbed",
            authenticated=customer is not None,
            user_id=customer.user_id if customer else None,
        )

    cards = build_product_cards(reply.products)
    if customer is not None:
        save_chat_message(customer.user_id, "user", message)
        save_chat_message(customer.user_id, "assistant", safe_message, cards)

    return ChatResponse(reply=safe_message, products=cards)
