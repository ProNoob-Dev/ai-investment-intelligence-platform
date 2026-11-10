import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils/cn";

type ButtonVariant = "primary" | "secondary" | "ghost" | "dark";

export function Button({
  variant = "primary",
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={cn(
        "btn-step inline-flex h-12 items-center justify-center gap-2 rounded-sm px-6 text-[15px] font-medium",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-accent text-white hover:bg-[#0a5e68]",
        variant === "secondary" && "border border-ink/20 bg-transparent text-ink hover:border-ink/40",
        variant === "ghost" && "bg-transparent text-accent hover:bg-accent/10",
        variant === "dark" && "bg-ink text-paper hover:bg-[#16242a]",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Card({
  className,
  children,
  dataUi,
}: {
  className?: string;
  children: ReactNode;
  dataUi?: boolean;
}) {
  return (
    <div className={cn("rounded-sm border border-ink/10 bg-white p-5", className)} data-ui={dataUi || undefined}>
      {children}
    </div>
  );
}

export function Chip({
  tone = "neutral",
  className,
  children,
}: {
  tone?: "buy" | "sell" | "hold" | "neutral" | "accent";
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-2.5 py-1 font-mono text-xs font-medium tracking-wide",
        tone === "buy" && "bg-accent/10 text-accent",
        tone === "sell" && "bg-[#c2402a]/10 text-[#c2402a]",
        tone === "hold" && "bg-[#8a6d00]/10 text-[#8a6d00]",
        tone === "neutral" && "bg-surface text-muted",
        tone === "accent" && "bg-accent text-white",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-sm bg-surface", className)} />;
}
