"""Deal: the CV input contract.

The computer-vision layer produces a ``Deal``; the solver consumes it. Unknown
cards are permitted only in ``TableauPile.face_down`` and ``Deal.stock``; in
"thoughtful" mode the solver rejects Deals with any unknowns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from solitaire_solver.cards import Card, Rank, Suit, SUIT_CHARS, full_deck


@dataclass(frozen=True)
class TableauPile:
    face_down: tuple[Card | None, ...]  # bottom -> top; None = unidentified
    face_up: tuple[Card, ...]            # bottom -> top; must be identified


@dataclass(frozen=True)
class Deal:
    tableau: tuple[TableauPile, ...]          # length 7
    stock: tuple[Card | None, ...]            # next-drawn first; None = unknown
    waste: tuple[Card, ...]                   # bottom -> top
    foundations: dict[str, Card | None]       # keys S,H,D,C; top card or None
    draw_count: int = 3
    metadata: dict = field(default_factory=dict)

    def validate(self) -> None:
        if len(self.tableau) != 7:
            raise ValueError(f"expected 7 tableau piles, got {len(self.tableau)}")
        if self.draw_count != 3:
            raise ValueError(f"only draw_count=3 supported, got {self.draw_count}")
        for key in ("S", "H", "D", "C"):
            if key not in self.foundations:
                raise ValueError(f"foundation {key!r} missing")
        seen: set[int] = set()
        total = 0
        for pile in self.tableau:
            for c in pile.face_down:
                total += 1
                if c is not None:
                    if int(c) in seen:
                        raise ValueError(f"duplicate card {c}")
                    seen.add(int(c))
            for c in pile.face_up:
                total += 1
                if int(c) in seen:
                    raise ValueError(f"duplicate card {c}")
                seen.add(int(c))
            _validate_face_up_run(pile.face_up)
        for c in self.stock:
            total += 1
            if c is not None:
                if int(c) in seen:
                    raise ValueError(f"duplicate card {c}")
                seen.add(int(c))
        for c in self.waste:
            total += 1
            if int(c) in seen:
                raise ValueError(f"duplicate card {c}")
            seen.add(int(c))
        for suit_key, top in self.foundations.items():
            if top is None:
                continue
            if top.suit.name[0] != suit_key:
                raise ValueError(f"foundation {suit_key} has wrong-suit card {top}")
            total += int(top.rank)  # ace = 1 card, 2 = 2 cards, ...
            for r in range(1, int(top.rank) + 1):
                card = Card.of(r, _suit_from_key(suit_key))
                if int(card) in seen:
                    raise ValueError(f"card {card} appears both on foundation and elsewhere")
                seen.add(int(card))
        if total != 52:
            raise ValueError(f"expected 52 cards total, got {total}")

    def is_fully_known(self) -> bool:
        for pile in self.tableau:
            if any(c is None for c in pile.face_down):
                return False
        return not any(c is None for c in self.stock)

    def digest(self) -> str:
        """Stable SHA-256 of the full deal, for tagging solutions."""
        import hashlib
        payload = json.dumps(deal_to_json(self), sort_keys=True).encode()
        return "sha256:" + hashlib.sha256(payload).hexdigest()


def _suit_from_key(key: str) -> Suit:
    return Suit(SUIT_CHARS.index(key))


def _validate_face_up_run(cards: tuple[Card, ...]) -> None:
    for lower, upper in zip(cards[1:], cards[:-1]):
        # `upper` is beneath `lower` in the visual pile (bottom->top ordering),
        # so upper should have rank = lower.rank + 1 and opposite color.
        if int(upper.rank) != int(lower.rank) + 1:
            raise ValueError(f"illegal tableau run: {upper} beneath {lower}")
        if upper.color == lower.color:
            raise ValueError(f"illegal tableau run (same color): {upper}/{lower}")


# ---------- JSON (de)serialization ----------


def _card_or_none(v: Any) -> Card | None:
    if v is None:
        return None
    return Card.parse(v)


def deal_from_json(obj: dict) -> Deal:
    tableau = tuple(
        TableauPile(
            face_down=tuple(_card_or_none(c) for c in pile.get("face_down", [])),
            face_up=tuple(Card.parse(c) for c in pile.get("face_up", [])),
        )
        for pile in obj["tableau"]
    )
    stock = tuple(_card_or_none(c) for c in obj.get("stock", []))
    waste = tuple(Card.parse(c) for c in obj.get("waste", []))
    foundations = {
        k: _card_or_none(obj.get("foundations", {}).get(k))
        for k in ("S", "H", "D", "C")
    }
    draw_count = int(obj.get("draw_count", 3))
    metadata = dict(obj.get("metadata", {}))
    deal = Deal(
        tableau=tableau,
        stock=stock,
        waste=waste,
        foundations=foundations,
        draw_count=draw_count,
        metadata=metadata,
    )
    deal.validate()
    return deal


def deal_to_json(deal: Deal) -> dict:
    return {
        "tableau": [
            {
                "face_down": [None if c is None else c.code() for c in pile.face_down],
                "face_up": [c.code() for c in pile.face_up],
            }
            for pile in deal.tableau
        ],
        "stock": [None if c is None else c.code() for c in deal.stock],
        "waste": [c.code() for c in deal.waste],
        "foundations": {k: (v.code() if v is not None else None) for k, v in deal.foundations.items()},
        "draw_count": deal.draw_count,
        "metadata": deal.metadata,
    }


def load_deal(path: str | Path) -> Deal:
    with open(path) as f:
        return deal_from_json(json.load(f))


# ---------- Synthesis helpers ----------


def make_random_deal(seed: int) -> Deal:
    """Deal from a seeded shuffle of the full 52-card deck. Fully known."""
    import random

    rng = random.Random(seed)
    deck = list(full_deck())
    rng.shuffle(deck)
    return deal_from_shuffled_deck(deck)


def deal_from_shuffled_deck(deck: list[Card]) -> Deal:
    """Deal Klondike from a 52-card ordered list (first card dealt first).

    Standard layout: pile i (0..6) gets i+1 cards; the top card of each pile is
    face-up, the rest are face-down. The remaining 24 cards become the stock
    (first element = next to draw).
    """
    if len(deck) != 52:
        raise ValueError("deck must have exactly 52 cards")
    if len(set(map(int, deck))) != 52:
        raise ValueError("deck has duplicate cards")
    idx = 0
    piles: list[TableauPile] = []
    for i in range(7):
        chunk = deck[idx : idx + i + 1]
        idx += i + 1
        face_down = tuple(chunk[:-1])
        face_up = (chunk[-1],)
        piles.append(TableauPile(face_down=face_down, face_up=face_up))
    stock = tuple(deck[idx:])
    foundations = {k: None for k in ("S", "H", "D", "C")}
    deal = Deal(
        tableau=tuple(piles),
        stock=stock,
        waste=(),
        foundations=foundations,
        draw_count=3,
        metadata={},
    )
    deal.validate()
    return deal


def _parse_cards(text: str, *, expected: int, context: str) -> list[Card]:
    """Parse whitespace/comma-separated card codes. Accepts ``10H`` or ``TH``."""
    tokens = [t for t in text.replace(",", " ").split() if t]
    cards: list[Card] = []
    for tok in tokens:
        code = tok.upper()
        if len(code) == 3 and code.startswith("10"):
            code = "T" + code[2]
        try:
            cards.append(Card.parse(code))
        except ValueError as e:
            raise ValueError(f"{context}: {e}") from None
    if len(cards) != expected:
        raise ValueError(
            f"{context}: expected {expected} card(s), got {len(cards)}"
        )
    return cards


def build_custom_deal(tableau_texts: list[str], stock_text: str) -> Deal:
    """Assemble a fully-known Deal from seven tableau rows + a 24-card stock.

    Each tableau row is a space-separated list of card codes, bottom-to-top.
    The LAST card in each row is the face-up card; the rest are face-down.
    Foundations start empty, waste starts empty.
    """
    if len(tableau_texts) != 7:
        raise ValueError("Expected 7 tableau rows")
    piles: list[TableauPile] = []
    for i, txt in enumerate(tableau_texts):
        cards = _parse_cards(txt, expected=i + 1, context=f"Tableau T{i}")
        piles.append(
            TableauPile(face_down=tuple(cards[:-1]), face_up=(cards[-1],))
        )
    stock_cards = _parse_cards(stock_text, expected=24, context="Stock")
    deal = Deal(
        tableau=tuple(piles),
        stock=tuple(stock_cards),
        waste=(),
        foundations={k: None for k in ("S", "H", "D", "C")},
        draw_count=3,
    )
    deal.validate()
    return deal
