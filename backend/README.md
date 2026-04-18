# Klondike Solver Backend

FastAPI service wrapping `solitaire_solver` (thoughtful Klondike draw-3 solver).

## Endpoints

| Method | Path            | Description                                                                |
| ------ | --------------- | -------------------------------------------------------------------------- |
| `GET`  | `/health`       | Liveness probe. Returns `{"status": "ok"}`.                                |
| `POST` | `/random-deal`  | `{seed?: int}` → returns a random fully-known deal + its digest.           |
| `POST` | `/solve`        | `{deal, budget_seconds?, budget_nodes?}` → solution + per-step snapshots.  |

The `/solve` response includes:

- `moves`: the raw move list (wire format from `solitaire_solver.serialize.move_to_json`)
- `move_descriptions`: human-readable strings, one per move
- `snapshots`: board state **after** each move (`snapshots[0]` is the initial deal); the frontend renders these directly instead of replaying moves in TS

## Run locally

From the **repo root** (so the `solitaire_solver` package is importable):

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Then hit `http://localhost:8000/health`.

The solver itself uses only the Python stdlib, so `backend/requirements.txt`
(fastapi + uvicorn + pydantic) is all you need.

## Deploy

This is a stateless Python service. It runs on anything that runs a Python process:

- **Fly.io**: `fly launch` in the repo root with a Dockerfile that pip-installs both `requirements.txt` files and runs `uvicorn backend.main:app --host 0.0.0.0 --port 8080`.
- **Render / Railway**: point them at the repo, set the start command to `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- **Cloud Run**: wrap in a Dockerfile exposing `$PORT`.

Set `NEXT_PUBLIC_API_BASE` on the frontend to the deployed URL.

## Notes

- CORS is wide-open (`allow_origins=["*"]`) because this is a trainer app for a single user. Tighten with an allowlist if you deploy multi-tenant.
- The solver is CPU-bound; a hard deal can pin a core for the full `budget_seconds`. For a public endpoint you'd put this behind a request queue or lower the budget.
