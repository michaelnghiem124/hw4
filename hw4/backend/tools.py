"""Tools the Campus Customs agent can call.

Every tool here opens its own SQLite connection in strict read-only mode
(`mode=ro` on the URI). This is a code-level guarantee, not just a prompt
instruction: even if a tool were misused or a prompt-injection attempt tried
to get the agent to "write" something, the underlying connection physically
cannot perform an INSERT/UPDATE/DELETE — SQLite raises instead.

Every tool is also metered and audited. `_audited` charges the run's tool
budget, times the call, and appends a `tool_call` record to the audit trail.
Two properties fall out of routing all four tools through one wrapper:

- A new tool cannot be added without being logged, because the logging lives in
  the call path rather than in each tool body.
- What gets logged is a *summary* — product ids, prices, row counts — never a
  result set. Tool results are catalogue facts, so they carry no customer data
  by construction, and the summaries keep the trail readable besides.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic_ai import Agent, RunContext

import audit
from models import (
    MAX_SEARCH_RESULTS,
    AgentDeps,
    ProductInventory,
    ProductNotFound,
    ProductSearchResult,
    SizeStock,
)

T = TypeVar("T")

#: Returned to the model in place of real data once the tool budget is spent.
BUDGET_MESSAGE = (
    "tool budget for this turn is exhausted — answer now using what you already have"
)


def _summarize(result: Any) -> dict[str, Any]:
    """Compress a tool result to the few facts worth auditing.

    Deliberately lossy. The audit trail answers "what did the agent look up and
    what came back", not "what was in the catalogue at the time" — the database
    is already the record for that.
    """
    if isinstance(result, ProductNotFound):
        return {"found": False, "error": result.error}
    if isinstance(result, ProductInventory):
        return {
            "found": True,
            "product_id": result.product_id,
            "price": result.price,
            "in_stock": result.in_stock,
            "sold_out_sizes": result.out_of_stock_sizes,
        }
    if isinstance(result, list):
        summary: dict[str, Any] = {"count": len(result)}
        if result and isinstance(result[0], ProductSearchResult):
            summary["product_ids"] = [r.product_id for r in result[:MAX_SEARCH_RESULTS]]
        return summary
    return {"value": str(result)[:120]}


def _audited(
    ctx: RunContext[AgentDeps],
    tool: str,
    args: dict[str, Any],
    work: Callable[[], T],
    on_budget_exhausted: Callable[[], T],
) -> T:
    """Meter, time, run and log one tool call.

    When the soft budget is spent the tool returns `on_budget_exhausted()`
    instead of touching the database — a type-compatible empty/not-found value
    that tells the model to stop searching and answer. The run still ends
    normally, so the shopper gets a reply built from what was already gathered
    rather than an error page.
    """
    state = ctx.deps.run_state

    if not state.charge_tool_call():
        audit.record(
            "tool_call",
            run_id=state.run_id,
            seq=state.tool_calls + 1,
            tool=tool,
            args=args,
            ok=False,
            blocked=True,
            reason="tool_budget_exhausted",
        )
        return on_budget_exhausted()

    seq = state.tool_calls
    started = time.perf_counter()
    try:
        result = work()
    except Exception as exc:
        audit.record(
            "tool_call",
            run_id=state.run_id,
            seq=seq,
            tool=tool,
            args=args,
            ok=False,
            error=type(exc).__name__,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        raise

    audit.record(
        "tool_call",
        run_id=state.run_id,
        seq=seq,
        tool=tool,
        args=args,
        ok=True,
        result=_summarize(result),
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return result


def _read_only_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


LOW_STOCK_THRESHOLD = 3


def _availability_phrase(quantity: int) -> str:
    """Turn a raw count into shop-floor language.

    The number still comes from the database; this only decides how to say it,
    so the agent never has to invent its own stock notation.
    """
    if quantity <= 0:
        return "sold out"
    if quantity == 1:
        return "last one left"
    if quantity <= LOW_STOCK_THRESHOLD:
        return f"only {quantity} left"
    return "in stock"


def _join_sizes(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _stock_summary(sizes: list[SizeStock]) -> str:
    """One ready-to-say sentence covering every size."""
    available = [s.size for s in sizes if s.in_stock]
    sold_out = [s.size for s in sizes if not s.in_stock]
    low = [s for s in sizes if 0 < s.quantity <= LOW_STOCK_THRESHOLD]

    if not available:
        return "Sold out in every size right now."

    parts = [f"Available in {_join_sizes(available)}."]
    if low:
        parts.append(
            "Running low on "
            + _join_sizes([f"{s.size} ({_availability_phrase(s.quantity)})" for s in low])
            + "."
        )
    if sold_out:
        parts.append(f"Sold out in {_join_sizes(sold_out)}.")
    return " ".join(parts)


def _load_inventory(
    conn: sqlite3.Connection, product_id: str
) -> ProductInventory | ProductNotFound:
    product = conn.execute(
        "SELECT product_id, name, garment_type, description, colors, price "
        "FROM catalogue WHERE product_id = ?",
        (product_id,),
    ).fetchone()
    if product is None:
        return ProductNotFound()

    size_rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ? "
        "ORDER BY CASE size WHEN 'XS' THEN 1 WHEN 'S' THEN 2 WHEN 'M' THEN 3 "
        "WHEN 'L' THEN 4 WHEN 'XL' THEN 5 WHEN 'XXL' THEN 6 END",
        (product_id,),
    ).fetchall()

    sizes = [
        SizeStock(
            size=s["size"],
            quantity=s["quantity"],
            in_stock=s["quantity"] > 0,
            availability=_availability_phrase(s["quantity"]),
        )
        for s in size_rows
    ]

    return ProductInventory(
        product_id=product["product_id"],
        name=product["name"],
        garment_type=product["garment_type"],
        description=product["description"],
        colors=json.loads(product["colors"]),
        price=product["price"],
        sizes=sizes,
        in_stock=any(s.in_stock for s in sizes),
        out_of_stock_sizes=[s.size for s in sizes if not s.in_stock],
        stock_summary=_stock_summary(sizes),
    )


def register_tools(agent: Agent) -> None:
    """Attach all read-only catalogue tools to the given agent instance."""

    @agent.tool
    def search_products(
        ctx: RunContext[AgentDeps], query: str, max_results: int = 5
    ) -> list[ProductSearchResult]:
        """Search the live product catalogue by name, garment type, description, or tags.

        Matches each word in the query independently (so "Boola Boola T-Shirt"
        still matches a catalogue row named "Boola Boola T Shirt"), across name,
        garment_type, description, and search_tags. Returns up to max_results
        matching products (capped server-side at 8). Use the returned product_id
        with get_product_inventory to check live price, sizes, and stock.
        """
        # The model picks max_results, so it is clamped here rather than
        # trusted — a 500-row result set is a context-window problem, and
        # "return everything" is the shape a runaway loop tends to take.
        capped = max(1, min(max_results, MAX_SEARCH_RESULTS))

        def work() -> list[ProductSearchResult]:
            conn = _read_only_connection(ctx.deps.db_path)
            try:
                tokens = [t for t in re.split(r"[\s-]+", query.lower()) if t]
                if not tokens:
                    return []

                clauses = []
                params: list[str] = []
                for token in tokens:
                    like = f"%{token}%"
                    clauses.append(
                        "(lower(name) LIKE ? OR lower(garment_type) LIKE ? "
                        "OR lower(description) LIKE ? OR lower(search_tags) LIKE ?)"
                    )
                    params.extend([like, like, like, like])

                sql = (
                    "SELECT product_id, name, garment_type, description, price "
                    f"FROM catalogue WHERE {' AND '.join(clauses)} ORDER BY name LIMIT ?"
                )
                rows = conn.execute(sql, (*params, capped)).fetchall()
                return [
                    ProductSearchResult(
                        product_id=r["product_id"],
                        name=r["name"],
                        garment_type=r["garment_type"],
                        description=r["description"],
                        price=r["price"],
                    )
                    for r in rows
                ]
            finally:
                conn.close()

        return _audited(
            ctx,
            "search_products",
            {"query": audit.preview(query, 80), "max_results": capped},
            work,
            lambda: [],
        )

    @agent.tool
    def get_product_inventory(
        ctx: RunContext[AgentDeps], product_id: str
    ) -> ProductInventory | ProductNotFound:
        """Look up the full live product detail and per-size stock for one product_id.

        This is the only source of truth for price, description, colors, and
        per-size stock quantities — never state any of these from memory or
        guess them. Use a product_id returned by search_products. Returns a
        ProductNotFound error object if the product_id doesn't exist.

        Every size present in the catalogue is returned, including sizes that
        are currently out of stock (quantity 0, in_stock=False) — never omit
        or round up an out-of-stock size, and always say plainly when a size
        has no stock.
        """

        def work() -> ProductInventory | ProductNotFound:
            conn = _read_only_connection(ctx.deps.db_path)
            try:
                return _load_inventory(conn, product_id)
            finally:
                conn.close()

        return _audited(
            ctx,
            "get_product_inventory",
            {"product_id": product_id},
            work,
            lambda: ProductNotFound(error=BUDGET_MESSAGE),
        )

    @agent.tool
    def get_page_product(ctx: RunContext[AgentDeps]) -> ProductInventory | ProductNotFound:
        """Look up the product the shopper is currently viewing on the website.

        Call this whenever the customer says "this", "it", "this shirt", or
        otherwise refers to an item without naming it — the website reports
        which product page they have open, and this returns that product's
        full detail and per-size stock. Returns ProductNotFound if they aren't
        on a product page, in which case ask them which item they mean.
        """
        page = ctx.deps.page_context
        if page is None or not page.product_id:
            return ProductNotFound(error="the shopper is not on a product page")
        product_id = page.product_id

        def work() -> ProductInventory | ProductNotFound:
            conn = _read_only_connection(ctx.deps.db_path)
            try:
                return _load_inventory(conn, product_id)
            finally:
                conn.close()

        return _audited(
            ctx,
            "get_page_product",
            {"product_id": product_id},
            work,
            lambda: ProductNotFound(error=BUDGET_MESSAGE),
        )

    @agent.tool
    def list_garment_types(ctx: RunContext[AgentDeps]) -> list[str]:
        """List the distinct garment types currently in the catalogue."""

        def work() -> list[str]:
            conn = _read_only_connection(ctx.deps.db_path)
            try:
                rows = conn.execute(
                    "SELECT DISTINCT garment_type FROM catalogue ORDER BY garment_type"
                ).fetchall()
                return [r["garment_type"] for r in rows]
            finally:
                conn.close()

        return _audited(ctx, "list_garment_types", {}, work, lambda: [])
