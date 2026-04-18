"use client";

import { useMemo, useState } from "react";
import { Card } from "./Card";
import { SUIT_GLYPH, fullDeck, parseCode } from "@/lib/cards";
import {
  type DealState,
  type Slot,
  emptyDealState,
  fillRemainingRandomly,
  firstEmptySlot,
  getSlot,
  isComplete,
  setSlot,
  usedCards,
} from "@/lib/dealBuilder";
import type { CardCode, SuitKey } from "@/lib/types";

type Props = {
  onSubmit: (state: DealState) => void;
  onReplaceState?: (state: DealState) => void; // e.g. load a random deal
  initial?: DealState;
};

/**
 * Two-tap deal entry:
 *   1. Tap an empty slot on the board (or use the auto-selected next empty slot).
 *   2. Tap a card in the deck grid; it fills the slot and selection advances.
 * "Fill rest randomly" completes the deal without manual entry for the remaining slots.
 */
export function DealBuilder({ onSubmit, onReplaceState, initial }: Props) {
  const [state, setState] = useState<DealState>(initial ?? emptyDealState());
  const [selected, setSelected] = useState<Slot | null>(firstEmptySlot(state));

  const used = useMemo(() => usedCards(state), [state]);

  function selectSlot(slot: Slot) {
    setSelected(slot);
  }

  function placeCard(code: CardCode) {
    const slot = selected ?? firstEmptySlot(state);
    if (!slot) return;
    const next = setSlot(state, slot, code);
    setState(next);
    setSelected(firstEmptySlot(next));
  }

  function clearSlot(slot: Slot) {
    const next = setSlot(state, slot, null);
    setState(next);
    setSelected(slot);
  }

  function resetAll() {
    const blank = emptyDealState();
    setState(blank);
    setSelected(firstEmptySlot(blank));
  }

  function fillRandom() {
    const next = fillRemainingRandomly(state);
    setState(next);
    setSelected(null);
    onReplaceState?.(next);
  }

  const complete = isComplete(state);

  return (
    <div className="flex flex-col gap-4">
      <div className="text-white/80 text-sm">
        Tap a slot, then tap a card. The <b>top</b> card of each pile is face-up
        (what you see in a real game). When you&apos;re done &mdash; or tap{" "}
        <b>Fill rest randomly</b> &mdash; hit <b>Solve</b>.
      </div>

      {/* Tableau layout */}
      <div className="overflow-x-auto -mx-2 px-2">
        <div className="flex gap-2 min-w-max justify-center">
          {state.tableau.map((pile, pi) => (
            <PileColumn
              key={pi}
              pileIndex={pi}
              pile={pile}
              selected={selected}
              onSelectSlot={selectSlot}
              onClearSlot={clearSlot}
            />
          ))}
        </div>
      </div>

      {/* Stock row */}
      <div>
        <div className="text-xs text-white/60 mb-1">
          Stock (24 cards, draw order)
        </div>
        <div className="overflow-x-auto -mx-2 px-2">
          <div className="flex gap-1 min-w-max">
            {state.stock.map((c, i) => {
              const slot: Slot = { kind: "stock", index: i };
              const isSel =
                selected?.kind === "stock" && selected.index === i;
              return (
                <Card
                  key={i}
                  code={c ?? undefined}
                  empty={c === null}
                  placeholder=""
                  facedown={false}
                  selected={isSel}
                  size="sm"
                  onClick={() => (c ? clearSlot(slot) : selectSlot(slot))}
                />
              );
            })}
          </div>
        </div>
      </div>

      {/* Deck picker */}
      <div>
        <div className="text-xs text-white/60 mb-1">
          Deck (tap a card to place it in the selected slot)
        </div>
        <DeckGrid used={used} onPick={placeCard} />
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 safe-bottom">
        <button
          onClick={resetAll}
          className="py-3 rounded-lg bg-white/10 active:bg-white/20 font-semibold"
        >
          Reset
        </button>
        <button
          onClick={fillRandom}
          className="py-3 rounded-lg bg-white/10 active:bg-white/20 font-semibold"
        >
          Fill rest randomly
        </button>
        <button
          onClick={() => onSubmit(state)}
          disabled={!complete}
          className="col-span-2 sm:col-span-1 py-3 rounded-lg bg-emerald-500 disabled:bg-white/10 disabled:text-white/40 font-semibold text-black disabled:text-white/40"
        >
          Solve
        </button>
      </div>
    </div>
  );
}

function PileColumn({
  pileIndex,
  pile,
  selected,
  onSelectSlot,
  onClearSlot,
}: {
  pileIndex: number;
  pile: Array<CardCode | null>;
  selected: Slot | null;
  onSelectSlot: (s: Slot) => void;
  onClearSlot: (s: Slot) => void;
}) {
  return (
    <div className="flex flex-col items-center min-w-[46px] sm:min-w-[52px]">
      <div className="text-[10px] text-white/60 mb-1">T{pileIndex}</div>
      <div className="flex flex-col gap-1">
        {pile.map((code, i) => {
          const slot: Slot = {
            kind: "tableau",
            pile: pileIndex,
            index: i,
            faceUp: i === pile.length - 1,
          };
          const isSel =
            selected?.kind === "tableau" &&
            selected.pile === pileIndex &&
            selected.index === i;
          const facedown = code !== null && i !== pile.length - 1;
          return (
            <Card
              key={i}
              code={code ?? undefined}
              empty={code === null}
              placeholder={i === pile.length - 1 ? "\u2605" : ""}
              facedown={facedown}
              selected={isSel}
              onClick={() => (code ? onClearSlot(slot) : onSelectSlot(slot))}
            />
          );
        })}
      </div>
    </div>
  );
}

function DeckGrid({
  used,
  onPick,
}: {
  used: Set<CardCode>;
  onPick: (code: CardCode) => void;
}) {
  const rows: { suit: SuitKey; cards: CardCode[] }[] = [
    { suit: "S", cards: [] },
    { suit: "H", cards: [] },
    { suit: "D", cards: [] },
    { suit: "C", cards: [] },
  ];
  for (const c of fullDeck()) {
    const { suit } = parseCode(c);
    rows.find((r) => r.suit === suit)!.cards.push(c);
  }
  return (
    <div className="flex flex-col gap-1">
      {rows.map((row) => (
        <div key={row.suit} className="flex gap-1 items-center">
          <div
            className={`w-5 text-center text-lg ${
              row.suit === "H" || row.suit === "D"
                ? "text-card-red"
                : "text-white"
            }`}
          >
            {SUIT_GLYPH[row.suit]}
          </div>
          <div className="flex gap-1 overflow-x-auto">
            {row.cards.map((c) => {
              const isUsed = used.has(c);
              return (
                <Card
                  key={c}
                  code={c}
                  size="sm"
                  className={isUsed ? "opacity-25" : ""}
                  onClick={isUsed ? undefined : () => onPick(c)}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
