"use client";

import { startTransition, useDeferredValue, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Building2, Filter, Search } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { Textarea } from "@/components/ui/textarea";
import {
  useBuildingDetailsQuery,
  useBuildingsQuery,
  useCreateBuildingMutation
} from "@/hooks/use-ecoloop-api";

const buildingSchema = z.object({
  name: z.string().min(2, "Building name is required."),
  description: z.string().optional(),
  timezone: z.string().optional(),
  baseline_idf_path: z.string().optional(),
  weather_file_path: z.string().optional(),
  metadata_lines: z.string().optional()
});

type BuildingFormValues = z.infer<typeof buildingSchema>;

function parseMetadata(lines: string | undefined) {
  return (lines ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce<Record<string, string>>((accumulator, line) => {
      const [key, ...valueParts] = line.split(":");
      if (!key || valueParts.length === 0) {
        return accumulator;
      }

      accumulator[key.trim()] = valueParts.join(":").trim();
      return accumulator;
    }, {});
}

function BuildingsSkeleton() {
  return (
    <div className="grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
      <Skeleton className="h-[520px] rounded-3xl" />
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-52 rounded-3xl" />
        ))}
      </div>
    </div>
  );
}

export function BuildingsPage() {
  const buildingsQuery = useBuildingsQuery();
  const createBuildingMutation = useCreateBuildingMutation();
  const [search, setSearch] = useState("");
  const [timezoneFilter, setTimezoneFilter] = useState("all");
  const [selectedBuildingId, setSelectedBuildingId] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search);
  const selectedBuildingQuery = useBuildingDetailsQuery(selectedBuildingId);

  const form = useForm<BuildingFormValues>({
    resolver: zodResolver(buildingSchema),
    defaultValues: {
      name: "",
      description: "",
      timezone: "",
      baseline_idf_path: "",
      weather_file_path: "",
      metadata_lines: ""
    }
  });

  const buildings = useMemo(() => buildingsQuery.data?.items ?? [], [buildingsQuery.data?.items]);
  const filteredBuildings = useMemo(() => {
    return buildings.filter((building) => {
      const matchesSearch =
        building.name.toLowerCase().includes(deferredSearch.toLowerCase()) ||
        (building.description ?? "").toLowerCase().includes(deferredSearch.toLowerCase());
      const matchesTimezone =
        timezoneFilter === "all" || (building.timezone ?? "unset") === timezoneFilter;
      return matchesSearch && matchesTimezone;
    });
  }, [buildings, deferredSearch, timezoneFilter]);

  const selectedBuildingSummary =
    buildingsQuery.data?.items.find((building) => building.building_id === selectedBuildingId) ??
    null;
  const selectedBuilding = selectedBuildingQuery.data ?? null;

  async function onSubmit(values: BuildingFormValues) {
    const response = await createBuildingMutation.mutateAsync({
      ...values,
      metadata: parseMetadata(values.metadata_lines)
    });
    form.reset();
    startTransition(() => {
      setSelectedBuildingId(response.building_id);
    });
  }

  const uniqueTimezones = [...new Set(buildings.map((building) => building.timezone ?? "unset"))];

  if (buildingsQuery.isLoading) {
    return <BuildingsSkeleton />;
  }

  if (buildingsQuery.isError) {
    return (
      <StateCard
        icon={Building2}
        title="Unable to load buildings"
        description="The building catalog could not be read from the existing backend API."
      />
    );
  }

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Badge>Buildings</Badge>
        <h1 className="font-display text-4xl font-semibold">Building management</h1>
        <p className="max-w-3xl text-muted-foreground">
          Create buildings through the REST API, search the portfolio, and inspect
          baseline file references before running simulations.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
        <Card>
          <CardHeader>
            <CardTitle>Create Building</CardTitle>
            <CardDescription>
              Add a building resource that the dashboard and simulation center can use.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="name">
                  Building Name
                </label>
                <Input id="name" {...form.register("name")} placeholder="HQ Office Tower" />
                {form.formState.errors.name ? (
                  <p className="text-sm text-rose-600">{form.formState.errors.name.message}</p>
                ) : null}
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="description">
                  Description
                </label>
                <Textarea
                  id="description"
                  {...form.register("description")}
                  placeholder="Primary office baseline for sustainability analysis."
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="timezone">
                    Timezone
                  </label>
                  <Input id="timezone" {...form.register("timezone")} placeholder="Asia/Kolkata" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="baseline_idf_path">
                    Baseline IDF Path
                  </label>
                  <Input
                    id="baseline_idf_path"
                    {...form.register("baseline_idf_path")}
                    placeholder="C:/ecoloop/buildings/hq-office.idf"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="weather_file_path">
                  Weather File Path
                </label>
                <Input
                  id="weather_file_path"
                  {...form.register("weather_file_path")}
                  placeholder="C:/ecoloop/weather/IND_Delhi.421820_IWEC.epw"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="metadata_lines">
                  Metadata
                </label>
                <Textarea
                  id="metadata_lines"
                  {...form.register("metadata_lines")}
                  placeholder={"portfolio: north-region\nbuilding_type: office"}
                />
              </div>
              <Button disabled={createBuildingMutation.isPending} type="submit">
                {createBuildingMutation.isPending ? "Creating..." : "Create Building"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardContent className="flex flex-col gap-4 p-6 md:flex-row md:items-center">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-10"
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search buildings..."
                  value={search}
                />
              </div>
              <div className="relative w-full md:w-64">
                <Filter className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <select
                  className="flex h-11 w-full rounded-2xl border border-slate-200 bg-white/80 pl-10 pr-4 text-sm text-slate-900 shadow-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 dark:border-slate-800 dark:bg-slate-950/70 dark:text-white"
                  onChange={(event) => setTimezoneFilter(event.target.value)}
                  value={timezoneFilter}
                >
                  <option value="all">All timezones</option>
                  {uniqueTimezones.map((timezone) => (
                    <option key={timezone} value={timezone}>
                      {timezone}
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          {filteredBuildings.length === 0 ? (
            <StateCard
              icon={Building2}
              title="No buildings found"
              description="Adjust the filters or create the first building to populate the workspace."
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredBuildings.map((building, index) => (
                <motion.button
                  key={building.building_id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: index * 0.04 }}
                  className="text-left"
                  onClick={() => setSelectedBuildingId(building.building_id)}
                  type="button"
                >
                  <Card className="h-full transition hover:-translate-y-1 hover:shadow-glow">
                    <CardContent className="space-y-4 p-6">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                          <Building2 className="h-5 w-5" />
                        </div>
                        <Badge variant="neutral">{building.simulation_count} sims</Badge>
                      </div>
                      <div className="space-y-2">
                        <p className="font-display text-xl font-semibold">{building.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {building.description ?? "No description provided."}
                        </p>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Timezone: {building.timezone ?? "Not set"}
                      </div>
                    </CardContent>
                  </Card>
                </motion.button>
              ))}
            </div>
          )}

          {selectedBuildingSummary ? (
            <Card>
              <CardHeader>
                <CardTitle>{selectedBuildingSummary.name}</CardTitle>
                <CardDescription>
                  Detail preview for the currently selected building resource.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                  <p className="text-sm text-muted-foreground">Timezone</p>
                  <p className="mt-2 font-medium">
                    {selectedBuildingSummary.timezone ?? "Not set"}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                  <p className="text-sm text-muted-foreground">Simulation Count</p>
                  <p className="mt-2 font-medium">{selectedBuildingSummary.simulation_count}</p>
                </div>
                <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                  <p className="text-sm text-muted-foreground">Baseline IDF</p>
                  <p className="mt-2 break-all font-medium">
                    {selectedBuildingQuery.isLoading
                      ? "Loading..."
                      : selectedBuilding?.baseline_idf_path ?? "Not set"}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                  <p className="text-sm text-muted-foreground">Weather File</p>
                  <p className="mt-2 break-all font-medium">
                    {selectedBuildingQuery.isLoading
                      ? "Loading..."
                      : selectedBuilding?.weather_file_path ?? "Not set"}
                  </p>
                </div>
              </CardContent>
              {selectedBuilding && Object.keys(selectedBuilding.metadata).length > 0 ? (
                <CardContent className="pt-0">
                  <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                    <p className="text-sm text-muted-foreground">Metadata</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {Object.entries(selectedBuilding.metadata).map(([key, value]) => (
                        <Badge key={key} variant="neutral">
                          {key}: {value}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardContent>
              ) : null}
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
