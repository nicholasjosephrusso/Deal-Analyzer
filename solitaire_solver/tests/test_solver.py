import pytest

from solitaire_solver.cards import Card
from solitaire_solver.deal import Deal, TableauPile, make_random_deal
from solitaire_solver.simulator import verify_solution
from solitaire_solver.solver import solve


def _empty_foundations():
    return {k: None for k in ("S", "H", "D", "C")}


def _pad_tableau(*piles):
    out = list(piles)
    while len(out) < 7:
        out.append(TableauPile(face_down=(), face_up=()))
    return tuple(out)


def _one_card_away(card_code: str) -> Deal:
    remaining = Card.parse(card_code)
    suits = ("S", "H", "D", "C")
    foundations = {
        k: Card.of(13, i) if k != card_code[1] else (
            Card.of(int(remaining.rank) - 1, remaining.suit) if remaining.rank > 1 else None
        )
        for i, k in enumerate(suits)
    }
    deal = Deal(
        tableau=_pad_tableau(),
        stock=(remaining,),
        waste=(),
        foundations=foundations,
        draw_count=3,
    )
    deal.validate()
    return deal


def test_solve_trivial_one_card_from_stock():
    deal = _one_card_away("KS")
    result = solve(deal, budget_seconds=5.0, budget_nodes=100_000)
    assert result.solved, f"should solve trivially; reason={result.reason}"
    v = verify_solution(deal, result.moves)
    assert v.ok, v.reason


def test_solve_trivial_from_waste():
    # Same card, but already on waste: should auto-play immediately.
    remaining = Card.parse("KS")
    suits = ("S", "H", "D", "C")
    foundations = {
        k: Card.of(13, i) if k != "S" else Card.of(12, 0)  # Q spades
        for i, k in enumerate(suits)
    }
    deal = Deal(
        tableau=_pad_tableau(),
        stock=(),
        waste=(remaining,),
        foundations=foundations,
        draw_count=3,
    )
    deal.validate()
    result = solve(deal, budget_seconds=5.0, budget_nodes=100_000)
    assert result.solved, result.reason
    v = verify_solution(deal, result.moves)
    assert v.ok, v.reason


def test_solve_near_terminal_tableau_play():
    # A single spade King is sitting on a tableau pile, ready to foundation.
    remaining = Card.parse("KS")
    suits = ("S", "H", "D", "C")
    foundations = {
        k: Card.of(13, i) if k != "S" else Card.of(12, 0)
        for i, k in enumerate(suits)
    }
    deal = Deal(
        tableau=_pad_tableau(
            TableauPile(face_down=(), face_up=(remaining,)),
        ),
        stock=(),
        waste=(),
        foundations=foundations,
        draw_count=3,
    )
    deal.validate()
    result = solve(deal, budget_seconds=5.0, budget_nodes=100_000)
    assert result.solved, result.reason
    v = verify_solution(deal, result.moves)
    assert v.ok, v.reason


@pytest.mark.slow
def test_solve_random_seeded_deal_within_budget():
    """Smoke-level full-deck solve. Known-winnable seeds are hard to guarantee
    in pure Python within a tight budget, so we sweep a few seeds and accept
    as long as at least one solves within the cap."""
    solved_any = False
    for seed in (1, 2, 3, 4, 5):
        deal = make_random_deal(seed)
        result = solve(deal, budget_seconds=15.0, budget_nodes=500_000)
        if result.solved:
            v = verify_solution(deal, result.moves)
            assert v.ok, v.reason
            solved_any = True
            break
    assert solved_any, "expected at least one of 5 random seeds to solve within budget"
