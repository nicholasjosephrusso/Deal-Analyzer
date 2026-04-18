# Solver Fixtures

- `deal_trivial.json` — A deal one move from winning. The King of Spades is the only non-foundation card; drawing it off the stock and auto-playing wins. Used as the smoke-test fixture for the CLI and solver.

Additional fixtures (randomly seeded full deals, published hard/unsolvable cases) can be generated with `solitaire_solver.deal.make_random_deal(seed)` and saved via `deal_to_json`.
