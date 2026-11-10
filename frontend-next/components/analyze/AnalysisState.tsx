"use client";

import { Skeleton } from "@/components/ui/ui";

export function AnalysisSkeleton() {
  return (
    <div className="mt-8 grid gap-4 lg:grid-cols-2" aria-label="Loading analysis">
      <Skeleton className="h-44" />
      <Skeleton className="h-44" />
      <Skeleton className="h-56 lg:col-span-2" />
      <Skeleton className="h-40" />
      <Skeleton className="h-40" />
    </div>
  );
}

export function ErrorDisplay({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="mt-8 rounded-sm border border-[#c2402a]/30 bg-[#c2402a]/[0.05] p-5" role="alert">
      <p className="font-medium text-[#c2402a]">Couldn’t run that analysis</p>
      <p className="mt-1 text-sm leading-relaxed text-muted">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="link-underline mt-3 font-medium text-accent"
        >
          Try again
        </button>
      )}
    </div>
  );
}
