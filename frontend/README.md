# Klondike Trainer (PWA)

Next.js 14 app for the Klondike draw-3 trainer. Talks to the `backend/` FastAPI
service — design a deal, solve it, watch the solution play out.

## Develop

```bash
# start the Python backend first (see ../backend/README.md)
uvicorn backend.main:app --reload

# then, in another terminal:
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

Set `NEXT_PUBLIC_API_BASE` if the backend isn't on `http://localhost:8000`:

```bash
NEXT_PUBLIC_API_BASE=https://your-api.example.com npm run dev
```

## Build & run

```bash
npm run build
npm run start
```

## Deploy

- **Vercel**: import the repo, set the project root to `frontend`, add
  `NEXT_PUBLIC_API_BASE` as an env var pointing at the backend.
- **Any static host**: `next build && next start` produces a Node server;
  `next build && next export` isn't compatible because we use client-only
  features, but a Node host (Render / Railway / Fly) works.

## Install as a PWA on iOS/Android

Open the site in mobile Safari / Chrome and hit **Share → Add to Home Screen**.
`public/manifest.json` declares `display: standalone` so it launches without
browser chrome once installed.

## Structure

```
app/
  layout.tsx          root HTML + metadata + PWA hooks
  page.tsx            setup → solving → playback state machine
  globals.css         Tailwind + safe-area helpers
components/
  Card.tsx            single card (face-up / face-down / empty)
  DealBuilder.tsx     tap-slot-tap-card deal entry + "fill rest randomly"
  Board.tsx           board renderer driven by a Snapshot
  Playback.tsx        Prev/Next/Play/slider + full move list
lib/
  cards.ts            card codes, glyphs, display helpers
  dealBuilder.ts      slot model, dealstate, random-fill, to/from DealJson
  api.ts              fetch client (POST /solve, POST /random-deal)
  types.ts            shared wire types
```
