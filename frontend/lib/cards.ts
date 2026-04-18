import type { CardCode, SuitKey } from "./types";

export const SUIT_GLYPH: Record<SuitKey, string> = {
  S: "\u2660",
  H: "\u2665",
  D: "\u2666",
  C: "\u2663",
};

export const RED_SUITS: ReadonlySet<SuitKey> = new Set(["H", "D"]);

const RANK_CHAR: Record<number, string> = {
  1: "A",
  2: "2",
  3: "3",
  4: "4",
  5: "5",
  6: "6",
  7: "7",
  8: "8",
  9: "9",
  10: "T",
  11: "J",
  12: "Q",
  13: "K",
};

const RANK_FROM_CHAR: Record<string, number> = Object.fromEntries(
  Object.entries(RANK_CHAR).map(([k, v]) => [v, Number(k)])
);

export function makeCode(rank: number, suit: SuitKey): CardCode {
  return RANK_CHAR[rank] + suit;
}

export function parseCode(code: CardCode): { rank: number; suit: SuitKey } {
  const r = code[0];
  const s = code[1] as SuitKey;
  return { rank: RANK_FROM_CHAR[r], suit: s };
}

export function displayRank(rank: number): string {
  // "10" instead of "T" for readability.
  if (rank === 10) return "10";
  return RANK_CHAR[rank];
}

export function displayCode(code: CardCode): string {
  const { rank, suit } = parseCode(code);
  return displayRank(rank) + SUIT_GLYPH[suit];
}

export function isRed(code: CardCode): boolean {
  return RED_SUITS.has(code[1] as SuitKey);
}

export function fullDeck(): CardCode[] {
  const out: CardCode[] = [];
  for (const suit of ["S", "H", "D", "C"] as const) {
    for (let r = 1; r <= 13; r++) out.push(makeCode(r, suit));
  }
  return out;
}
