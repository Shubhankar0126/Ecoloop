"use client";

import Link from "next/link";
import { startTransition, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { FileText, PlayCircle, Scale, Search } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { useBuildingsQuery, useRunSimulationMutation, useSimulationDetailsQuery, useSimulationListQuery } from "@/hooks/use-ecoloop-api";
import { compareSimulations } from "@/lib/api/insights";
import { formatCompactNumber } from "@/lib/utils";

const simulationSchema = z.object({
  building_id: z.string().optional(),
  idf_path: z.string().min(1, "IDF path is required."),
  epw_path: z.string().min(1, "EPW path is required."),
  timeout_seconds: z.coerce.number().int().positive().optional(),
  parallel_jobs: z.coerce.number().int().positive().optional()
});

type SimulationFormValues = z.infer<typeof simulationSchema>;

function statusVariant(status: string) {
  if (status === "succeeded") {
    return "success";
  }

  if (status === "failed" || status === "parse_failed" || status === "timed_out") {
    return "destructive";
  }

  return "warning";
}

export function SimulationsPage() {
  const buildingsQuery = useBuildingsQuery();
  const simulationsQuery = useSimulationListQuery();
  const detailsQuery = useSimulationDetailsQuery(simulationsQuery.data?.items);
  const runSimulationMutation = useRunSimulationMutation();
  const [selectedSimulationId, setSelectedSimulationId] = useState<string | null>(null);
  const [comparisonIds, setComparisonIds] = useState<string[]>([]);
  const [search, setSearch] = useState("");

  const form = useForm<SimulationFormValues>({
    resolver: zodResolver(simulationSchema),
    defaultValues: {
      building_id: "",
      idf_path: "",
      epw_path: "",
      timeout_seconds: 1800,
      parallel_jobs: 1
    }
  });

  const buildings = useMemo(() => buildingsQuery.data?.items ?? [], [buildingsQuery.data?.items]);
  const simulations = useMemo(() => detailsQuery.data ?? [], [detailsQuery.data]);
  const selectedSimulation =
    simulations.find((simulation) => simulation.simulation_id === selectedSimulationId) ?? null;
  const comparisonSimulations = comparisonIds
    .map((id) => simulations.find((simulation) => simulation.simulation_id === id) ?? null)
    .filter((simulation): simulation is NonNullable<typeof simulation> => simulation !== null);

  const filteredSimulations = useMemo(() => {
    return simulations.filter((simulation) => {
      const building = buildings.find((item) => item.building_id === simulation.building_id);
      const haystack = [
        simulation.simulation_id,
        simulation.final_status,
        building?.name ?? "",
        simulation.idf_path,
        simulation.epw_path
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(search.toLowerCase());
    });
  }, [buildings, search, simulations]);

  async function onSubmit(values: SimulationFormValues) {
    const response = await runSimulationMutation.mutateAsync({
      ...values,
      building_id: values.building_id || undefined
    });
    form.reset({
      building_id: values.building_id,
      idf_path: "",
      epw_path: "",
      timeout_seconds: values.timeout_seconds,
      parallel_jobs: values.parallel_jobs
    });
    startTransition(() => {
      setSelectedSimulationId(response.simulation_id);
    });
  }

  function toggleComparison(simulationId: string) {
    setComparisonIds((current) => {
      if (current.includes(simulationId)) {
        return current.filter((id) => id !== simulationId);
      }

      if (current.length === 2) {
        return [current[1], simulationId];
      }

      return [...current, simulationId];
    });
  }

  const comparison =
    comparisonSimulations.length === 2
      ? compareSimulations(comparisonSimulations[0], comparisonSimulations[1])
      : null;

  const isLoading =
    simulationsQuery.isLoading || ((simulationsQuery.data?.count ?? 0) > 0 && detailsQuery.isLoading);

  if (isLoading) {
    return <Skeleton className="h-[720px] rounded-3xl" />;
  }

  if (simulationsQuery.isError || detailsQuery.isError || buildingsQuery.isError) {
    return (
      <StateCard
        icon={PlayCircle}
        title="Unable to load simulation center"
        description="The simulation history or building catalog could not be read from the REST API."
      />
    );
  }

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Badge>Simulations</Badge>
        <h1 className="font-display text-4xl font-semibold">Simulation center</h1>
        <p className="max-w-3xl text-muted-foreground">
          Launch simulations through the REST API, compare outcomes, and pass a run
          directly into the report viewer.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[0.86fr_1.14fr]">
        <Card>
          <CardHeader>
            <CardTitle>Run Simulation</CardTitle>
            <CardDescription>
              Trigger the existing backend simulation endpoint from the product UI.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="building_id">
                  Building
                </label>
                <select
                  className="flex h-11 w-full rounded-2xl border border-slate-200 bg-white/80 px-4 text-sm text-slate-900 shadow-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 dark:border-slate-800 dark:bg-slate-950/70 dark:text-white"
                  id="building_id"
                  {...form.register("building_id")}
                >
                  <option value="">No building selected</option>
                  {buildings.map((building) => (
                    <option key={building.building_id} value={building.building_id}>
                      {building.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="idf_path">
                  IDF Path
                </label>
                <Input
                  id="idf_path"
                  {...form.register("idf_path")}
                  placeholder="C:/ecoloop/buildings/hq-office.idf"
                />
                {form.formState.errors.idf_path ? (
                  <p className="text-sm text-rose-600">
                    {form.formState.errors.idf_path.message}
                  </p>
                ) : null}
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="epw_path">
                  EPW Path
                </label>
                <Input
                  id="epw_path"
                  {...form.register("epw_path")}
                  placeholder="C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw"
                />
                {form.formState.errors.epw_path ? (
                  <p className="text-sm text-rose-600">
                    {form.formState.errors.epw_path.message}
                  </p>
                ) : null}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="timeout_seconds">
                    Timeout (s)
                  </label>
                  <Input
                    id="timeout_seconds"
                    type="number"
                    {...form.register("timeout_seconds")}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="parallel_jobs">
                    Parallel Jobs
                  </label>
                  <Input id="parallel_jobs" type="number" {...form.register("parallel_jobs")} />
                </div>
              </div>
              <Button disabled={runSimulationMutation.isPending} type="submit">
                {runSimulationMutation.isPending ? "Running..." : "Run Simulation"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardContent className="relative p-6">
              <Search className="pointer-events-none absolute left-10 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-10"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search simulations, buildings, or file paths..."
                value={search}
              />
            </CardContent>
          </Card>

          {filteredSimulations.length === 0 ? (
            <StateCard
              icon={PlayCircle}
              title="No simulation history yet"
              description="Run the first simulation through the form to populate the table and comparison workspace."
            />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Simulation History</CardTitle>
                <CardDescription>
                  Status, execution time, energy, comfort, and next actions.
                </CardDescription>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200/70 text-muted-foreground dark:border-slate-800">
                      <th className="py-3 pr-4 font-medium">Simulation</th>
                      <th className="py-3 pr-4 font-medium">Status</th>
                      <th className="py-3 pr-4 font-medium">Execution Time</th>
                      <th className="py-3 pr-4 font-medium">Energy</th>
                      <th className="py-3 pr-4 font-medium">Comfort</th>
                      <th className="py-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSimulations.map((simulation) => (
                      <tr
                        key={simulation.simulation_id}
                        className="border-b border-slate-200/60 align-top last:border-b-0 dark:border-slate-800/80"
                      >
                        <td className="py-4 pr-4">
                          <div className="space-y-1">
                            <p className="font-medium">{simulation.simulation_id.slice(0, 8)}</p>
                            <p className="text-muted-foreground">
                              {buildings.find((building) => building.building_id === simulation.building_id)
                                ?.name ?? "Unassigned"}
                            </p>
                          </div>
                        </td>
                        <td className="py-4 pr-4">
                          <Badge variant={statusVariant(simulation.final_status)}>
                            {simulation.final_status}
                          </Badge>
                        </td>
                        <td className="py-4 pr-4 text-muted-foreground">
                          {simulation.duration_ms ? `${simulation.duration_ms} ms` : "n/a"}
                        </td>
                        <td className="py-4 pr-4">
                          {formatCompactNumber(
                            simulation.result.metrics.energy?.total_site_energy_kwh ?? 0
                          )}{" "}
                          kWh
                        </td>
                        <td className="py-4 pr-4">
                          {(
                            100 -
                            (simulation.result.metrics.comfort?.average_ppd_percent ?? 100)
                          ).toFixed(1)}
                        </td>
                        <td className="py-4">
                          <div className="flex flex-wrap gap-2">
                            <Button
                              size="sm"
                              type="button"
                              variant="secondary"
                              onClick={() => setSelectedSimulationId(simulation.simulation_id)}
                            >
                              View
                            </Button>
                            <Button
                              size="sm"
                              type="button"
                              variant={
                                comparisonIds.includes(simulation.simulation_id)
                                  ? "accent"
                                  : "secondary"
                              }
                              onClick={() => toggleComparison(simulation.simulation_id)}
                            >
                              <Scale className="h-3.5 w-3.5" />
                              Compare
                            </Button>
                            <Button asChild size="sm" type="button" variant="secondary">
                              <Link
                                href={{
                                  pathname: "/reports",
                                  query: { simulationId: simulation.simulation_id }
                                }}
                              >
                                <FileText className="h-3.5 w-3.5" />
                                Generate Report
                              </Link>
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {selectedSimulation ? (
        <Card>
          <CardHeader>
            <CardTitle>Simulation Detail</CardTitle>
            <CardDescription>
              Current selection from the simulation history table.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-4">
            {[
              {
                label: "Total Site Energy",
                value: `${(
                  selectedSimulation.result.metrics.energy?.total_site_energy_kwh ?? 0
                ).toFixed(1)} kWh`
              },
              {
                label: "HVAC Energy",
                value: `${(
                  selectedSimulation.result.metrics.hvac?.hvac_energy_kwh ?? 0
                ).toFixed(1)} kWh`
              },
              {
                label: "Avg Temperature",
                value: `${(
                  selectedSimulation.result.metrics.comfort?.average_zone_temperature_celsius ?? 0
                ).toFixed(1)} deg C`
              },
              {
                label: "Diagnostics",
                value: String((selectedSimulation.result.diagnostics ?? []).length)
              }
            ].map((metric) => (
              <div
                key={metric.label}
                className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 dark:border-slate-800 dark:bg-slate-950/60"
              >
                <p className="text-sm text-muted-foreground">{metric.label}</p>
                <p className="mt-2 font-display text-2xl font-semibold">{metric.value}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {comparison ? (
        <Card>
          <CardHeader>
            <CardTitle>Simulation Comparison</CardTitle>
            <CardDescription>
              Comparing the two selected simulations from the history table.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            {[
              { label: "Energy Delta", value: `${comparison.energyDelta.toFixed(1)} kWh` },
              { label: "HVAC Delta", value: `${comparison.hvacDelta.toFixed(1)} kWh` },
              { label: "Comfort Delta", value: `${comparison.comfortDelta.toFixed(1)} PPD` }
            ].map((metric) => (
              <div
                key={metric.label}
                className="rounded-2xl border border-slate-200/70 bg-white/75 p-5 dark:border-slate-800 dark:bg-slate-950/60"
              >
                <p className="text-sm text-muted-foreground">{metric.label}</p>
                <p className="mt-3 font-display text-3xl font-semibold">{metric.value}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
