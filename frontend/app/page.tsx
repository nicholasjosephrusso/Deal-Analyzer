"use client";

import { useState } from "react";
import { DealBuilder } from "@/components/DealBuilder";
import { Playback } from "@/components/Playback";
import { solveDeal, randomDeal } from "@/lib/api";
import { fromDealJson, toDealJson, type DealState } from "@/lib/dealBuilder";
import type { SolveResponse } from "@/lib/types";

type Phase =
  | { kind: "setup"; initial?: DealState }
  | { kind: "solving" }
  | { kind: "result"; solution: SolveResponse; lastState: DealState }
  | { kind: "error"; message: string; lastState?: DealState };

export default function HomePage() {
  const [phase, setPhase] = useState<Phase>({ kind: "setup" });
  const [budgetSeconds, setBudgetSeconds] = useState(30);

  async function handleSolve(state: DealState) {
    setPhase({ kind: "solving" });
    try {
      const deal = toDealJson(state);
      const solution = await solveDeal(deal, { budgetSeconds });
      setPhase({ kind: "result", solution, lastState: state });
    } catch (e: any) {
      setPhase({ kind: "error", message: e?.message ?? String(e), lastState: state });
    }
  }

  async function handleRandom() {
    try {
      const { deal } = await randomDeal();
      const state = fromDealJson(deal);
      setPhase({ kind: "setup", initial: state });
    } catch (e: any) {
      setPhase({ kind: "error", message: e?.message ?? String(e) });
    }
  }

  if (phase.kind === "solving") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-6">
        <div className="text-lg font-semibold">Searching for a solution…</div>
        <div className="text-sm text-white/60">
          Up to {budgetSeconds}s. Hard deals may time out.
        </div>
        <div className="w-12 h-12 border-4 border-white/30 border-t-emerald-400 rounded-full animate-spin" />
      </div>
    );
  }

  if (phase.kind === "result") {
    return (
      <Playback
        solution={phase.solution}
        onBack={() => setPhase({ kind: "setup", initial: phase.lastState })}
      />
    );
  }

  return (
    <div className="min-h-screen p-3 safe-top safe-bottom">
      <header className="flex items-center justify-between mb-3">
        <h1 className="text-xl font-bold">🃏 Klondike Trainer</h1>
        <button
          onClick={handleRandom}
          className="px-3 py-2 rounded-lg bg-white/10 active:bg-white/20 text-sm"
        >
          Random deal
        </button>
      </header>

      {phase.kind === "error" && (
        <div className="mb-3 p-3 rounded-lg bg-red-700/40 text-sm">
          <b>Error:</b> {phase.message}
        </div>
      )}

      <DealBuilder
        key={phase.kind === "setup" && phase.initial ? "initial" : "blank"}
        initial={phase.kind === "setup" ? phase.initial : undefined}
        onSubmit={handleSolve}
      />

      <div className="mt-4 flex items-center gap-3 text-sm text-white/70">
        <label>Time budget (s):</label>
        <input
          type="number"
          min={5}
          max={120}
          value={budgetSeconds}
          onChange={(e) => setBudgetSeconds(Number(e.target.value))}
          className="w-20 px-2 py-1 rounded bg-white/10"
        />
      </div>
    </div>
  );
}
