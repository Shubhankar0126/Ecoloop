export function EcoLoopLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 via-sky-500 to-teal-400 text-white shadow-lg shadow-blue-500/20">
        <div className="absolute inset-[7px] rounded-xl border border-white/25" />
        <span className="font-display text-lg font-bold">E</span>
      </div>
      {!compact ? (
        <div className="flex flex-col">
          <span className="font-display text-sm font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
            EcoLoop AI
          </span>
          <span className="text-sm text-muted-foreground">
            Building Intelligence Platform
          </span>
        </div>
      ) : null}
    </div>
  );
}
