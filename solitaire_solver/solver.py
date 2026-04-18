"""DFS + transposition-table solver for Klondike draw-3.

Strategy: depth-first, first-solution wins (not optimal moves). Safe
foundation auto-plays are applied at each node before branching. State
equivalence is tracked via a canonical bytestring key; symmetric empty piles
and equivalent stock/waste cycles collapse into a single TT entry.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

from solitaire_solver.deal import Deal
from solitaire_solver.moves import (
    Move,
    MoveType,
    apply_move,
    auto_play_safe,
    is_inverse,
    legal_moves,
)
from solitaire_solver.state import GameState


DEFAULT_BUDGET_SECONDS = 60.0
DEFAULT_BUDGET_NODES = 2_000_000


@dataclass
class SolveResult:
    solved: bool
    moves: list[Move] = field(default_factory=list)
    node_count: int = 0
    elapsed_seconds: float = 0.0
    aborted: bool = False
    reason: str = ""


def solve(
    deal: Deal,
    budget_seconds: float = DEFAULT_BUDGET_SECONDS,
    budget_nodes: int = DEFAULT_BUDGET_NODES,
) -> SolveResult:
    """Run DFS + TT until a solution is found or the budget is exhausted."""
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
    state = GameState.from_deal(deal)
    tt: set[bytes] = set()
    path: list[Move] = []

    start = time.monotonic()
    deadline = start + budget_seconds
    nodes = [0]  # single-element list for mutable closure

    def _flip_record(src_pile: int, revealed) -> Move:
        return Move(mtype=MoveType.FLIP, src_pile=src_pile, revealed_card=revealed)

    def dfs(last_move: Move | None) -> bool | None:
        nodes[0] += 1
        if nodes[0] >= budget_nodes or time.monotonic() >= deadline:
            return None  # abort

        key = state.canonical_key()
        if key in tt:
            return False
        tt.add(key)

        checkpoint = len(path)
        auto = auto_play_safe(state)
        for am, atok in auto:
            path.append(
                Move(
                    mtype=am.mtype,
                    src_pile=am.src_pile,
                    dst_pile=am.dst_pile,
                    count=am.count,
                    card=am.card,
                    revealed_card=atok.src_flipped_card,
                )
            )
            if atok.src_flipped_card is not None:
                path.append(_flip_record(atok.src_pile if am.src_pile < 0 else am.src_pile, atok.src_flipped_card))

        if state.is_won():
            return True

        for m in legal_moves(state):
            if last_move is not None and is_inverse(last_move, m):
                continue
            tok = apply_move(state, m)
            path.append(
                Move(
                    mtype=m.mtype,
                    src_pile=m.src_pile,
                    dst_pile=m.dst_pile,
                    count=m.count,
                    card=m.card,
                    revealed_card=tok.src_flipped_card,
                )
            )
            if tok.src_flipped_card is not None:
                path.append(_flip_record(m.src_pile, tok.src_flipped_card))

            result = dfs(m)
            if result is True:
                return True
            if result is None:
                return None

            if tok.src_flipped_card is not None:
                path.pop()
            path.pop()
            state.undo(tok)

        # Unwind auto-plays.
        del path[checkpoint:]
        for _, atok in reversed(auto):
            state.undo(atok)
        return False

    result = dfs(None)
    elapsed = time.monotonic() - start

    if result is True:
        return SolveResult(
            solved=True,
            moves=list(path),
            node_count=nodes[0],
            elapsed_seconds=elapsed,
        )
    if result is None:
        return SolveResult(
            solved=False,
            moves=[],
            node_count=nodes[0],
            elapsed_seconds=elapsed,
            aborted=True,
            reason="budget exhausted (node or time limit)",
        )
    return SolveResult(
        solved=False,
        moves=[],
        node_count=nodes[0],
        elapsed_seconds=elapsed,
        aborted=False,
        reason="state space exhausted; deal unsolvable within search",
    )
