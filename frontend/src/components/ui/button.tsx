import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "rounded-full bg-control text-text-inverse shadow-soft hover:bg-control-hover active:bg-control-active",
        destructive:
          "rounded-full bg-destructive text-destructive-foreground hover:opacity-90",
        outline:
          "rounded-full border border-border-strong bg-transparent text-text-secondary hover:border-control hover:text-link",
        secondary:
          "bg-secondary text-secondary-foreground rounded-full hover:bg-secondary/80",
        ghost:
          "rounded-full text-text-secondary hover:bg-surface-subtle hover:text-text-primary",
        link: "text-link underline-offset-4 hover:text-link-hover hover:underline",
      },
      size: {
        default: "h-10 px-6 py-2",
        sm: "h-9 rounded-full px-4",
        lg: "h-12 rounded-full px-8 text-base",
        icon: "h-10 w-10 rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild, children, ...props }, ref) => {
    const buttonClassName = cn(buttonVariants({ variant, size, className }));

    if (asChild && React.isValidElement(children)) {
      const child = children as React.ReactElement<{ className?: string }>;
      return React.cloneElement(child, {
        ...props,
        className: cn(buttonClassName, child.props.className),
      });
    }

    return (
      <button className={buttonClassName} ref={ref} {...props}>
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
