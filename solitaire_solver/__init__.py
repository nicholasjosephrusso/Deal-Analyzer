"""Klondike draw-3 solitaire solver.

Public API:
    Card, Suit, Rank, Color  -- card primitives
    Deal                     -- CV input contract
    GameState                -- internal search state
    Move, MoveType           -- move representation
    solve(deal, budget)      -- top-level solver
    verify_solution          -- replay-based verifier
"""

from solitaire_solver.cards import Card, Color, Rank, Suit
from solitaire_solver.deal import Deal, TableauPile
from solitaire_solver.moves import Move, MoveType
from solitaire_solver.simulator import verify_solution
from solitaire_solver.solver import SolveResult, solve
from solitaire_solver.state import GameState

__version__ = "0.1.0"

__all__ = [
    "Card",
    "Color",
    "Deal",
    "GameState",
    "Move",
    "MoveType",
    "Rank",
    "SolveResult",
    "Suit",
    "TableauPile",
    "solve",
    "verify_solution",
]
