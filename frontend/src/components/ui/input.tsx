import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-xl border border-[rgba(216,220,232,0.18)] bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm text-[#F6F1E8] ring-offset-background placeholder:text-[rgba(216,220,232,0.40)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5B3FD6] focus-visible:ring-offset-2 focus-visible:ring-offset-[#17142A] disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };
