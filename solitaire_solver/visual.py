"""Streamlit-free HTML renderer for a GameState board.

Lives outside ``solver_app.py`` so it can be unit-tested without a Streamlit
runtime. The renderer returns a single self-contained HTML string suitable
for ``st.markdown(..., unsafe_allow_html=True)``.
"""

from __future__ import annotations

from solitaire_solver.cards import Card, SUIT_CHARS
from solitaire_solver.moves import MoveType, apply_move
from solitaire_solver.state import GameState


SUIT_GLYPHS = {"S": "\u2660", "H": "\u2665", "D": "\u2666", "C": "\u2663"}
RED_SUITS = {"H", "D"}
RANK_GLYPHS = {1: "A", 11: "J", 12: "Q", 13: "K"}


CARD_CSS = """
<style>
.solv-pile { display: inline-block; vertical-align: top; margin-right: 18px; min-width: 60px; }
.solv-pile-label { font-size: 11px; color: #888; text-align: center; margin-bottom: 4px; }
.solv-card {
  display: block;
  width: 56px; height: 78px;
  border: 1px solid #444;
  border-radius: 6px;
  background: white;
  text-align: center;
  font-weight: 600;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 18px;
  line-height: 78px;
  margin-bottom: -56px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.18);
  position: relative;
}
.solv-card.red { color: #c0392b; }
.solv-card.black { color: #111; }
.solv-card.facedown {
  background: repeating-linear-gradient(45deg, #2c3e50, #2c3e50 6px, #34495e 6px, #34495e 12px);
  color: transparent;
}
.solv-card.empty {
  background: transparent;
  border: 1px dashed #888;
  color: #888;
  font-size: 22px;
}
.solv-card.last { margin-bottom: 0; }
.solv-row { display: flex; flex-wrap: wrap; gap: 4px; }
</style>
"""


def card_text(card: Card) -> str:
    rank = RANK_GLYPHS.get(int(card.rank), str(int(card.rank)))
    return f"{rank}{SUIT_GLYPHS[SUIT_CHARS[int(card.suit)]]}"


def _card_html(card: Card, last: bool = False) -> str:
    color = "red" if SUIT_CHARS[int(card.suit)] in RED_SUITS else "black"
    cls = f"solv-card {color}{' last' if last else ''}"
    return f'<div class="{cls}">{card_text(card)}</div>'


def _facedown_html(last: bool = False) -> str:
    return f'<div class="solv-card facedown{" last" if last else ""}">.</div>'


def _empty_html(label: str = "") -> str:
    return f'<div class="solv-card empty last">{label}</div>'


def _pile_html(label: str, cards_html: list[str]) -> str:
    body = "".join(cards_html) if cards_html else _empty_html()
    return f'<div class="solv-pile"><div class="solv-pile-label">{label}</div>{body}</div>'


def render_board(state: GameState) -> str:
    parts: list[str] = [CARD_CSS]

    foundation_piles = []
    for i, key in enumerate(("S", "H", "D", "C")):
        rank = state.foundations[i]
        if rank == 0:
            cards_html = [_empty_html(SUIT_GLYPHS[key])]
        else:
            cards_html = [_card_html(Card.of(rank, i), last=True)]
        foundation_piles.append(_pile_html(f"Found {key}", cards_html))

    stock_count = max(0, len(state.deck) - 1 - state.cursor)
    if stock_count > 0:
        stock_html = [_facedown_html(last=True)]
        stock_label = f"Stock ({stock_count})"
    else:
        stock_html = [_empty_html("\u2205")]
        stock_label = "Stock (0)"

    if state.cursor >= 0:
        start = max(0, state.cursor - 2)
        waste_cards = state.deck[start : state.cursor + 1]
        waste_html = [
            _card_html(c, last=(idx == len(waste_cards) - 1))
            for idx, c in enumerate(waste_cards)
        ]
        waste_label = f"Waste ({state.cursor + 1})"
    else:
        waste_html = [_empty_html("\u2205")]
        waste_label = "Waste (0)"

    top_row = (
        '<div class="solv-row">'
        + "".join(foundation_piles)
        + '<div style="width:30px;"></div>'
        + _pile_html(stock_label, stock_html)
        + _pile_html(waste_label, waste_html)
        + "</div>"
    )
    parts.append(top_row)

    tableau_piles = []
    for i in range(7):
        fd = state.tableau_face_down[i]
        fu = state.tableau_face_up[i]
        cards_html: list[str] = []
        for _ in fd:
            cards_html.append(_facedown_html())
        for j, c in enumerate(fu):
            cards_html.append(_card_html(c, last=(j == len(fu) - 1)))
        tableau_piles.append(_pile_html(f"T{i}", cards_html))
    parts.append('<div style="height:18px;"></div>')
    parts.append('<div class="solv-row">' + "".join(tableau_piles) + "</div>")

    return "".join(parts)


def state_at_step(deal, moves, step: int) -> GameState:
    """Reconstruct the GameState after applying the first ``step`` moves
    (FLIP entries are bookkeeping and do not advance state on their own)."""
    s = GameState.from_deal(deal)
    applied = 0
    for m in moves:
        if applied >= step:
            break
        if m.mtype == MoveType.FLIP:
            applied += 1
            continue
        apply_move(s, m)
        applied += 1
    return s
