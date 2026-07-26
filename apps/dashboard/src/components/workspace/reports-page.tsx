"use client";

import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Download, FileBarChart2, LoaderCircle } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { useGenerateReportMutation, useSimulationDetailsQuery, useSimulationListQuery } from "@/hooks/use-ecoloop-api";

const reportSchema = z.object({
  simulation_id: z.string().min(1, "Select a simulation."),
  title: z.string().optional(),
  include_diagnostics: z.boolean().default(true)
});

type ReportFormValues = z.infer<typeof reportSchema>;

export function ReportsPage() {
  const searchParams = useSearchParams();
  const simulationsQuery = useSimulationListQuery();
  const detailsQuery = useSimulationDetailsQuery(simulationsQuery.data?.items);
  const reportMutation = useGenerateReportMutation();
  const [selectedSimulationId, setSelectedSimulationId] = useState<string>("");

  const form = useForm<ReportFormValues>({
    resolver: zodResolver(reportSchema),
    defaultValues: {
      simulation_id: "",
      title: "",
      include_diagnostics: true
    }
  });

  useEffect(() => {
    const simulationId = searchParams.get("simulationId");
    if (simulationId) {
      setSelectedSimulationId(simulationId);
      form.setValue("simulation_id", simulationId);
    }
  }, [form, searchParams]);

  const simulations = useMemo(() => detailsQuery.data ?? [], [detailsQuery.data]);
  const selectedSimulation = useMemo(
    () =>
      simulations.find((simulation) => simulation.simulation_id === selectedSimulationId) ?? null,
    [selectedSimulationId, simulations]
  );

  async function onSubmit(values: ReportFormValues) {
    setSelectedSimulationId(values.simulation_id);
    await reportMutation.mutateAsync(values);
  }

  const chartData = selectedSimulation
    ? [
        {
          label: "Site",
          value: selectedSimulation.result.metrics.energy?.total_site_energy_kwh ?? 0
        },
        {
          label: "Electric",
          value: selectedSimulation.result.metrics.energy?.electricity_consumption_kwh ?? 0
        },
        {
          label: "HVAC",
          value: selectedSimulation.result.metrics.hvac?.hvac_energy_kwh ?? 0
        }
      ]
    : [];

  const isLoading =
    simulationsQuery.isLoading || ((simulationsQuery.data?.count ?? 0) > 0 && detailsQuery.isLoading);

  if (isLoading) {
    return <Skeleton className="h-[720px] rounded-3xl" />;
  }

  if (simulationsQuery.isError || detailsQuery.isError) {
    return (
      <StateCard
        icon={FileBarChart2}
        title="Unable to load report data"
        description="The report workspace could not read recorded simulations from the existing REST API."
      />
    );
  }

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Badge>Reports</Badge>
        <h1 className="font-display text-4xl font-semibold">Executive reports</h1>
        <p className="max-w-3xl text-muted-foreground">
          Generate board-ready summaries from recorded simulations using the existing
          report endpoint, then review highlights, diagnostics, and performance charts.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[0.84fr_1.16fr]">
        <Card>
          <CardHeader>
            <CardTitle>Generate Report</CardTitle>
            <CardDescription>
              Choose a simulation, set an optional title, and request an executive summary.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="simulation_id">
                  Simulation
                </label>
                <select
                  className="flex h-11 w-full rounded-2xl border border-slate-200 bg-white/80 px-4 text-sm text-slate-900 shadow-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 dark:border-slate-800 dark:bg-slate-950/70 dark:text-white"
                  id="simulation_id"
                  {...form.register("simulation_id")}
                >
                  <option value="">Select a simulation</option>
                  {simulations.map((simulation) => (
                    <option key={simulation.simulation_id} value={simulation.simulation_id}>
                      {simulation.simulation_id.slice(0, 8)} - {simulation.final_status}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="title">
                  Report Title
                </label>
                <Input
                  id="title"
                  placeholder="Executive summary for the latest candidate run"
                  {...form.register("title")}
                />
              </div>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200/70 bg-white/70 px-4 py-3 text-sm dark:border-slate-800 dark:bg-slate-950/60">
                <input type="checkbox" {...form.register("include_diagnostics")} />
                Include diagnostics in the final report payload.
              </label>
              <Button disabled={reportMutation.isPending} type="submit">
                {reportMutation.isPending ? (
                  <>
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <FileBarChart2 className="h-4 w-4" />
                    Generate Executive Report
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          {reportMutation.data ? (
            <>
              <Card>
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <CardTitle>{reportMutation.data.title}</CardTitle>
                    <CardDescription>{reportMutation.data.executive_summary}</CardDescription>
                  </div>
                  <Button disabled type="button" variant="secondary">
                    <Download className="h-4 w-4" />
                    Download (Soon)
                  </Button>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-3">
                  {(reportMutation.data.highlights ?? []).map((highlight) => (
                    <div
                      key={highlight}
                      className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 text-sm dark:border-slate-800 dark:bg-slate-950/60"
                    >
                      {highlight}
                    </div>
                  ))}
                </CardContent>
              </Card>

              <div className="grid gap-6 xl:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Energy Snapshot</CardTitle>
                    <CardDescription>
                      Chart derived from the selected simulation detail.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.16} />
                        <XAxis dataKey="label" tickLine={false} axisLine={false} />
                        <YAxis tickLine={false} axisLine={false} />
                        <Tooltip />
                        <Bar dataKey="value" fill="#2563eb" radius={[10, 10, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Recommendations</CardTitle>
                    <CardDescription>Operational guidance for the selected simulation.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {(reportMutation.data.recommendations ?? []).map((recommendation) => (
                      <div
                        key={recommendation}
                        className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 text-sm dark:border-slate-800 dark:bg-slate-950/60"
                      >
                        {recommendation}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>

              {(reportMutation.data.diagnostics ?? []).length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Diagnostics</CardTitle>
                    <CardDescription>
                      Raw diagnostic notes included by the backend report endpoint.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {(reportMutation.data.diagnostics ?? []).map((diagnostic) => (
                      <div
                        key={diagnostic}
                        className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300"
                      >
                        {diagnostic}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ) : null}
            </>
          ) : (
            <StateCard
              icon={FileBarChart2}
              title="No report generated yet"
              description="Choose a simulation and request an executive report to populate the viewer."
            />
          )}
        </div>
      </div>
    </div>
  );
}
