"use client";

import { useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Bot, LoaderCircle, MessageSquareDashed, Sparkles } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { StateCard } from "@/components/ui/state-card";
import { Textarea } from "@/components/ui/textarea";
import { useAiChatMutation, useSimulationDetailsQuery, useSimulationListQuery } from "@/hooks/use-ecoloop-api";

const aiSchema = z.object({
  objective: z.string().min(10, "Describe a meaningful optimization goal."),
  success_criteria: z.string().optional(),
  constraints: z.string().optional(),
  max_iterations: z.coerce.number().int().min(1).max(20).default(3)
});

type AiFormValues = z.infer<typeof aiSchema>;

function splitLines(value: string | undefined) {
  return (value ?? "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function AiPage() {
  const aiChatMutation = useAiChatMutation();
  const simulationsQuery = useSimulationListQuery();
  const detailsQuery = useSimulationDetailsQuery(simulationsQuery.data?.items);
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>(
    []
  );

  const form = useForm<AiFormValues>({
    resolver: zodResolver(aiSchema),
    defaultValues: {
      objective: "",
      success_criteria: "",
      constraints: "",
      max_iterations: 3
    }
  });

  const latestSimulation = useMemo(() => {
    const latestId = aiChatMutation.data?.latest_simulation_id;
    if (!latestId) {
      return null;
    }

    return (detailsQuery.data ?? []).find((simulation) => simulation.simulation_id === latestId) ?? null;
  }, [aiChatMutation.data?.latest_simulation_id, detailsQuery.data]);

  async function onSubmit(values: AiFormValues) {
    setMessages((current) => [...current, { role: "user", content: values.objective }]);

    const response = await aiChatMutation.mutateAsync({
      goal: {
        objective: values.objective,
        success_criteria: splitLines(values.success_criteria),
        constraints: splitLines(values.constraints)
      },
      conversation: [
        {
          role: "user",
          content: values.objective
        }
      ],
      previous_optimizations: [],
      max_iterations: values.max_iterations
    });

    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: response.report.executive_summary
      }
    ]);
  }

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <Badge>AI Assistant</Badge>
        <h1 className="font-display text-4xl font-semibold">Optimization co-pilot</h1>
        <p className="max-w-3xl text-muted-foreground">
          A ChatGPT-style interface for simulation-backed recommendations generated
          through the existing `POST /api/v1/ai/chat` endpoint.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="min-h-[680px]">
          <CardHeader>
            <CardTitle>Conversation</CardTitle>
            <CardDescription>
              Describe the goal, constraints, and success criteria for the AI assistant.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="objective">
                  Goal
                </label>
                <Textarea
                  id="objective"
                  {...form.register("objective")}
                  placeholder="Reduce cooling energy without degrading occupant comfort."
                />
                {form.formState.errors.objective ? (
                  <p className="text-sm text-rose-600">
                    {form.formState.errors.objective.message}
                  </p>
                ) : null}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="success_criteria">
                    Success Criteria
                  </label>
                  <Textarea
                    id="success_criteria"
                    {...form.register("success_criteria")}
                    placeholder={"Lower cooling energy by 5%\nKeep average PMV near neutral"}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium" htmlFor="constraints">
                    Constraints
                  </label>
                  <Textarea
                    id="constraints"
                    {...form.register("constraints")}
                    placeholder={"Do not modify weather data\nKeep occupancy assumptions unchanged"}
                  />
                </div>
              </div>
              <div className="space-y-2 md:max-w-44">
                <label className="text-sm font-medium" htmlFor="max_iterations">
                  Max Iterations
                </label>
                <Input id="max_iterations" type="number" {...form.register("max_iterations")} />
              </div>
              <Button disabled={aiChatMutation.isPending} type="submit">
                {aiChatMutation.isPending ? (
                  <>
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    Thinking...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Ask EcoLoop AI
                  </>
                )}
              </Button>
            </form>

            <div className="space-y-4 rounded-[1.8rem] border border-slate-200/70 bg-white/60 p-5 dark:border-slate-800 dark:bg-slate-950/50">
              {messages.length === 0 ? (
                <StateCard
                  icon={MessageSquareDashed}
                  title="No conversation yet"
                  description="Start with an optimization goal and the AI assistant will respond with an executive summary and next actions."
                />
              ) : (
                messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`max-w-[88%] rounded-3xl px-5 py-4 text-sm leading-7 ${
                      message.role === "user"
                        ? "ml-auto bg-primary text-primary-foreground"
                        : "bg-slate-100 text-slate-900 dark:bg-slate-900 dark:text-white"
                    }`}
                  >
                    {message.content}
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Recommendations</CardTitle>
              <CardDescription>
                Structured executive output from the most recent AI response.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {aiChatMutation.data ? (
                <div className="space-y-5">
                  <div className="rounded-3xl border border-slate-200/70 bg-white/75 p-5 dark:border-slate-800 dark:bg-slate-950/60">
                    <p className="font-display text-xl font-semibold">
                      {aiChatMutation.data.report.executive_summary}
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Goal achieved: {aiChatMutation.data.report.goal_achieved ? "Yes" : "No"}
                    </p>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-3xl border border-slate-200/70 bg-white/75 p-5 dark:border-slate-800 dark:bg-slate-950/60">
                      <p className="text-sm text-muted-foreground">Key Findings</p>
                      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">
                        {(aiChatMutation.data.report.key_findings ?? []).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-3xl border border-slate-200/70 bg-white/75 p-5 dark:border-slate-800 dark:bg-slate-950/60">
                      <p className="text-sm text-muted-foreground">Next Actions</p>
                      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">
                        {(aiChatMutation.data.report.next_actions ?? []).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ) : (
                <StateCard
                  icon={Bot}
                  title="Awaiting AI response"
                  description="Recommendations and executive summaries will appear here after the assistant completes a run."
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Simulation Results</CardTitle>
              <CardDescription>
                When the latest AI run maps to a recorded simulation, the key metrics appear here.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {latestSimulation ? (
                <div className="grid gap-4 md:grid-cols-2">
                  {[
                    {
                      label: "Simulation ID",
                      value: latestSimulation.simulation_id.slice(0, 8)
                    },
                    {
                      label: "Status",
                      value: latestSimulation.final_status
                    },
                    {
                      label: "Site Energy",
                      value: `${(
                        latestSimulation.result.metrics.energy?.total_site_energy_kwh ?? 0
                      ).toFixed(1)} kWh`
                    },
                    {
                      label: "Comfort Score",
                      value: `${(
                        100 -
                        (latestSimulation.result.metrics.comfort?.average_ppd_percent ?? 100)
                      ).toFixed(1)}`
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
                </div>
              ) : (
                <StateCard
                  icon={Sparkles}
                  title="No linked simulation in history"
                  description="AI-generated runs are shown here when a matching simulation is available in the recorded workspace history."
                />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
