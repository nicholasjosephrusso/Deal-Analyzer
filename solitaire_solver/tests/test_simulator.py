from solitaire_solver.cards import Card
from solitaire_solver.deal import Deal, TableauPile
from solitaire_solver.moves import Move, MoveType
from solitaire_solver.simulator import verify_solution


def _empty_foundations():
    return {k: None for k in ("S", "H", "D", "C")}


def _pad_tableau(*piles):
    out = list(piles)
    while len(out) < 7:
        out.append(TableauPile(face_down=(), face_up=()))
    return tuple(out)


def _deal_one_spade_away(remaining_card: str) -> Deal:
    """Build a deal where every non-``remaining_card`` is already on the
    foundation; the remaining card sits on top of the stock."""
    remaining = Card.parse(remaining_card)
    # Foundations: each suit's top rank = 13, except the remaining_card's suit,
    # which stops one rank below.
    foundations = {k: Card.of(13, i) for i, k in enumerate(("S", "H", "D", "C"))}
    foundations[remaining_card[1]] = (
        Card.of(int(remaining.rank) - 1, remaining.suit)
        if remaining.rank > 1
        else None
    )
    deal = Deal(
        tableau=_pad_tableau(),
        stock=(remaining,),
        waste=(),
        foundations=foundations,
        draw_count=3,
    )
    deal.validate()
    return deal


def test_verify_one_move_solution():
    deal = _deal_one_spade_away("KS")
    moves = [
        Move(mtype=MoveType.DRAW),
        Move(mtype=MoveType.WASTE_TO_FOUNDATION, card=Card.parse("KS")),
    ]
    r = verify_solution(deal, moves)
    assert r.ok, r.reason


def test_verify_rejects_illegal_move():
    deal = _deal_one_spade_away("KS")
    moves = [
        Move(mtype=MoveType.WASTE_TO_FOUNDATION, card=Card.parse("KS")),  # waste empty
    ]
    r = verify_solution(deal, moves)
    assert not r.ok
    assert "illegal" in r.reason


def test_verify_rejects_non_terminal():
    deal = _deal_one_spade_away("KS")
    moves = [Move(mtype=MoveType.DRAW)]
    r = verify_solution(deal, moves)
    assert not r.ok
    assert "not a win" in r.reason
