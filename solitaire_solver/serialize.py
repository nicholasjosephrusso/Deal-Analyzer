"""JSON and human-readable serialization for move lists."""

from __future__ import annotations

import json
from pathlib import Path

from solitaire_solver.cards import Card, SUIT_CHARS
from solitaire_solver.moves import Move, MoveType


SUIT_KEYS = ("S", "H", "D", "C")


def move_to_json(m: Move) -> dict:
    if m.mtype == MoveType.DRAW:
        return {"type": "draw"}
    if m.mtype == MoveType.RECYCLE:
        return {"type": "recycle"}
    if m.mtype == MoveType.WASTE_TO_FOUNDATION:
        assert m.card is not None
        return {"type": "waste_to_foundation", "card": m.card.code(), "to_foundation": SUIT_KEYS[int(m.card.suit)]}
    if m.mtype == MoveType.WASTE_TO_TABLEAU:
        assert m.card is not None
        return {"type": "waste_to_tableau", "card": m.card.code(), "to_pile": m.dst_pile}
    if m.mtype == MoveType.TABLEAU_TO_FOUNDATION:
        assert m.card is not None
        return {
            "type": "tableau_to_foundation",
            "from_pile": m.src_pile,
            "card": m.card.code(),
            "to_foundation": SUIT_KEYS[int(m.card.suit)],
        }
    if m.mtype == MoveType.TABLEAU_TO_TABLEAU:
        assert m.card is not None
        return {
            "type": "tableau_to_tableau",
            "from_pile": m.src_pile,
            "to_pile": m.dst_pile,
            "cards": m.count,
            "top_card": m.card.code(),
        }
    if m.mtype == MoveType.FLIP:
        assert m.revealed_card is not None
        return {"type": "flip", "pile": m.src_pile, "revealed_card": m.revealed_card.code()}
    raise ValueError(f"unknown move type: {m.mtype!r}")


def move_from_json(obj: dict) -> Move:
    t = obj["type"]
    if t == "draw":
        return Move(mtype=MoveType.DRAW)
    if t == "recycle":
        return Move(mtype=MoveType.RECYCLE)
    if t == "waste_to_foundation":
        return Move(mtype=MoveType.WASTE_TO_FOUNDATION, card=Card.parse(obj["card"]))
    if t == "waste_to_tableau":
        return Move(mtype=MoveType.WASTE_TO_TABLEAU, dst_pile=int(obj["to_pile"]), card=Card.parse(obj["card"]))
    if t == "tableau_to_foundation":
        return Move(
            mtype=MoveType.TABLEAU_TO_FOUNDATION,
            src_pile=int(obj["from_pile"]),
            card=Card.parse(obj["card"]),
        )
    if t == "tableau_to_tableau":
        return Move(
            mtype=MoveType.TABLEAU_TO_TABLEAU,
            src_pile=int(obj["from_pile"]),
            dst_pile=int(obj["to_pile"]),
            count=int(obj["cards"]),
            card=Card.parse(obj["top_card"]),
        )
    if t == "flip":
        return Move(
            mtype=MoveType.FLIP,
            src_pile=int(obj["pile"]),
            revealed_card=Card.parse(obj["revealed_card"]),
        )
    raise ValueError(f"unknown move json: {obj}")


def envelope(
    deal_digest: str,
    moves: list[Move],
    solved: bool,
    node_count: int,
    elapsed_seconds: float,
) -> dict:
    return {
        "version": "1.0",
        "variant": "klondike-draw-3",
        "initial_deal_id": deal_digest,
        "solved": solved,
        "node_count": node_count,
        "elapsed_seconds": round(elapsed_seconds, 6),
        "moves": [move_to_json(m) for m in moves],
    }


def write_envelope(path: str | Path, env: dict) -> None:
    with open(path, "w") as f:
        json.dump(env, f, indent=2)
        f.write("\n")


def read_moves(path: str | Path) -> list[Move]:
    with open(path) as f:
        env = json.load(f)
    return [move_from_json(o) for o in env["moves"]]


# ---------- Human-readable ----------


def humanize(m: Move, index: int) -> str:
    n = f"{index:>4}."
    if m.mtype == MoveType.DRAW:
        return f"{n} draw"
    if m.mtype == MoveType.RECYCLE:
        return f"{n} recycle stock"
    if m.mtype == MoveType.WASTE_TO_FOUNDATION:
        assert m.card is not None
        return f"{n} waste -> foundation {SUIT_KEYS[int(m.card.suit)]}: {m.card}"
    if m.mtype == MoveType.WASTE_TO_TABLEAU:
        assert m.card is not None
        return f"{n} waste -> tableau[{m.dst_pile}]: {m.card}"
    if m.mtype == MoveType.TABLEAU_TO_FOUNDATION:
        assert m.card is not None
        return f"{n} tableau[{m.src_pile}] -> foundation {SUIT_KEYS[int(m.card.suit)]}: {m.card}"
    if m.mtype == MoveType.TABLEAU_TO_TABLEAU:
        assert m.card is not None
        return f"{n} tableau[{m.src_pile}] -> tableau[{m.dst_pile}]: {m.count} cards (bottom {m.card})"
    if m.mtype == MoveType.FLIP:
        assert m.revealed_card is not None
        return f"{n} (flip) tableau[{m.src_pile}] reveals {m.revealed_card}"
    return f"{n} ???"


def humanize_all(moves: list[Move]) -> str:
    return "\n".join(humanize(m, i + 1) for i, m in enumerate(moves))
