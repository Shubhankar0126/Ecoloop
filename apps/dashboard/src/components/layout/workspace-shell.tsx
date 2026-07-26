"use client";

import Link from "next/link";
import { Settings, UserCircle2 } from "lucide-react";
import { usePathname } from "next/navigation";

import { EcoLoopLogo } from "@/components/ecoloop-logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { workspaceNavigation } from "@/content/site";
import { cn } from "@/lib/utils";

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-50 border-b border-white/40 bg-white/75 backdrop-blur-xl dark:border-slate-900/70 dark:bg-slate-950/80">
        <div className="section-shell flex h-20 flex-wrap items-center justify-between gap-4">
          <Link href="/dashboard" aria-label="EcoLoop dashboard">
            <EcoLoopLogo compact />
          </Link>
          <nav className="flex flex-wrap items-center gap-2">
            {workspaceNavigation.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-full px-4 py-2 text-sm font-semibold transition",
                    active
                      ? "bg-primary text-primary-foreground shadow-lg shadow-blue-500/20"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-white"
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-3">
            <Badge variant="neutral" className="hidden lg:inline-flex">
              REST API Surface
            </Badge>
            <Button size="icon" variant="secondary" type="button" aria-label="Settings">
              <Settings className="h-4 w-4" />
            </Button>
            <Button size="icon" variant="secondary" type="button" aria-label="User">
              <UserCircle2 className="h-5 w-5" />
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="section-shell py-10">{children}</main>
    </div>
  );
}
