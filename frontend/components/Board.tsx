"use client";

import { Card } from "./Card";
import { SUIT_GLYPH, makeCode } from "@/lib/cards";
import type { Snapshot, SuitKey } from "@/lib/types";

const SUITS: SuitKey[] = ["S", "H", "D", "C"];

export function Board({ snapshot }: { snapshot: Snapshot }) {
  return (
    <div className="flex flex-col gap-3">
      {/* Top row: foundations + stock + waste */}
      <div className="flex flex-wrap gap-3 items-start">
        <div className="flex gap-1">
          {SUITS.map((s) => {
            const rank = snapshot.foundations[s];
            return rank === 0 ? (
              <Card
                key={s}
                empty
                placeholder={SUIT_GLYPH[s]}
                size="md"
                className={
                  s === "H" || s === "D" ? "text-card-red/60" : "text-white/40"
                }
              />
            ) : (
              <Card key={s} code={makeCode(rank, s)} size="md" />
            );
          })}
        </div>

        <div className="flex gap-1 ml-auto">
          <div className="flex flex-col items-center">
            <div className="text-[10px] text-white/60 mb-1">
              Stock ({snapshot.stock_count})
            </div>
            {snapshot.stock_count > 0 ? (
              <Card facedown size="md" />
            ) : (
              <Card empty placeholder="\u2205" size="md" />
            )}
          </div>
          <div className="flex flex-col items-center">
            <div className="text-[10px] text-white/60 mb-1">
              Waste ({snapshot.waste_visible.length})
            </div>
            {snapshot.waste_visible.length === 0 ? (
              <Card empty placeholder="\u2205" size="md" />
            ) : (
              <div className="relative">
                {snapshot.waste_visible.slice(-3).map((code, i, arr) => (
                  <div
                    key={i}
                    style={{
                      position: i === 0 ? "static" : "absolute",
                      left: i === 0 ? 0 : `${i * 10}px`,
                      top: 0,
                      opacity: i === arr.length - 1 ? 1 : 0.55,
                    }}
                  >
                    <Card code={code} size="md" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tableau */}
      <div className="overflow-x-auto -mx-2 px-2">
        <div className="flex gap-2 min-w-max">
          {snapshot.tableau.map((pile, i) => (
            <div key={i} className="flex flex-col items-center min-w-[46px] sm:min-w-[52px]">
              <div className="text-[10px] text-white/60 mb-1">T{i}</div>
              <div className="relative">
                {/* Face-downs stacked with overlap. */}
                {Array.from({ length: pile.face_down }).map((_, j) => (
                  <div
                    key={`fd-${j}`}
                    style={{ position: "absolute", top: `${j * 18}px` }}
                  >
                    <Card facedown size="md" />
                  </div>
                ))}
                {/* Face-ups continue the stack below the face-downs. */}
                {pile.face_up.map((code, j) => (
                  <div
                    key={`fu-${j}`}
                    style={{
                      position: "absolute",
                      top: `${(pile.face_down + j) * 18}px`,
                    }}
                  >
                    <Card code={code} size="md" />
                  </div>
                ))}
                {/* Empty placeholder if no cards. */}
                {pile.face_down === 0 && pile.face_up.length === 0 && (
                  <Card empty placeholder="" size="md" />
                )}
                {/* Spacer to make the container tall enough. */}
                <div
                  style={{
                    height: `${
                      Math.max(pile.face_down + pile.face_up.length, 1) *
                        18 +
                      54
                    }px`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
