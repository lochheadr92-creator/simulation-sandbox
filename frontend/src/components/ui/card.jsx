import React from "react";
import { cn } from "../../lib/utils";

export const Card = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("bg-panel border border-zinc-800 rounded-sm", className)} {...props} />
));
Card.displayName = "Card";

export const CardHeader = ({ className, ...props }) => (
  <div className={cn("px-3 py-2 border-b border-zinc-800", className)} {...props} />
);

export const CardTitle = ({ className, ...props }) => (
  <h3 className={cn("text-xs font-semibold uppercase tracking-[0.1em] text-zinc-400", className)} {...props} />
);

export const CardContent = ({ className, ...props }) => (
  <div className={cn("p-3", className)} {...props} />
);
