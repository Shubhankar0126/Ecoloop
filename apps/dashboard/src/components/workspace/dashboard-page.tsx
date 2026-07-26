"use client";

import type { Route } from "next";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  Bot,
  Building2,
  FileText,
  Leaf,
  Sparkles
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { useBuildingsQuery, useSimulationDetailsQuery, useSimulationListQuery } from "@/hooks/use-ecoloop-api";
import {
  buildDashboardSummary,
  createComfortChartData,
  createEnergyTrendData,
  createHvacUsageData
} from "@/lib/api/insights";
import { formatCompactNumber, formatPercent } from "@/lib/utils";

type QuickAction = {
  href: Route;
  title: string;
  description: string;
  icon: typeof Sparkles;
};

function MetricCard({
  title,
  value,
  helper,
  icon: Icon
}: {
  title: string;
  value: string;
  helper: string;
  icon: typeof Sparkles;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 p-6">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="font-display text-3xl font-semibold">{value}</p>
          <p className="text-xs text-muted-foreground">{helper}</p>
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-36 rounded-3xl" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-3">
        <Skeleton className="h-[360px] rounded-3xl xl:col-span-2" />
        <Skeleton className="h-[360px] rounded-3xl" />
      </div>
    </div>
  );
}

export function DashboardPage() {
  const buildingsQuery = useBuildingsQuery();
  const simulationsQuery = useSimulationListQuery();
  const simulationDetailsQuery = useSimulationDetailsQuery(simulationsQuery.data?.items);

  const isLoading =
    buildingsQuery.isLoading ||
    simulationsQuery.isLoading ||
    (((simulationsQuery.data?.count ?? 0) > 0) && simulationDetailsQuery.isLoading);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (buildingsQuery.isError || simulationsQuery.isError || simulationDetailsQuery.isError) {
    return (
      <StateCard
        icon={Activity}
        title="Unable to load dashboard analytics"
        description="The workspace could not read the existing EcoLoop REST APIs. Check the API base URL and backend availability."
        action={
          <Button asChild>
            <Link href="/">Return Home</Link>
          </Button>
        }
      />
    );
  }

  const buildings = buildingsQuery.data;
  const simulations = simulationDetailsQuery.data ?? [];

  if (!buildings || simulations.length === 0) {
    return (
      <div className="space-y-8">
        <header className="space-y-3">
          <Badge>Dashboard</Badge>
          <h1 className="font-display text-4xl font-semibold">Simulation workspace overview</h1>
          <p className="max-w-3xl text-muted-foreground">
            Once buildings and simulations are created through the existing backend APIs,
            the dashboard will turn them into charts, health signals, and executive views.
          </p>
        </header>
        <StateCard
          icon={Building2}
          title="No simulation history yet"
          description="Create a building, run a simulation, and return here to see live analytics powered only by the REST API."
          action={
            <div className="flex flex-wrap justify-center gap-3">
              <Button asChild>
                <Link href="/buildings">Create Building</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href="/simulations">Run Simulation</Link>
              </Button>
            </div>
          }
        />
      </div>
    );
  }

  const summary = buildDashboardSummary(buildings, simulations);
  const energyTrendData = createEnergyTrendData(simulations);
  const hvacData = createHvacUsageData(simulations);
  const comfortData = createComfortChartData(simulations);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Badge>Dashboard</Badge>
        <h1 className="font-display text-4xl font-semibold">Simulation workspace overview</h1>
        <p className="max-w-3xl text-muted-foreground">
          A top-level readout of buildings, simulations, comfort performance, and
          derived sustainability gains from the existing backend APIs.
        </p>
      </header>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid gap-4 md:grid-cols-2 xl:grid-cols-5"
      >
        <MetricCard
          title="Total Buildings"
          value={String(summary.totalBuildings)}
          helper="REST-backed building catalog"
          icon={Building2}
        />
        <MetricCard
          title="Total Simulations"
          value={String(summary.totalSimulations)}
          helper="Recorded execution history"
          icon={Sparkles}
        />
        <MetricCard
          title="Energy Saved"
          value={`${formatCompactNumber(summary.energySaved)} kWh`}
          helper="Best run versus least efficient run"
          icon={Activity}
        />
        <MetricCard
          title="Comfort Score"
          value={formatPercent(summary.comfortScore)}
          helper="Derived from average PPD"
          icon={Bot}
        />
        <MetricCard
          title="Carbon Reduction"
          value={`${formatCompactNumber(summary.carbonReduction)} kg`}
          helper="Estimated from energy reduction"
          icon={Leaf}
        />
      </motion.div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Energy Trend</CardTitle>
            <CardDescription>
              Total site energy and electricity consumption across recorded simulations.
            </CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={energyTrendData}>
                <defs>
                  <linearGradient id="energyGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.16} />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="energy"
                  stroke="#2563eb"
                  strokeWidth={2}
                  fill="url(#energyGradient)"
                />
                <Area
                  type="monotone"
                  dataKey="electricity"
                  stroke="#14b8a6"
                  strokeWidth={2}
                  fillOpacity={0}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Simulations</CardTitle>
            <CardDescription>Latest executions available in the workspace.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {simulations.slice(0, 5).map((simulation) => (
              <div
                key={simulation.simulation_id}
                className="rounded-2xl border border-slate-200/70 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-950/60"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium">{simulation.simulation_id.slice(0, 8)}</p>
                  <Badge variant={simulation.final_status === "succeeded" ? "success" : "warning"}>
                    {simulation.final_status}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {simulation.result.metrics.energy?.total_site_energy_kwh?.toFixed(1) ?? "0.0"} kWh
                  total site energy
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>HVAC Usage</CardTitle>
            <CardDescription>Heating, cooling, and equipment loads per run.</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hvacData}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.16} />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="heating" stackId="hvac" fill="#2563eb" radius={[8, 8, 0, 0]} />
                <Bar dataKey="cooling" stackId="hvac" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
                <Bar dataKey="equipment" stackId="hvac" fill="#14b8a6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card className="xl:col-span-2">
          <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle>Comfort Overview</CardTitle>
              <CardDescription>
                Temperature, humidity, and comfort score by recent simulation.
              </CardDescription>
            </div>
            <Button asChild variant="secondary">
              <Link href="/reports">
                Executive Reports
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            {comfortData.map((point) => (
              <div
                key={point.name}
                className="rounded-2xl border border-slate-200/70 bg-white/75 p-5 dark:border-slate-800 dark:bg-slate-950/60"
              >
                <p className="text-sm text-muted-foreground">{point.name}</p>
                <p className="mt-3 font-display text-3xl font-semibold">{point.score.toFixed(1)}</p>
                <p className="mt-1 text-sm text-muted-foreground">Comfort score</p>
                <div className="mt-4 space-y-1 text-sm text-muted-foreground">
                  <p>{point.temperature.toFixed(1)} deg C average temperature</p>
                  <p>{point.humidity.toFixed(1)}% average humidity</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Jump directly into the product workflows built on top of the existing backend.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          {([
            {
              href: "/buildings",
              title: "Manage Buildings",
              description: "Create buildings and review baselines.",
              icon: Building2
            },
            {
              href: "/simulations",
              title: "Run Simulation",
              description: "Launch an EnergyPlus run via the REST API.",
              icon: Sparkles
            },
            {
              href: "/ai",
              title: "AI Assistant",
              description: "Ask the agent for optimization guidance.",
              icon: Bot
            },
            {
              href: "/reports",
              title: "Generate Report",
              description: "Create an executive summary from a simulation.",
              icon: FileText
            }
          ] satisfies QuickAction[]).map((action) => (
            <Button
              key={action.title}
              asChild
              variant="secondary"
              className="h-auto justify-start rounded-3xl p-0"
            >
              <Link href={action.href} className="flex w-full flex-col items-start gap-3 p-5">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <action.icon className="h-5 w-5" />
                </div>
                <div className="space-y-1 text-left">
                  <p className="font-display text-lg font-semibold">{action.title}</p>
                  <p className="text-sm text-muted-foreground">{action.description}</p>
                </div>
              </Link>
            </Button>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
