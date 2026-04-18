"""Command-line entry point.

Examples:
    python -m solitaire_solver.cli --deal fixtures/deal_00001.json --human
    python -m solitaire_solver.cli --deal fixtures/deal_00001.json --out /tmp/sol.json
    python -m solitaire_solver.cli --verify --deal fixtures/deal_00001.json --moves /tmp/sol.json
"""

from __future__ import annotations

import argparse
import sys

from solitaire_solver.deal import load_deal
from solitaire_solver.serialize import (
    envelope,
    humanize_all,
    read_moves,
    write_envelope,
)
from solitaire_solver.simulator import verify_solution
from solitaire_solver.solver import (
    DEFAULT_BUDGET_NODES,
    DEFAULT_BUDGET_SECONDS,
    solve,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="solitaire_solver")
    p.add_argument("--deal", required=True, help="Path to deal JSON")
    p.add_argument("--out", help="Write solution envelope JSON to this path")
    p.add_argument("--human", action="store_true", help="Print human-readable move list")
    p.add_argument("--budget-seconds", type=float, default=DEFAULT_BUDGET_SECONDS)
    p.add_argument("--budget-nodes", type=int, default=DEFAULT_BUDGET_NODES)
    p.add_argument("--verify", action="store_true", help="Verify an existing moves file instead of solving")
    p.add_argument("--moves", help="Path to moves envelope JSON (required with --verify)")
    args = p.parse_args(argv)

    deal = load_deal(args.deal)

    if args.verify:
        if not args.moves:
            p.error("--verify requires --moves")
        moves = read_moves(args.moves)
        result = verify_solution(deal, moves)
        if result.ok:
            print(f"OK: {result.moves_applied} moves replay legally; foundations complete.")
            return 0
        print(f"FAIL: {result.reason}", file=sys.stderr)
        return 1

    result = solve(
        deal,
        budget_seconds=args.budget_seconds,
        budget_nodes=args.budget_nodes,
    )

    if result.solved:
        print(
            f"Solved in {result.elapsed_seconds:.3f}s, "
            f"{result.node_count} nodes, {len(result.moves)} moves"
        )
        if args.human:
            print(humanize_all(result.moves))
        if args.out:
            env = envelope(
                deal_digest=deal.digest(),
                moves=result.moves,
                solved=True,
                node_count=result.node_count,
                elapsed_seconds=result.elapsed_seconds,
            )
            write_envelope(args.out, env)
            print(f"Solution written to {args.out}")
        return 0

    print(
        f"Not solved after {result.elapsed_seconds:.3f}s, "
        f"{result.node_count} nodes. Reason: {result.reason}",
        file=sys.stderr,
    )
    if args.out:
        env = envelope(
            deal_digest=deal.digest(),
            moves=[],
            solved=False,
            node_count=result.node_count,
            elapsed_seconds=result.elapsed_seconds,
        )
        write_envelope(args.out, env)
    return 2 if result.aborted else 3


if __name__ == "__main__":
    raise SystemExit(main())
