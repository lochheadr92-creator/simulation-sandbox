import React from "react";
import { cn } from "../../lib/utils";

const VARIANTS = {
  default: "bg-zinc-100 text-zinc-900 hover:bg-white border border-zinc-100",
  outline: "bg-transparent text-zinc-200 border border-zinc-700 hover:bg-zinc-900 hover:border-zinc-500",
  ghost: "bg-transparent text-zinc-400 border border-transparent hover:bg-zinc-900 hover:text-zinc-100",
  destructive: "bg-transparent text-red-400 border border-red-900/50 hover:bg-red-950/30",
  primary: "bg-sky-500 text-white border border-sky-500 hover:bg-sky-400",
};

const SIZES = {
  default: "h-8 px-3 text-sm",
  sm: "h-7 px-2 text-xs",
  icon: "h-8 w-8",
};

export const Button = React.forwardRef(
  ({ className, variant = "outline", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-sm font-medium transition-colors duration-75 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-500",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";
