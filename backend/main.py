"""FastAPI service wrapping the Klondike draw-3 solver.

Endpoints:
- POST /solve: accepts a Deal (same JSON shape as deal_to_json) and returns
  the solution envelope + per-step board snapshots so the frontend can
  replay without duplicating apply_move logic.
- POST /random-deal: returns a random fully-known deal.
- GET  /health: liveness probe.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from solitaire_solver.cards import Card
from solitaire_solver.deal import Deal, deal_from_json, deal_to_json, make_random_deal
from solitaire_solver.moves import Move, MoveType, apply_move
from solitaire_solver.serialize import envelope, humanize, move_to_json
from solitaire_solver.solver import solve
from solitaire_solver.state import GameState


app = FastAPI(title="Deal-Analyzer Solitaire Solver", version="1.0")

# Wide-open CORS since this is a trainer app; tighten with an allowlist for prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


SUIT_KEYS = ("S", "H", "D", "C")


def _card_code(c: Card | None) -> str | None:
    return c.code() if c is not None else None


def _snapshot(state: GameState) -> dict[str, Any]:
    """Compact board snapshot the frontend can render directly."""
    # Waste: show up to 3 most-recently-drawn (the visible draw-3 stack).
    waste: list[str] = []
    if state.cursor >= 0:
        start = max(0, state.cursor - 2)
        waste = [c.code() for c in state.deck[start : state.cursor + 1]]
    return {
        "foundations": {SUIT_KEYS[i]: state.foundations[i] for i in range(4)},
        "stock_count": max(0, len(state.deck) - 1 - state.cursor),
        "waste_visible": waste,
        "tableau": [
            {
                "face_down": len(state.tableau_face_down[i]),
                "face_up": [c.code() for c in state.tableau_face_up[i]],
            }
            for i in range(7)
        ],
        "is_won": state.is_won(),
    }


def _replay_snapshots(deal: Deal, moves: list[Move]) -> list[dict[str, Any]]:
    """Reconstruct the state after each move so the frontend doesn't need to."""
    state = GameState.from_deal(deal)
    snaps = [_snapshot(state)]
    for m in moves:
        if m.mtype != MoveType.FLIP:
            apply_move(state, m)
        snaps.append(_snapshot(state))
    return snaps


# ---------- Request / response models ----------


class SolveRequest(BaseModel):
    deal: dict = Field(..., description="Deal JSON (see solitaire_solver.deal.deal_to_json)")
    budget_seconds: float = Field(30.0, ge=0.5, le=300.0)
    budget_nodes: int = Field(1_000_000, ge=1_000, le=50_000_000)


class RandomDealRequest(BaseModel):
    seed: int | None = Field(None, ge=0)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/random-deal")
def random_deal(req: RandomDealRequest) -> dict[str, Any]:
    import random

    seed = req.seed if req.seed is not None else random.randint(0, 10_000_000)
    deal = make_random_deal(seed)
    return {"seed": seed, "deal": deal_to_json(deal), "digest": deal.digest()}


@app.post("/solve")
def solve_endpoint(req: SolveRequest) -> dict[str, Any]:
    try:
        deal = deal_from_json(req.deal)
    except Exception as e:  # malformed input
        raise HTTPException(status_code=400, detail=f"invalid deal: {e}") from None

    start = time.monotonic()
    result = solve(
        deal,
        budget_seconds=float(req.budget_seconds),
        budget_nodes=int(req.budget_nodes),
    )
    env = envelope(
        deal_digest=deal.digest(),
        moves=result.moves,
        solved=result.solved,
        node_count=result.node_count,
        elapsed_seconds=result.elapsed_seconds,
    )
    env["reason"] = result.reason
    env["move_descriptions"] = [
        humanize(m, i + 1).strip() for i, m in enumerate(result.moves)
    ]
    env["snapshots"] = (
        _replay_snapshots(deal, result.moves) if result.solved else []
    )
    env["wall_seconds"] = round(time.monotonic() - start, 6)
    return env
