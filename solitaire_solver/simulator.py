"""Pure replay engine.

``verify_solution`` rebuilds a GameState from the initial Deal, applies each
move asserting legality at application time, and confirms the terminal state
has all four foundations at King.
"""

from __future__ import annotations

from dataclasses import dataclass

from solitaire_solver.cards import Card
from solitaire_solver.deal import Deal
from solitaire_solver.moves import Move, MoveType, apply_move
from solitaire_solver.state import GameState


@dataclass
class VerifyResult:
    ok: bool
    reason: str = ""
    moves_applied: int = 0


def is_legal(state: GameState, m: Move) -> bool:
    if m.mtype == MoveType.DRAW:
        return state.stock_has_cards()
    if m.mtype == MoveType.RECYCLE:
        return (
            len(state.deck) > 0
            and state.cursor == len(state.deck) - 1
        )
    if m.mtype == MoveType.WASTE_TO_FOUNDATION:
        if state.cursor < 0:
            return False
        c = state.deck[state.cursor]
        return state.foundations[int(c.suit)] + 1 == int(c.rank)
    if m.mtype == MoveType.WASTE_TO_TABLEAU:
        if state.cursor < 0:
            return False
        c = state.deck[state.cursor]
        return _fits_tableau(state, m.dst_pile, c)
    if m.mtype == MoveType.TABLEAU_TO_FOUNDATION:
        fu = state.tableau_face_up[m.src_pile]
        if not fu:
            return False
        c = fu[-1]
        return state.foundations[int(c.suit)] + 1 == int(c.rank)
    if m.mtype == MoveType.TABLEAU_TO_TABLEAU:
        fu = state.tableau_face_up[m.src_pile]
        if m.count < 1 or m.count > len(fu):
            return False
        bottom = fu[-m.count]
        return _fits_tableau(state, m.dst_pile, bottom)
    if m.mtype == MoveType.FLIP:
        return True  # informational
    return False


def _fits_tableau(state: GameState, dst: int, card: Card) -> bool:
    fu_dst = state.tableau_face_up[dst]
    if fu_dst:
        top = fu_dst[-1]
        return int(top.rank) == int(card.rank) + 1 and top.color != card.color
    return int(card.rank) == 13


def verify_solution(deal: Deal, moves: list[Move]) -> VerifyResult:
    state = GameState.from_deal(deal)
    for i, m in enumerate(moves):
        if m.mtype == MoveType.FLIP:
            continue  # informational; apply_move does the real flip
        if not is_legal(state, m):
            return VerifyResult(
                ok=False,
                reason=f"illegal move at index {i}: {m}",
                moves_applied=i,
            )
        apply_move(state, m)
    if not state.is_won():
        return VerifyResult(
            ok=False,
            reason="terminal state is not a win (not all foundations complete)",
            moves_applied=len(moves),
        )
    return VerifyResult(ok=True, moves_applied=len(moves))
