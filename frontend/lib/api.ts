import type { DealJson, SolveResponse } from "./types";

function apiBase(): string {
  // Client-side: prefer NEXT_PUBLIC_API_BASE, fallback to localhost for dev.
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  }
  return process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
}

export async function solveDeal(
  deal: DealJson,
  opts: { budgetSeconds?: number; budgetNodes?: number } = {}
): Promise<SolveResponse> {
  const res = await fetch(`${apiBase()}/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      deal,
      budget_seconds: opts.budgetSeconds ?? 30,
      budget_nodes: opts.budgetNodes ?? 1_000_000,
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`solve failed: HTTP ${res.status} ${text}`);
  }
  return res.json();
}

export async function randomDeal(seed?: number): Promise<{ seed: number; deal: DealJson; digest: string }> {
  const res = await fetch(`${apiBase()}/random-deal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seed: seed ?? null }),
  });
  if (!res.ok) throw new Error(`random-deal failed: HTTP ${res.status}`);
  return res.json();
}
