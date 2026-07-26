import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Play } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Demo | EcoLoop AI",
  description: "Preview the EcoLoop AI dashboard experience before entering the workspace."
};

export default function DemoRoute() {
  return (
    <div className="section-shell space-y-10 py-12 sm:py-16">
      <div className="space-y-4">
        <Badge>Product Demo</Badge>
        <div className="space-y-3">
          <h1 className="font-display text-4xl font-semibold tracking-tight sm:text-5xl">
            EcoLoop AI walkthrough
          </h1>
          <p className="max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">
            This placeholder page reserves the production demo surface while the final
            guided walkthrough is being prepared. It keeps the landing page CTA wired
            without introducing speculative video content.
          </p>
        </div>
      </div>

      <Card className="overflow-hidden">
        <CardContent className="grid gap-8 p-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-5">
            <div className="flex aspect-video items-center justify-center rounded-[2rem] border border-slate-200/70 bg-gradient-to-br from-blue-600 via-sky-500 to-teal-400 p-6 dark:border-slate-800">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-white/20 text-white backdrop-blur">
                <Play className="ml-1 h-8 w-8" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Planned walkthrough topics: marketing story, dashboard analytics, buildings,
              simulations, AI chat, and executive reports.
            </p>
          </div>

          <div className="space-y-4">
            <CardHeader className="p-0">
              <CardTitle>What the demo will cover</CardTitle>
              <CardDescription>
                A focused tour of the exact frontend flows now available on top of the
                frozen EcoLoop backend platform.
              </CardDescription>
            </CardHeader>
            <div className="grid gap-3">
              {[
                "Landing and product narrative",
                "Simulation analytics dashboard",
                "Building and simulation workflows",
                "AI assistant and executive reporting"
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-2xl border border-slate-200/70 bg-white/80 px-4 py-3 text-sm text-muted-foreground dark:border-slate-800 dark:bg-slate-950/60"
                >
                  {item}
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-3 pt-2">
              <Button asChild>
                <Link href="/dashboard">
                  Launch Dashboard
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href="/architecture">Explore Architecture</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
