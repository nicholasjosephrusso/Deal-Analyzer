import json
from pathlib import Path

from solitaire_solver.cards import Card
from solitaire_solver.deal import deal_from_json, deal_to_json, load_deal
from solitaire_solver.moves import Move, MoveType
from solitaire_solver.serialize import (
    envelope,
    humanize_all,
    move_from_json,
    move_to_json,
)


FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_deal_json_roundtrip():
    deal = load_deal(FIXTURES / "deal_trivial.json")
    j = deal_to_json(deal)
    deal2 = deal_from_json(j)
    assert deal == deal2


def test_move_json_roundtrip_all_kinds():
    samples = [
        Move(mtype=MoveType.DRAW),
        Move(mtype=MoveType.RECYCLE),
        Move(mtype=MoveType.WASTE_TO_FOUNDATION, card=Card.parse("AH")),
        Move(mtype=MoveType.WASTE_TO_TABLEAU, dst_pile=3, card=Card.parse("5H")),
        Move(mtype=MoveType.TABLEAU_TO_FOUNDATION, src_pile=2, card=Card.parse("2S")),
        Move(
            mtype=MoveType.TABLEAU_TO_TABLEAU,
            src_pile=3,
            dst_pile=5,
            count=2,
            card=Card.parse("7C"),
        ),
        Move(mtype=MoveType.FLIP, src_pile=4, revealed_card=Card.parse("QD")),
    ]
    for m in samples:
        j = move_to_json(m)
        m2 = move_from_json(j)
        assert m2.mtype == m.mtype
        assert m2.src_pile == m.src_pile
        assert m2.dst_pile == m.dst_pile
        assert m2.count == m.count
        assert m2.card == m.card
        assert m2.revealed_card == m.revealed_card


def test_envelope_shape():
    env = envelope(
        deal_digest="sha256:abc",
        moves=[Move(mtype=MoveType.DRAW)],
        solved=True,
        node_count=100,
        elapsed_seconds=0.05,
    )
    assert env["version"] == "1.0"
    assert env["variant"] == "klondike-draw-3"
    assert env["initial_deal_id"] == "sha256:abc"
    assert env["solved"] is True
    assert env["moves"] == [{"type": "draw"}]


def test_humanize_runs_without_error():
    moves = [
        Move(mtype=MoveType.DRAW),
        Move(mtype=MoveType.WASTE_TO_FOUNDATION, card=Card.parse("KS")),
    ]
    s = humanize_all(moves)
    assert "draw" in s
    assert "KS" in s
