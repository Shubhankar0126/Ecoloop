"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BrainCircuit,
  Building2,
  ChevronRight,
  Cpu,
  Leaf,
  PanelsTopLeft,
  Play,
  Radar,
  Sparkles,
  Wind
} from "lucide-react";

import { ArchitectureDiagram } from "@/components/marketing/architecture-diagram";
import { DeveloperLinks } from "@/components/marketing/developer-links";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  demoRoute,
  developerProfile,
  featureGroups,
  technologies,
  valuePillars
} from "@/content/site";

const reveal = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 }
};

function SectionHeading({
  eyebrow,
  title,
  description
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-4">
      <span className="eyebrow">{eyebrow}</span>
      <div className="space-y-3">
        <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
          {title}
        </h2>
        <p className="max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">
          {description}
        </p>
      </div>
    </div>
  );
}

function SmartBuildingIllustration() {
  return (
    <motion.div
      animate={{ y: [0, -10, 0] }}
      transition={{ duration: 6, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
      className="relative mx-auto w-full max-w-xl"
    >
      <div className="absolute -left-8 top-14 h-32 w-32 rounded-full bg-blue-500/20 blur-3xl" />
      <div className="absolute -right-10 bottom-10 h-36 w-36 rounded-full bg-teal-500/20 blur-3xl" />
      <div className="glass-panel grid-surface relative overflow-hidden rounded-[2rem] p-8">
        <div className="absolute inset-x-10 top-10 h-px bg-gradient-to-r from-transparent via-teal-400/70 to-transparent animate-pulseLine" />
        <div className="grid grid-cols-[1fr_auto] gap-8">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Badge>Smart Building</Badge>
              <Badge variant="neutral">Live Energy Loop</Badge>
            </div>
            <div className="space-y-3">
              <div className="h-4 w-28 rounded-full bg-blue-500/20" />
              <div className="h-4 w-16 rounded-full bg-teal-500/20" />
            </div>
          </div>
          <div className="flex gap-4">
            {[0, 1, 2].map((column) => (
              <div key={column} className="flex items-end gap-3">
                {[0, 1, 2, 3].map((row) => (
                  <div
                    key={`${column}-${row}`}
                    className="w-14 rounded-t-2xl border border-white/30 bg-gradient-to-b from-slate-100/80 to-slate-200/80 shadow-sm dark:from-slate-800/70 dark:to-slate-950/70"
                    style={{ height: `${150 - row * 18 - column * 8}px` }}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            { label: "Comfort", value: "92/100", icon: Wind },
            { label: "HVAC Load", value: "-12%", icon: Radar },
            { label: "Carbon", value: "-8.4%", icon: Leaf }
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-white/40 bg-white/70 p-4 backdrop-blur dark:border-white/10 dark:bg-slate-950/60"
            >
              <div className="mb-3 flex items-center gap-2 text-muted-foreground">
                <item.icon className="h-4 w-4" />
                <span className="text-xs uppercase tracking-[0.2em]">{item.label}</span>
              </div>
              <p className="font-display text-2xl font-semibold">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function DashboardPreviewCard() {
  return (
    <Card className="overflow-hidden">
      <CardContent className="grid gap-6 p-0 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="border-b border-slate-200/70 p-6 dark:border-slate-800 lg:border-b-0 lg:border-r">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="font-display text-xl font-semibold">Dashboard Snapshot</p>
              <p className="text-sm text-muted-foreground">
                Analytics, AI chat, reports, buildings, and simulations.
              </p>
            </div>
            <Badge variant="neutral">Launch Ready</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {[
              { label: "Energy Saved", value: "1.2 MWh" },
              { label: "Comfort Score", value: "92.4" },
              { label: "Buildings", value: "18" },
              { label: "Simulations", value: "146" }
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 dark:border-slate-800 dark:bg-slate-950/60"
              >
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <p className="mt-2 font-display text-3xl font-semibold">{stat.value}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 grid grid-cols-6 gap-3">
            {[44, 68, 55, 80, 64, 92].map((height, index) => (
              <div
                key={height}
                className="rounded-t-2xl bg-gradient-to-t from-blue-600 via-sky-500 to-teal-400"
                style={{ height: `${height}px`, animationDelay: `${index * 150}ms` }}
              />
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-4 p-6">
          {[
            "AI chat recommendations with executive summaries",
            "Recent simulation history with comparison actions",
            "Report viewer with recommendations and diagnostics"
          ].map((item) => (
            <div
              key={item}
              className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 text-sm text-muted-foreground dark:border-slate-800 dark:bg-slate-950/60"
            >
              {item}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function PipelineSection() {
  const steps = [
    { label: "Building", icon: Building2 },
    { label: "AI Brain", icon: BrainCircuit },
    { label: "Simulation", icon: Cpu },
    { label: "Optimization", icon: Sparkles },
    { label: "Executive Report", icon: PanelsTopLeft }
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-5">
      {steps.map((step, index) => (
        <div key={step.label} className="relative">
          <Card className="h-full">
            <CardContent className="flex min-h-44 flex-col gap-5 p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/10 text-accent">
                <step.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="font-display text-xl font-semibold">{step.label}</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  {index === 0
                    ? "Building context and operational intent."
                    : index === steps.length - 1
                      ? "Leadership-ready output and recommendations."
                      : "Structured decision step in the optimization loop."}
                </p>
              </div>
            </CardContent>
          </Card>
          {index < steps.length - 1 ? (
            <ChevronRight className="absolute right-[-12px] top-1/2 hidden h-5 w-5 -translate-y-1/2 text-teal-400 lg:block" />
          ) : null}
        </div>
      ))}
    </div>
  );
}

export function LandingPage() {
  return (
    <div className="space-y-24 py-12 sm:py-16">
      <section className="section-shell">
        <div className="grid items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={reveal}
            transition={{ duration: 0.6 }}
            className="space-y-8"
          >
            <Badge>AI-Powered Building Energy Optimization Platform</Badge>
            <div className="space-y-6">
              <h1 className="font-display text-5xl font-semibold tracking-tight sm:text-6xl lg:text-7xl">
                EcoLoop AI
                <span className="mt-3 block text-slate-500 dark:text-slate-300">
                  Optimize commercial buildings with simulation-backed intelligence.
                </span>
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl">
                Optimize commercial buildings using Artificial Intelligence, EnergyPlus,
                LangGraph, MCP, and Qwen3 in a single enterprise-grade platform.
              </p>
            </div>
            <div className="flex flex-wrap gap-4">
              <Button asChild size="lg">
                <Link href="/dashboard">
                  Launch Dashboard
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="secondary" size="lg">
                <Link href={demoRoute}>
                  <Play className="h-4 w-4" />
                  Watch Demo
                </Link>
              </Button>
              <Button asChild variant="secondary" size="lg">
                <Link href="/features">Explore Features</Link>
              </Button>
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.15 }}
          >
            <SmartBuildingIllustration />
          </motion.div>
        </div>
      </section>

      <section className="section-shell space-y-8">
        <SectionHeading
          eyebrow="Trusted Technologies"
          title="A product layer built on serious engineering foundations."
          description="EcoLoop AI brings together simulation, orchestration, and interface layers in one consistent experience."
        />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {technologies.map((technology, index) => (
            <motion.div
              key={technology.name}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.3 }}
              variants={reveal}
              transition={{ duration: 0.45, delay: index * 0.05 }}
            >
              <Card className="h-full">
                <CardContent className="flex h-full flex-col gap-5 p-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <technology.icon className="h-5 w-5" />
                  </div>
                  <div className="space-y-2">
                    <p className="font-display text-xl font-semibold">{technology.name}</p>
                    <p className="text-sm text-muted-foreground">{technology.description}</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="section-shell space-y-8">
        <SectionHeading
          eyebrow="Why EcoLoop AI"
          title="Designed for operators who need sustainability without guesswork."
          description="The product experience focuses on measurable outcomes, readable analytics, and AI workflows grounded in simulation reality."
        />
        <div className="grid gap-4 lg:grid-cols-5">
          {valuePillars.map((pillar, index) => (
            <motion.div
              key={pillar.title}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.3 }}
              variants={reveal}
              transition={{ duration: 0.45, delay: index * 0.06 }}
            >
              <Card className="h-full">
                <CardContent className="flex h-full flex-col gap-5 p-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/10 text-accent">
                    <pillar.icon className="h-5 w-5" />
                  </div>
                  <div className="space-y-2">
                    <p className="font-display text-xl font-semibold">{pillar.title}</p>
                    <p className="text-sm text-muted-foreground">{pillar.description}</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="section-shell space-y-8">
        <SectionHeading
          eyebrow="How It Works"
          title="A clear product pipeline from building context to leadership-ready reporting."
          description="Every stage is visible, structured, and intentionally designed to support optimization decisions."
        />
        <PipelineSection />
      </section>

      <section className="section-shell space-y-8">
        <SectionHeading
          eyebrow="Architecture Preview"
          title="A professional stack that stays readable from UI to execution engine."
          description="The frontend speaks only to the REST layer, which preserves the clean boundaries of the backend platform."
        />
        <ArchitectureDiagram />
      </section>

      <section className="section-shell space-y-8">
        <SectionHeading
          eyebrow="Dashboard Preview"
          title="The workspace feels like a modern AI product, not an admin console."
          description="Top navigation, rich cards, simulation history, AI recommendations, and executive reporting live in one cohesive shell."
        />
        <DashboardPreviewCard />
      </section>

      <section className="section-shell">
        <Card className="overflow-hidden">
          <CardContent className="grid gap-10 p-8 lg:grid-cols-[1.1fr_0.9fr] lg:p-10">
            <div className="space-y-6">
              <SectionHeading
                eyebrow="Developer"
                title={developerProfile.name}
                description="Creator of EcoLoop AI. Building intelligent software systems that combine Artificial Intelligence, Simulation, and Enterprise Software Engineering to improve building sustainability."
              />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                {developerProfile.attribution}
              </p>
              <DeveloperLinks />
            </div>
            <div className="rounded-[2rem] border border-slate-200/70 bg-gradient-to-br from-blue-600 to-teal-400 p-[1px] dark:border-slate-800">
              <div className="flex h-full flex-col justify-between rounded-[calc(2rem-1px)] bg-slate-950 p-8 text-white">
                <div className="space-y-4">
                  <Badge variant="default">{developerProfile.title}</Badge>
                  <h3 className="font-display text-3xl font-semibold">
                    Product design grounded in systems engineering.
                  </h3>
                  <p className="text-sm leading-7 text-slate-300">
                    EcoLoop AI brings simulation rigor, agent orchestration, and
                    executive storytelling into a product surface meant to feel fast,
                    deliberate, and trustworthy.
                  </p>
                </div>
                <div className="grid gap-3">
                  {[
                    "EnergyPlus simulation backbone",
                    "LangGraph planning and reasoning loop",
                    "REST-first dashboard integration"
                  ].map((item) => (
                    <div
                      key={item}
                      className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200"
                    >
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

export function FeatureHighlightsPage() {
  return (
    <div className="section-shell space-y-14 py-12">
      <SectionHeading
        eyebrow="Features"
        title="A premium product surface for EcoLoop AI's completed platform."
        description="This sprint focuses on how people experience the system: polished storytelling, dashboard clarity, and AI-first workflows on top of the frozen backend."
      />
      <div className="grid gap-6 lg:grid-cols-3">
        {featureGroups.map((group) => (
          <Card key={group.title} className="h-full">
            <CardHeader>
              <Badge>{group.eyebrow}</Badge>
              <CardTitle>{group.title}</CardTitle>
              <CardDescription>{group.description}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
      <Card>
        <CardContent className="grid gap-5 p-8 md:grid-cols-2 xl:grid-cols-4">
          {[
            {
              title: "Landing Narrative",
              description: "Modern startup framing with clear architecture and value communication."
            },
            {
              title: "Workspace Analytics",
              description: "REST-backed building, simulation, AI, and reporting experiences."
            },
            {
              title: "Dark Mode",
              description: "A polished dual-theme system with readable contrast and soft glass surfaces."
            },
            {
              title: "Design Language",
              description: "Blue, white, teal, and gray tokens with large whitespace and rounded cards."
            }
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-3xl border border-slate-200/70 bg-white/80 p-5 dark:border-slate-800 dark:bg-slate-950/60"
            >
              <p className="font-display text-xl font-semibold">{item.title}</p>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export function ArchitectureStoryPage() {
  return (
    <div className="section-shell space-y-14 py-12">
      <SectionHeading
        eyebrow="Architecture"
        title="The product layer respects every backend boundary that was already frozen."
        description="Frontend pages consume only the existing REST APIs. They never speak directly to MCP, SimulationService, or EnergyPlus."
      />
      <ArchitectureDiagram />
      <div className="grid gap-6 lg:grid-cols-3">
        {[
          {
            title: "Presentation Layer",
            description:
              "Next.js routes, client components, charts, forms, and motion-based storytelling."
          },
          {
            title: "REST Contract",
            description:
              "All workspace data flows through the existing versioned FastAPI endpoints."
          },
          {
            title: "Execution Stack",
            description:
              "The backend continues to own AI execution, simulation orchestration, and report generation."
          }
        ].map((item) => (
          <Card key={item.title}>
            <CardHeader>
              <CardTitle>{item.title}</CardTitle>
              <CardDescription>{item.description}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function AboutStoryPage() {
  return (
    <div className="section-shell space-y-14 py-12">
      <SectionHeading
        eyebrow="About"
        title="EcoLoop AI is a product vision for sustainable building operations."
        description="The project blends AI reasoning, simulation rigor, and enterprise-grade software engineering to improve how buildings consume energy."
      />
      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader>
            <Badge>Mission</Badge>
            <CardTitle>Make energy optimization readable, explainable, and actionable.</CardTitle>
            <CardDescription>
              EcoLoop AI turns complex simulation and orchestration systems into a
              product experience that building operators, sustainability leaders, and
              technical stakeholders can all understand.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            {[
              "Simulation-backed evidence",
              "AI-assisted planning loops",
              "Executive-ready reporting"
            ].map((item) => (
              <div
                key={item}
                className="rounded-3xl border border-slate-200/70 bg-white/75 p-5 text-sm dark:border-slate-800 dark:bg-slate-950/60"
              >
                {item}
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Badge variant="neutral">Creator</Badge>
            <CardTitle>{developerProfile.name}</CardTitle>
            <CardDescription>
              {developerProfile.title} focused on intelligent systems that combine
              enterprise software, simulation, and sustainability outcomes.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
              {developerProfile.attribution}
            </p>
            <DeveloperLinks />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
