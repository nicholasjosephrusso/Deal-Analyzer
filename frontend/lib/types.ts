export type SuitKey = "S" | "H" | "D" | "C";
export const SUITS: SuitKey[] = ["S", "H", "D", "C"];
export const RANKS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13] as const;

export type CardCode = string; // e.g. "AS", "TD", "QH"

export type TableauSlot = {
  faceDown: Array<CardCode | null>; // bottom -> top
  faceUp: Array<CardCode | null>;   // bottom -> top (only the LAST card really face-up initially)
};

export type DealJson = {
  tableau: Array<{ face_down: (string | null)[]; face_up: string[] }>;
  stock: (string | null)[];
  waste: string[];
  foundations: Record<SuitKey, string | null>;
  draw_count: number;
  metadata?: Record<string, unknown>;
};

export type Snapshot = {
  foundations: Record<SuitKey, number>;
  stock_count: number;
  waste_visible: CardCode[];
  tableau: Array<{ face_down: number; face_up: CardCode[] }>;
  is_won: boolean;
};

export type SolveResponse = {
  version: string;
  variant: string;
  initial_deal_id: string;
  solved: boolean;
  reason?: string;
  node_count: number;
  elapsed_seconds: number;
  wall_seconds?: number;
  moves: unknown[];
  move_descriptions: string[];
  snapshots: Snapshot[];
};
