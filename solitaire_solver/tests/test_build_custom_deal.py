import pytest

from solitaire_solver.deal import build_custom_deal, make_random_deal


def _tableau_rows_from_deal(deal):
    rows = []
    for pile in deal.tableau:
        cards = list(pile.face_down) + list(pile.face_up)
        rows.append(" ".join(c.code() for c in cards))
    return rows


def test_build_custom_deal_roundtrip_matches_seeded():
    original = make_random_deal(seed=42)
    rows = _tableau_rows_from_deal(original)
    stock_text = " ".join(c.code() for c in original.stock)
    rebuilt = build_custom_deal(rows, stock_text)
    assert rebuilt == original


def test_build_custom_deal_accepts_10_and_t_notation():
    original = make_random_deal(seed=7)
    rows = _tableau_rows_from_deal(original)
    rows = [r.replace("TH", "10H").replace("TD", "10D") for r in rows]
    stock_text = " ".join(c.code() for c in original.stock).replace("TS", "10S")
    rebuilt = build_custom_deal(rows, stock_text)
    assert rebuilt == original


def test_build_custom_deal_rejects_wrong_card_count():
    rows = ["AS", "2H 3C", "4D 5S 6H", "7C 8D 9S TH",
            "JC QH KS AD 2C", "3H 4S 5D 6C 7H 8S",
            "9D 10C JH QS KD AC 2D"]
    # Missing one stock card.
    with pytest.raises(ValueError, match="Stock"):
        build_custom_deal(rows, "3S 4H 5C 6D 7S 8H 9C TD JS QC KH AH 2S 3D 4C 5H 6S 7D 8C 9H TS JD QC")


def test_build_custom_deal_rejects_wrong_tableau_count():
    # T3 should have 4 cards, not 3.
    rows = ["AS", "2H 3C", "4D 5S 6H", "7C 8D 9S",
            "JC QH KS AD 2C", "3H 4S 5D 6C 7H 8S",
            "9D 10C JH QS KD AC 2D"]
    stock = "3S 4H 5C 6D 7S 8H 9C TD JS QC KH AH 2S 3D 4C 5H 6S 7D 8C 9H TS JD QC KS 10H"
    with pytest.raises(ValueError, match="Tableau T3"):
        build_custom_deal(rows, stock)


def test_build_custom_deal_rejects_duplicates():
    original = make_random_deal(seed=3)
    rows = _tableau_rows_from_deal(original)
    # Replace first card of T1 with the already-used card from T0.
    t0_card = rows[0].split()[0]
    t1 = rows[1].split()
    t1[0] = t0_card
    rows[1] = " ".join(t1)
    stock_text = " ".join(c.code() for c in original.stock)
    with pytest.raises(ValueError, match="duplicate"):
        build_custom_deal(rows, stock_text)


def test_build_custom_deal_rejects_bad_code():
    rows = ["ZZ"] + [""] * 6
    with pytest.raises(ValueError, match="Tableau T0"):
        build_custom_deal(rows, "")
