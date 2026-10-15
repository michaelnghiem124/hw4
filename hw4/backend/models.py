"""Pydantic / PydanticAI structured types shared across the agent and the API layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class CustomerContext(BaseModel):
    """Who is chatting.

    Built server-side from the `users` table using the signed-in user's id —
    never taken from whatever the browser claims the shopper's name/email is.
    """

    user_id: int
    name: str
    email: str


class PageContext(BaseModel):
    """What the shopper is looking at while they type.

    `product_id` is set whenever they're on a /products/:id detail page, so a
    question like "do you have this in pink?" can be resolved to a real item.
    """

    path: str
    product_id: str | None = None


#: Soft cap on tool calls in a single turn. Past this the tools stop querying
#: and return an empty/not-found result telling the model to answer with what it
#: already has. Four is a normal turn (search, then inventory on a couple of
#: hits); eight means the model is going in circles.
MAX_TOOL_CALLS = 8

#: Hard ceilings handed to PydanticAI. These end the run outright rather than
#: nudging the model, and sit above the soft cap on purpose — the soft cap
#: should normally fire first and produce a usable answer.
MAX_MODEL_REQUESTS = 12
MAX_TOOL_CALLS_HARD = 12
MAX_TOTAL_TOKENS = 60_000

#: Wall-clock ceiling for one turn, including every model round trip. Nothing
#: the shopper asked is worth more than this, and an unbounded await is how a
#: stuck run becomes a stuck connection.
RUN_TIMEOUT_SECONDS = 45.0

#: Never let one search drag the whole catalogue into the context window.
MAX_SEARCH_RESULTS = 8

#: Request-shape ceilings, enforced at the API boundary before a model is ever
#: reached. A shopping question is a sentence; anything far past this is either
#: a mistake or someone trying to smuggle a payload through the chat box.
MAX_MESSAGE_CHARS = 1_000
MAX_HISTORY_TURNS = 20
MAX_HISTORY_CHARS = 8_000

#: Per-client throttle on /api/chat. Each turn costs a real model call, so an
#: unthrottled endpoint is both a billing hole and a denial-of-service surface.
RATE_LIMIT_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 300


@dataclass
class RunState:
    """Per-run counters and identity for one agent turn.

    Carried on `AgentDeps` so tools can both enforce the budget and write
    themselves into the audit trail with the right `run_id`.
    """

    run_id: str
    tool_calls: int = 0
    budget_exhausted: bool = False

    def charge_tool_call(self) -> bool:
        """Count one tool call. Returns False once the soft cap is used up."""
        if self.tool_calls >= MAX_TOOL_CALLS:
            self.budget_exhausted = True
            return False
        self.tool_calls += 1
        return True


@dataclass
class AgentDeps:
    """Per-run dependencies handed to agent tools via RunContext.

    Only a read-only path to the database is provided — tools open their own
    strictly read-only SQLite connection from this path (see tools.py), so the
    agent has no code path capable of writing to the database.

    `customer` is None for guests; `page_context` is None if the browser didn't
    report a page (the agent then just has no on-screen item to refer to).
    `run_state` carries the tool budget and the audit correlation id.
    """

    db_path: Path
    customer: CustomerContext | None = None
    page_context: PageContext | None = None
    run_state: RunState = field(default_factory=lambda: RunState(run_id="untracked"))


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = Field(default_factory=list)
    page_context: PageContext | None = None
    user_id: int | None = None
    """Ignored. Identity comes from the signed session token in the
    Authorization header — see security.verify_session_token. The field is
    retained only so a stale client that still sends it gets a normal guest
    session rather than a 422, and it is never read."""


class ProductRef(BaseModel):
    """A product the assistant is citing, sourced from a tool call result."""

    product_id: str
    name: str
    price: float


class ChatProductCard(BaseModel):
    """A product card the chat widget renders on the page.

    The agent only ever names a product_id; every display field here is
    re-read from the catalogue by the API layer before it is sent to the
    browser, so a card can never show an invented name, price, or image.
    """

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    image_url: str
    in_stock: bool


class ProductSearchResult(BaseModel):
    """One row returned by the search_products tool."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float


class SizeStock(BaseModel):
    """Live stock for a single size of a single product."""

    size: str
    quantity: int
    in_stock: bool
    availability: str
    """Plain-English phrasing of `quantity` — "in stock", "only 2 left",
    "sold out". Derived from the live number so the agent can say stock in a
    sentence instead of inventing its own symbol key."""


class ProductInventory(BaseModel):
    """Full live product + inventory detail returned by get_product_inventory.

    This is the structured return type tools use to hand price/stock facts to
    the agent — the agent must never state a price, size, or quantity that
    didn't come from a value in one of these fields.
    """

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str] = Field(default_factory=list)
    price: float
    sizes: list[SizeStock] = Field(default_factory=list)
    in_stock: bool
    out_of_stock_sizes: list[str] = Field(default_factory=list)
    stock_summary: str = ""
    """A ready-to-say sentence covering every size, e.g. "Available in S, M and
    L. Sold out in XS and XXL." The agent is told to reuse this wording rather
    than rendering its own bulleted symbol list."""


class ProductNotFound(BaseModel):
    """Returned by get_product_inventory when a product_id doesn't exist."""

    error: str = "unknown product_id"


class AgentReply(BaseModel):
    """Structured output the agent must produce for every turn."""

    message: str
    products: list[ProductRef] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    products: list[ChatProductCard] = Field(default_factory=list)


class StoredChatTurn(BaseModel):
    """One persisted turn, replayed into the widget when a user returns."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ChatProductCard] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    messages: list[StoredChatTurn] = Field(default_factory=list)
