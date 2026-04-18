"use client";

import { useEffect, useRef, useState } from "react";
import { Board } from "./Board";
import type { SolveResponse } from "@/lib/types";

type Props = {
  solution: SolveResponse;
  onBack: () => void;
};

export function Playback({ solution, onBack }: Props) {
  const n = solution.snapshots.length - 1; // number of moves
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(700); // ms per move
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) return;
    if (step >= n) {
      setPlaying(false);
      return;
    }
    timer.current = window.setTimeout(() => setStep((s) => s + 1), speed);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [playing, step, n, speed]);

  const snap = solution.snapshots[step];
  const desc =
    step === 0
      ? `Initial deal (0 / ${n})`
      : `${step} / ${n} — ${solution.move_descriptions[step - 1]}`;

  return (
    <div className="flex flex-col gap-3 p-3 safe-top safe-bottom">
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="px-3 py-2 rounded-lg bg-white/10 active:bg-white/20 text-sm"
        >
          ← Back
        </button>
        <div className="text-xs text-white/60">
          {solution.solved ? (
            <>
              Solved in {solution.elapsed_seconds.toFixed(2)}s ·{" "}
              {solution.node_count.toLocaleString()} nodes
            </>
          ) : (
            <>Not solved</>
          )}
        </div>
      </div>

      {snap && <Board snapshot={snap} />}

      <div className="text-sm text-white/90 px-1">{desc}</div>

      <div className="grid grid-cols-4 gap-2">
        <button
          className="py-3 rounded-lg bg-white/10 active:bg-white/20"
          onClick={() => {
            setPlaying(false);
            setStep(0);
          }}
          aria-label="Reset"
        >
          ⏮
        </button>
        <button
          className="py-3 rounded-lg bg-white/10 active:bg-white/20 disabled:opacity-40"
          disabled={step === 0}
          onClick={() => {
            setPlaying(false);
            setStep((s) => Math.max(0, s - 1));
          }}
        >
          ◀ Prev
        </button>
        <button
          className="py-3 rounded-lg bg-white/10 active:bg-white/20 disabled:opacity-40"
          disabled={step >= n}
          onClick={() => {
            setPlaying(false);
            setStep((s) => Math.min(n, s + 1));
          }}
        >
          Next ▶
        </button>
        <button
          className={`py-3 rounded-lg ${
            playing ? "bg-amber-400 text-black" : "bg-emerald-500 text-black"
          } active:opacity-80 font-semibold`}
          disabled={n === 0}
          onClick={() => setPlaying((p) => !p)}
        >
          {playing ? "Pause" : "Play"}
        </button>
      </div>

      <input
        type="range"
        min={0}
        max={Math.max(n, 0)}
        value={step}
        onChange={(e) => {
          setPlaying(false);
          setStep(Number(e.target.value));
        }}
        className="w-full accent-emerald-400"
      />

      <details className="text-sm bg-white/5 rounded-lg p-2">
        <summary className="cursor-pointer">Full move list</summary>
        <ol className="mt-2 pl-4 list-decimal space-y-0.5 max-h-64 overflow-y-auto">
          {solution.move_descriptions.map((d, i) => (
            <li key={i} className={i + 1 === step ? "text-amber-300 font-bold" : ""}>
              {d}
            </li>
          ))}
        </ol>
      </details>
    </div>
  );
}
