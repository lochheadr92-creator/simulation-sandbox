import * as React from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";
import { cn } from "../../lib/utils";

export const Slider = React.forwardRef(({ className, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn("relative flex w-full touch-none select-none items-center h-4", className)}
    {...props}
  >
    <SliderPrimitive.Track className="relative h-1 w-full grow overflow-hidden rounded-full bg-zinc-800">
      <SliderPrimitive.Range className="absolute h-full bg-sky-500" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb className="block h-3 w-3 rounded-full border border-sky-400 bg-zinc-100 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-500" />
  </SliderPrimitive.Root>
));
Slider.displayName = "Slider";
