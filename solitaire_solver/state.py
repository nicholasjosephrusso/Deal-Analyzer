"""Mutable GameState with apply/undo semantics for DFS search.

Stock+waste are stored as a single ``deck`` list; ``cursor`` is the index of
the current top-of-waste (``-1`` = waste empty). A ``draw`` moves cursor +3
(clamped); ``recycle`` resets cursor to ``-1``; playing a card off the waste
pops ``deck[cursor]`` and decrements cursor by 1. This representation is
invariant under draw/recycle cycles (same physical pile) and so yields
correct state equivalence for the transposition table.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from solitaire_solver.cards import Card, Rank, Suit
from solitaire_solver.deal import Deal


@dataclass(slots=True)
class UndoToken:
    """Everything apply_move needs to restore the prior state in O(1)."""

    move_kind: int                  # one of MoveType ints (avoid circular import)
    prev_cursor: int
    src_pile: int = -1
    dst_pile: int = -1
    count: int = 1
    src_flipped_card: Card | None = None  # face-down card that got flipped by this move
    src_removed_from_deck_index: int = -1
    src_removed_card: Card | None = None
    prev_foundation_rank: int = -1


class GameState:
    __slots__ = (
        "foundations",
        "tableau_face_up",
        "tableau_face_down",
        "deck",
        "cursor",
        "recycles",
        "hidden_known",  # True if face-down identities are recorded (thoughtful mode)
    )

    def __init__(self) -> None:
        self.foundations: list[int] = [0, 0, 0, 0]  # indexed by Suit
        self.tableau_face_up: list[list[Card]] = [[] for _ in range(7)]
        self.tableau_face_down: list[list[Card]] = [[] for _ in range(7)]
        self.deck: list[Card] = []
        self.cursor: int = -1
        self.recycles: int = 0
        self.hidden_known: bool = True

    # ---------- Construction ----------

    @classmethod
    def from_deal(cls, deal: Deal) -> "GameState":
        if not deal.is_fully_known():
            raise ValueError(
                "GameState.from_deal requires a fully-known deal (thoughtful mode); "
                "supply identities for all face-down and stock cards."
            )
        s = cls()
        for i, pile in enumerate(deal.tableau):
            s.tableau_face_down[i] = [c for c in pile.face_down if c is not None]
            s.tableau_face_up[i] = list(pile.face_up)
        # deck_order: waste bottom..top + stock next..last
        deck: list[Card] = []
        deck.extend(deal.waste)  # bottom-of-waste first
        deck.extend(c for c in deal.stock if c is not None)
        s.deck = deck
        s.cursor = len(deal.waste) - 1  # -1 if waste empty
        for key, top in deal.foundations.items():
            if top is not None:
                s.foundations[int(top.suit)] = int(top.rank)
        return s

    # ---------- Queries ----------

    def is_won(self) -> bool:
        return all(r == 13 for r in self.foundations)

    def waste_top(self) -> Card | None:
        if self.cursor < 0:
            return None
        return self.deck[self.cursor]

    def stock_has_cards(self) -> bool:
        return self.cursor < len(self.deck) - 1

    def waste_has_cards(self) -> bool:
        return self.cursor >= 0

    # ---------- Apply / undo ----------

    def apply_draw(self) -> UndoToken:
        prev = self.cursor
        new_cursor = prev + 3
        if new_cursor > len(self.deck) - 1:
            new_cursor = len(self.deck) - 1
        self.cursor = new_cursor
        return UndoToken(move_kind=1, prev_cursor=prev)

    def apply_recycle(self) -> UndoToken:
        prev = self.cursor
        self.cursor = -1
        self.recycles += 1
        return UndoToken(move_kind=2, prev_cursor=prev)

    def apply_waste_to_foundation(self) -> UndoToken:
        card = self.deck[self.cursor]
        prev_cursor = self.cursor
        prev_rank = self.foundations[int(card.suit)]
        del self.deck[self.cursor]
        self.cursor -= 1
        self.foundations[int(card.suit)] = int(card.rank)
        return UndoToken(
            move_kind=3,
            prev_cursor=prev_cursor,
            src_removed_from_deck_index=prev_cursor,
            src_removed_card=card,
            prev_foundation_rank=prev_rank,
        )

    def apply_waste_to_tableau(self, dst_pile: int) -> UndoToken:
        card = self.deck[self.cursor]
        prev_cursor = self.cursor
        del self.deck[self.cursor]
        self.cursor -= 1
        self.tableau_face_up[dst_pile].append(card)
        return UndoToken(
            move_kind=4,
            prev_cursor=prev_cursor,
            dst_pile=dst_pile,
            src_removed_from_deck_index=prev_cursor,
            src_removed_card=card,
        )

    def apply_tableau_to_foundation(self, src_pile: int) -> UndoToken:
        fu = self.tableau_face_up[src_pile]
        card = fu.pop()
        prev_rank = self.foundations[int(card.suit)]
        self.foundations[int(card.suit)] = int(card.rank)
        flipped: Card | None = None
        if not fu and self.tableau_face_down[src_pile]:
            flipped = self.tableau_face_down[src_pile].pop()
            fu.append(flipped)
        return UndoToken(
            move_kind=5,
            prev_cursor=self.cursor,
            src_pile=src_pile,
            src_flipped_card=flipped,
            src_removed_card=card,
            prev_foundation_rank=prev_rank,
        )

    def apply_tableau_to_tableau(self, src_pile: int, dst_pile: int, count: int) -> UndoToken:
        fu_src = self.tableau_face_up[src_pile]
        fu_dst = self.tableau_face_up[dst_pile]
        start = len(fu_src) - count
        moving = fu_src[start:]
        del fu_src[start:]
        fu_dst.extend(moving)
        flipped: Card | None = None
        if not fu_src and self.tableau_face_down[src_pile]:
            flipped = self.tableau_face_down[src_pile].pop()
            fu_src.append(flipped)
        return UndoToken(
            move_kind=6,
            prev_cursor=self.cursor,
            src_pile=src_pile,
            dst_pile=dst_pile,
            count=count,
            src_flipped_card=flipped,
        )

    def undo(self, tok: UndoToken) -> None:
        kind = tok.move_kind
        if kind == 1:  # draw
            self.cursor = tok.prev_cursor
        elif kind == 2:  # recycle
            self.cursor = tok.prev_cursor
            self.recycles -= 1
        elif kind == 3:  # waste -> foundation
            assert tok.src_removed_card is not None
            card = tok.src_removed_card
            self.foundations[int(card.suit)] = tok.prev_foundation_rank
            self.deck.insert(tok.src_removed_from_deck_index, card)
            self.cursor = tok.prev_cursor
        elif kind == 4:  # waste -> tableau
            assert tok.src_removed_card is not None
            self.tableau_face_up[tok.dst_pile].pop()
            self.deck.insert(tok.src_removed_from_deck_index, tok.src_removed_card)
            self.cursor = tok.prev_cursor
        elif kind == 5:  # tableau -> foundation
            fu = self.tableau_face_up[tok.src_pile]
            if tok.src_flipped_card is not None:
                flipped = fu.pop()
                self.tableau_face_down[tok.src_pile].append(flipped)
            assert tok.src_removed_card is not None
            fu.append(tok.src_removed_card)
            self.foundations[int(tok.src_removed_card.suit)] = tok.prev_foundation_rank
        elif kind == 6:  # tableau -> tableau
            fu_src = self.tableau_face_up[tok.src_pile]
            fu_dst = self.tableau_face_up[tok.dst_pile]
            if tok.src_flipped_card is not None:
                flipped = fu_src.pop()
                self.tableau_face_down[tok.src_pile].append(flipped)
            moving = fu_dst[-tok.count :]
            del fu_dst[-tok.count :]
            fu_src.extend(moving)
        else:
            raise AssertionError(f"unknown move_kind {kind}")

    # ---------- Canonical key for transposition table ----------

    def canonical_key(self) -> bytes:
        """Compact, canonical bytes representation of the full state.

        Empty tableau piles are made interchangeable by sorting piles by a
        deterministic key (pile contents) so symmetric placements collide.
        """
        parts: list[bytes] = []
        parts.append(bytes(self.foundations))                                  # 4 bytes, rank per suit
        # Tableau piles: sort by (face_down_count, face_up tuple) for symmetry dedup.
        piles = []
        for i in range(7):
            fd = self.tableau_face_down[i]
            fu = self.tableau_face_up[i]
            piles.append((len(fd), tuple(int(c) for c in fd), tuple(int(c) for c in fu)))
        piles.sort()
        for fd_count, fd, fu in piles:
            parts.append(bytes([fd_count, len(fu)]))
            parts.append(bytes(fd))
            parts.append(bytes(fu))
        # Deck + cursor: cursor encoded as 2 bytes (cursor + 1, allowing -1..255).
        parts.append(bytes([len(self.deck)]))
        parts.append(bytes(int(c) for c in self.deck))
        parts.append(bytes([self.cursor + 1]))
        return b"".join(parts)
