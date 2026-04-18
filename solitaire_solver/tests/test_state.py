from solitaire_solver.cards import Card
from solitaire_solver.deal import make_random_deal
from solitaire_solver.moves import apply_move, legal_moves
from solitaire_solver.state import GameState


def test_from_deal_roundtrip_card_count():
    deal = make_random_deal(seed=1)
    s = GameState.from_deal(deal)
    total = sum(s.foundations)
    for i in range(7):
        total += len(s.tableau_face_down[i]) + len(s.tableau_face_up[i])
    total += len(s.deck)
    assert total == 52


def test_apply_undo_restores_state():
    deal = make_random_deal(seed=42)
    s = GameState.from_deal(deal)
    key0 = s.canonical_key()
    moves = legal_moves(s)
    assert moves, "expected legal moves on fresh deal"
    for m in moves:
        tok = apply_move(s, m)
        s.undo(tok)
        assert s.canonical_key() == key0, f"undo failed for move {m}"


def test_deep_apply_undo():
    deal = make_random_deal(seed=7)
    s = GameState.from_deal(deal)
    key0 = s.canonical_key()
    trail = []
    for _ in range(10):
        moves = legal_moves(s)
        if not moves:
            break
        m = moves[0]
        trail.append(apply_move(s, m))
    for tok in reversed(trail):
        s.undo(tok)
    assert s.canonical_key() == key0
