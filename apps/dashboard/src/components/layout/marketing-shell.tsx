import Link from "next/link";

import { DeveloperLinks } from "@/components/marketing/developer-links";
import { EcoLoopLogo } from "@/components/ecoloop-logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { developerProfile, marketingNavigation } from "@/content/site";

export function MarketingShell({ children }: { children: React.ReactNode }) {
  const githubLink =
    developerProfile.links.find((link) => link.label === "GitHub" && link.href !== null) ?? null;

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[540px] bg-grid-pattern bg-[size:44px_44px] opacity-40" />
      <header className="sticky top-0 z-50 border-b border-white/40 bg-white/70 backdrop-blur-xl dark:border-slate-900/70 dark:bg-slate-950/75">
        <div className="section-shell flex h-20 items-center justify-between gap-6">
          <Link href="/" aria-label="EcoLoop AI home">
            <EcoLoopLogo />
          </Link>
          <nav className="hidden items-center gap-6 lg:flex">
            {marketingNavigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm font-medium text-slate-600 transition hover:text-slate-950 dark:text-slate-300 dark:hover:text-white"
              >
                {item.label}
              </Link>
            ))}
            {githubLink?.href ? (
              <a
                href={githubLink.href}
                target="_blank"
                rel="noreferrer"
                className="text-sm font-medium text-slate-600 transition hover:text-slate-950 dark:text-slate-300 dark:hover:text-white"
              >
                GitHub
              </a>
            ) : null}
          </nav>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Button asChild variant="secondary" className="hidden md:inline-flex">
              <Link href="/dashboard">Launch Dashboard</Link>
            </Button>
          </div>
        </div>
      </header>
      <main>{children}</main>
      <footer className="border-t border-slate-200/70 bg-white/70 py-10 dark:border-slate-900 dark:bg-slate-950/80">
        <div className="section-shell flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <p className="font-display text-lg font-semibold">EcoLoop AI</p>
            <p className="text-sm text-muted-foreground">{developerProfile.attribution}</p>
            <p className="text-sm text-muted-foreground">{developerProfile.copyright}</p>
          </div>
          <DeveloperLinks mode="icons" />
        </div>
      </footer>
    </div>
  );
}
