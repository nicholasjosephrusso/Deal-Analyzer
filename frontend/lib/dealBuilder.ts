import { fullDeck } from "./cards";
import type { CardCode, DealJson, SuitKey } from "./types";

// Dealing-order slots: T0 gets 1, T1 gets 2, ..., T6 gets 7. Then 24 stock cards.
// Within a tableau pile: positions 0..n-2 are face-down, position n-1 is face-up.
export type Slot =
  | { kind: "tableau"; pile: number; index: number; faceUp: boolean }
  | { kind: "stock"; index: number };

export function allSlots(): Slot[] {
  const slots: Slot[] = [];
  for (let pile = 0; pile < 7; pile++) {
    for (let index = 0; index <= pile; index++) {
      slots.push({
        kind: "tableau",
        pile,
        index,
        faceUp: index === pile, // top of the pile is face-up
      });
    }
  }
  for (let index = 0; index < 24; index++) {
    slots.push({ kind: "stock", index });
  }
  return slots;
}

export type DealState = {
  tableau: Array<Array<CardCode | null>>; // tableau[pile] = (pile+1)-length array
  stock: Array<CardCode | null>;           // length 24
};

export function emptyDealState(): DealState {
  return {
    tableau: Array.from({ length: 7 }, (_, i) => Array(i + 1).fill(null)),
    stock: Array(24).fill(null),
  };
}

export function getSlot(state: DealState, slot: Slot): CardCode | null {
  if (slot.kind === "tableau") return state.tableau[slot.pile][slot.index];
  return state.stock[slot.index];
}

export function setSlot(state: DealState, slot: Slot, card: CardCode | null): DealState {
  if (slot.kind === "tableau") {
    const next = state.tableau.map((p) => [...p]);
    next[slot.pile][slot.index] = card;
    return { ...state, tableau: next };
  }
  const nextStock = [...state.stock];
  nextStock[slot.index] = card;
  return { ...state, stock: nextStock };
}

export function usedCards(state: DealState): Set<CardCode> {
  const s = new Set<CardCode>();
  for (const pile of state.tableau) for (const c of pile) if (c) s.add(c);
  for (const c of state.stock) if (c) s.add(c);
  return s;
}

export function emptySlots(state: DealState): Slot[] {
  return allSlots().filter((slot) => getSlot(state, slot) === null);
}

export function firstEmptySlot(state: DealState): Slot | null {
  return emptySlots(state)[0] ?? null;
}

export function isComplete(state: DealState): boolean {
  return emptySlots(state).length === 0;
}

function shuffled<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export function fillRemainingRandomly(state: DealState): DealState {
  const used = usedCards(state);
  const pool = shuffled(fullDeck().filter((c) => !used.has(c)));
  let next = state;
  for (const slot of emptySlots(next)) {
    const card = pool.shift();
    if (!card) throw new Error("ran out of cards while auto-filling");
    next = setSlot(next, slot, card);
  }
  return next;
}

export function toDealJson(state: DealState): DealJson {
  if (!isComplete(state)) throw new Error("deal is not complete");
  const foundations: Record<SuitKey, string | null> = { S: null, H: null, D: null, C: null };
  return {
    tableau: state.tableau.map((pile) => ({
      face_down: pile.slice(0, -1),
      face_up: pile.slice(-1) as string[],
    })),
    stock: state.stock,
    waste: [],
    foundations,
    draw_count: 3,
    metadata: {},
  };
}

export function fromDealJson(deal: DealJson): DealState {
  const tableau = deal.tableau.map((p) => [...p.face_down, ...p.face_up] as Array<CardCode | null>);
  const stock = [...deal.stock] as Array<CardCode | null>;
  return { tableau, stock };
}
