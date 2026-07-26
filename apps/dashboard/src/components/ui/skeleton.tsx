import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-2xl bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 bg-[length:200%_100%] dark:from-slate-900 dark:via-slate-800 dark:to-slate-900",
        className
      )}
    />
  );
}
