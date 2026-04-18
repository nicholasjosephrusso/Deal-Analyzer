from solitaire_solver.cards import (
    Card,
    Color,
    Rank,
    Suit,
    full_deck,
    opposite_colors,
)


def test_all_52_ids_parse_roundtrip():
    for i in range(52):
        c = Card(i)
        assert Card.parse(c.code()) == c
        assert int(c) == i


def test_rank_suit_color():
    c = Card.parse("AS")
    assert c.rank == Rank.ACE
    assert c.suit == Suit.SPADES
    assert c.color == Color.BLACK

    c = Card.parse("KH")
    assert c.rank == Rank.KING
    assert c.suit == Suit.HEARTS
    assert c.color == Color.RED


def test_opposite_colors():
    assert opposite_colors(Card.parse("5S"), Card.parse("6H"))
    assert not opposite_colors(Card.parse("5S"), Card.parse("6C"))


def test_full_deck_is_52_unique():
    deck = full_deck()
    assert len(deck) == 52
    assert len({int(c) for c in deck}) == 52
