"use client";

import { displayCode, isRed } from "@/lib/cards";
import type { CardCode } from "@/lib/types";

type Props = {
  code?: CardCode;
  facedown?: boolean;
  empty?: boolean;
  placeholder?: string; // shown when empty (e.g. suit glyph)
  selected?: boolean;
  highlight?: boolean;
  onClick?: () => void;
  size?: "sm" | "md";
  className?: string;
};

export function Card({
  code,
  facedown = false,
  empty = false,
  placeholder,
  selected = false,
  highlight = false,
  onClick,
  size = "md",
  className = "",
}: Props) {
  const dims =
    size === "sm"
      ? "w-9 h-[52px] text-[13px]"
      : "w-[46px] h-[64px] text-[15px] sm:w-[52px] sm:h-[72px] sm:text-[17px]";
  const ring = selected
    ? "ring-2 ring-yellow-300"
    : highlight
    ? "ring-2 ring-sky-400"
    : "ring-0";
  const base = `rounded-md border font-bold font-mono flex items-center justify-center select-none ${dims} ${ring}`;

  if (empty) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-label={placeholder ? `empty ${placeholder}` : "empty slot"}
        className={`${base} border-dashed border-white/30 bg-transparent text-white/40 ${
          onClick ? "active:scale-95 transition-transform" : ""
        } ${className}`}
      >
        {placeholder ?? ""}
      </button>
    );
  }
  if (facedown) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-label="face-down card"
        className={`${base} border-black/40 bg-card-back text-transparent
          bg-[repeating-linear-gradient(45deg,#1e3a5f,#1e3a5f_6px,#2c5282_6px,#2c5282_12px)]
          ${onClick ? "active:scale-95 transition-transform" : ""} ${className}`}
      />
    );
  }
  const red = code ? isRed(code) : false;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={code ?? ""}
      className={`${base} border-black/40 bg-white shadow ${
        red ? "text-card-red" : "text-black"
      } ${onClick ? "active:scale-95 transition-transform" : ""} ${className}`}
    >
      {code ? displayCode(code) : ""}
    </button>
  );
}
