import React from "react";
import { cn } from "../../lib/utils";

const VARIANTS = {
  default: "text-zinc-300 border-zinc-700",
  success: "text-emerald-400 border-emerald-900/50",
  danger: "text-red-400 border-red-900/50",
  warning: "text-yellow-400 border-yellow-900/50",
  info: "text-sky-400 border-sky-900/50",
};

export function Badge({ className, variant = "default", ...props }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border bg-transparent px-1.5 py-0.5 text-[10px] font-medium font-data uppercase tracking-wide",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}
