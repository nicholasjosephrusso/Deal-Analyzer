"""Card primitives: Suit, Rank, Color, Card.

A Card is encoded as an int in [0, 52): ``suit_index * 13 + (rank - 1)``.
Two-char string codes use ``{A,2,3,4,5,6,7,8,9,T,J,Q,K}`` for rank and
``{S,H,D,C}`` for suit.
"""

from __future__ import annotations

from enum import IntEnum


class Suit(IntEnum):
    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3


class Color(IntEnum):
    BLACK = 0
    RED = 1


class Rank(IntEnum):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13


SUIT_CHARS = "SHDC"
RANK_CHARS = "A23456789TJQK"

_SUIT_FROM_CHAR = {c: Suit(i) for i, c in enumerate(SUIT_CHARS)}
_RANK_FROM_CHAR = {c: Rank(i + 1) for i, c in enumerate(RANK_CHARS)}

_SUIT_COLOR = {
    Suit.SPADES: Color.BLACK,
    Suit.CLUBS: Color.BLACK,
    Suit.HEARTS: Color.RED,
    Suit.DIAMONDS: Color.RED,
}


class Card(int):
    """Card is an int 0..51. Stored as ``suit * 13 + (rank - 1)``."""

    __slots__ = ()

    def __new__(cls, value: int) -> "Card":
        if not 0 <= int(value) < 52:
            raise ValueError(f"Card id out of range: {value}")
        return super().__new__(cls, int(value))

    @classmethod
    def of(cls, rank: int | Rank, suit: int | Suit) -> "Card":
        return cls(int(suit) * 13 + int(rank) - 1)

    @classmethod
    def parse(cls, s: str) -> "Card":
        if len(s) != 2:
            raise ValueError(f"Expected 2-char card code, got {s!r}")
        rank_char, suit_char = s[0].upper(), s[1].upper()
        if rank_char not in _RANK_FROM_CHAR or suit_char not in _SUIT_FROM_CHAR:
            raise ValueError(f"Unparseable card code {s!r}")
        return cls.of(_RANK_FROM_CHAR[rank_char], _SUIT_FROM_CHAR[suit_char])

    @property
    def rank(self) -> Rank:
        return Rank((int(self) % 13) + 1)

    @property
    def suit(self) -> Suit:
        return Suit(int(self) // 13)

    @property
    def color(self) -> Color:
        return _SUIT_COLOR[self.suit]

    def code(self) -> str:
        return RANK_CHARS[int(self.rank) - 1] + SUIT_CHARS[int(self.suit)]

    def __repr__(self) -> str:
        return self.code()

    def __str__(self) -> str:
        return self.code()


def full_deck() -> tuple[Card, ...]:
    return tuple(Card(i) for i in range(52))


def opposite_colors(a: Card, b: Card) -> bool:
    return a.color != b.color
