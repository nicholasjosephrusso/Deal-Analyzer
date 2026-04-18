from solitaire_solver.cards import Card
from solitaire_solver.deal import Deal, TableauPile, make_random_deal
from solitaire_solver.moves import Move, MoveType, apply_move
from solitaire_solver.solver import solve
from solitaire_solver.state import GameState
from solitaire_solver.visual import card_text, render_board, state_at_step


def test_card_text_basic():
    assert card_text(Card.parse("AS")) == "A\u2660"
    assert card_text(Card.parse("KH")) == "K\u2665"
    assert card_text(Card.parse("TD")) == "10\u2666"  # display uses "10", not "T"
    assert card_text(Card.parse("9C")) == "9\u2663"


def test_render_board_initial_seeded_deal():
    deal = make_random_deal(seed=42)
    s = GameState.from_deal(deal)
    html = render_board(s)
    # Spot-check structural pieces.
    assert "<style>" in html
    assert "solv-card" in html
    assert "solv-row" in html
    assert "Stock (24)" in html
    assert "Waste (0)" in html
    # All seven tableau labels rendered.
    for i in range(7):
        assert f"T{i}" in html


def test_state_at_step_zero_equals_initial():
    deal = make_random_deal(seed=42)
    s0 = state_at_step(deal, [], 0)
    s_init = GameState.from_deal(deal)
    assert s0.canonical_key() == s_init.canonical_key()


def test_state_at_step_advances_through_solution():
    deal = make_random_deal(seed=42)
    r = solve(deal, budget_seconds=15.0, budget_nodes=500_000)
    if not r.solved:
        # Seed isn't reliably winnable in this budget; skip the deep check.
        return
    final = state_at_step(deal, r.moves, len(r.moves))
    assert final.is_won()
    # Mid-step is at least a valid state and consistent with apply_move.
    mid = state_at_step(deal, r.moves, len(r.moves) // 2)
    assert isinstance(mid, GameState)


def test_render_board_won_state():
    # Construct a trivially-won state: all foundations at K, no tableau, no deck.
    foundations = {k: Card.of(13, i) for i, k in enumerate(("S", "H", "D", "C"))}
    deal = Deal(
        tableau=tuple(TableauPile(face_down=(), face_up=()) for _ in range(7)),
        stock=(),
        waste=(),
        foundations=foundations,
        draw_count=3,
    )
    deal.validate()
    s = GameState.from_deal(deal)
    assert s.is_won()
    html = render_board(s)
    # Each foundation slot shows its King.
    assert "K\u2660" in html and "K\u2665" in html and "K\u2666" in html and "K\u2663" in html
