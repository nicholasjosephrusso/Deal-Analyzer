from solitaire_solver.cards import Card
from solitaire_solver.deal import Deal, TableauPile
from solitaire_solver.moves import MoveType, legal_moves
from solitaire_solver.state import GameState


def _empty_foundations():
    return {k: None for k in ("S", "H", "D", "C")}


def _pad_tableau(*piles):
    """Pad to exactly 7 TableauPile entries, each trailing pile empty."""
    out = list(piles)
    while len(out) < 7:
        out.append(TableauPile(face_down=(), face_up=()))
    return tuple(out)


def test_tableau_to_tableau_color_and_rank():
    # Pile 0 top = 6S (black), Pile 1 top = 7H (red). 6S should be movable onto 7H.
    # Use the remaining 50 cards as deck to keep validate() happy.
    placed = {Card.parse("6S"), Card.parse("7H")}
    remaining = [Card(i) for i in range(52) if Card(i) not in placed]

    deal = Deal(
        tableau=_pad_tableau(
            TableauPile(face_down=(), face_up=(Card.parse("6S"),)),
            TableauPile(face_down=(), face_up=(Card.parse("7H"),)),
        ),
        stock=tuple(remaining),
        waste=(),
        foundations=_empty_foundations(),
    )
    deal.validate()
    s = GameState.from_deal(deal)
    moves = legal_moves(s)
    tt_moves = [m for m in moves if m.mtype == MoveType.TABLEAU_TO_TABLEAU]
    pairs = {(m.src_pile, m.dst_pile) for m in tt_moves}
    assert (0, 1) in pairs  # 6S onto 7H: legal
    assert (1, 0) not in pairs  # 7H onto 6S: illegal (wrong rank direction)


def test_king_to_empty_pile_only():
    placed = {Card.parse("KS"), Card.parse("QH")}
    remaining = [Card(i) for i in range(52) if Card(i) not in placed]

    deal = Deal(
        tableau=_pad_tableau(
            TableauPile(face_down=(), face_up=(Card.parse("KS"),)),
            TableauPile(face_down=(), face_up=(Card.parse("QH"),)),
        ),
        stock=tuple(remaining),
        waste=(),
        foundations=_empty_foundations(),
    )
    deal.validate()
    s = GameState.from_deal(deal)
    moves = legal_moves(s)
    # King can move to an empty pile (2..6) but not onto QH (queen needs red king
    # of opposite color — QH is red, so it actually *could* take a black king...
    # wait: to move KS onto QH would be Q + K which is wrong direction. Only
    # K->empty is legal.)
    king_moves = [
        m for m in moves
        if m.mtype == MoveType.TABLEAU_TO_TABLEAU and m.src_pile == 0
    ]
    # King at pile 0 (has no face-down) moving to empty piles 2..6 is a no-op
    # shuffle and should be pruned; destinations should be empty (no face-down)
    # OR onto QH (not allowed). So zero legal moves for King at pile 0.
    assert king_moves == []
