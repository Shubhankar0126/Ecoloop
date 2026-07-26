"use client";

import { Fragment, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bot,
  BrainCircuit,
  Building2,
  Network,
  PanelsTopLeft,
  ServerCog,
  type LucideIcon
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type ArchitectureNodeId =
  | "frontend"
  | "fastapi"
  | "ai-agent"
  | "mcp"
  | "simulation-service"
  | "energyplus";

type ArchitectureNode = {
  id: ArchitectureNodeId;
  label: string;
  icon: LucideIcon;
  summary: string;
  description: string;
  contract: string;
  boundary: string;
};

const architectureNodes: readonly ArchitectureNode[] = [
  {
    id: "frontend",
    label: "Frontend",
    icon: PanelsTopLeft,
    summary: "Premium Next.js marketing and workspace surfaces.",
    description:
      "Owns product presentation, dashboards, forms, charts, and executive storytelling while consuming only backend HTTP contracts.",
    contract: "Reads and writes through versioned REST APIs under /api/v1.",
    boundary: "Never talks directly to MCP, SimulationService, or EnergyPlus."
  },
  {
    id: "fastapi",
    label: "FastAPI",
    icon: ServerCog,
    summary: "Typed backend API and orchestration boundary.",
    description:
      "Accepts frontend requests, validates payloads, delegates to backend services, and preserves the clean architecture boundary already frozen in earlier sprints.",
    contract: "Exposes buildings, simulations, AI chat, reports, and health endpoints.",
    boundary: "Keeps HTTP concerns separate from simulation and AI internals."
  },
  {
    id: "ai-agent",
    label: "AI Agent",
    icon: BrainCircuit,
    summary: "LangGraph reasoning loop powered by Ollama and Qwen3.",
    description:
      "Plans, critiques, and iterates on optimization tasks without ever calling EnergyPlus directly. It acts through tool interfaces only.",
    contract: "Provides the intelligence behind the AI chat workflow and report guidance.",
    boundary: "Reaches the simulation platform only through MCP tools."
  },
  {
    id: "mcp",
    label: "MCP",
    icon: Network,
    summary: "Tool bridge between AI workflows and the simulation platform.",
    description:
      "Registers simulation-aware tools so agents, workers, and future distributed clients can trigger platform capabilities through a stable contract.",
    contract: "Exposes simulation, comparison, metrics, and validation tools.",
    boundary: "Remains framework-independent and does not own simulation execution itself."
  },
  {
    id: "simulation-service",
    label: "SimulationService",
    icon: Bot,
    summary: "Single public entry point into the EnergyPlus platform.",
    description:
      "Coordinates validation, execution, parsing, and result assembly so upstream callers never need to know EnergyPlus internals.",
    contract: "Accepts a simulation spec and returns a normalized simulation result.",
    boundary: "Owns orchestration only; raw simulation mechanics stay below this layer."
  },
  {
    id: "energyplus",
    label: "EnergyPlus",
    icon: Building2,
    summary: "The simulation execution engine and source of truth.",
    description:
      "Runs the real building simulation and produces the ERR, SQL, CSV, and other artifacts from which every dashboard metric is derived.",
    contract: "Consumes validated IDF and EPW inputs and generates real output artifacts.",
    boundary: "No fabricated metrics or bypassed execution paths are allowed here."
  }
] as const;

function ArchitectureConnection({ delay }: { delay: number }) {
  return (
    <div className="relative hidden lg:block lg:col-span-1">
      <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-slate-200/80 dark:bg-slate-800" />
      <motion.div
        className="absolute top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-teal-400 shadow-[0_0_20px_rgba(45,212,191,0.45)]"
        animate={{ x: ["0%", "calc(100% - 0.5rem)", "0%"], opacity: [0.45, 1, 0.45] }}
        transition={{
          duration: 4.2,
          ease: "easeInOut",
          repeat: Number.POSITIVE_INFINITY,
          delay
        }}
      />
    </div>
  );
}

export function ArchitectureDiagram({ className }: { className?: string }) {
  const [selectedId, setSelectedId] = useState<ArchitectureNodeId>("frontend");

  const selectedNode =
    architectureNodes.find((node) => node.id === selectedId) ?? architectureNodes[0];

  return (
    <div className={cn("grid gap-6 xl:grid-cols-[1.2fr_0.8fr]", className)}>
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[repeat(11,minmax(0,1fr))]">
          {architectureNodes.map((node, index) => {
            const isSelected = node.id === selectedId;

            return (
              <Fragment key={node.id}>
                <motion.button
                  type="button"
                  onClick={() => setSelectedId(node.id)}
                  onMouseEnter={() => setSelectedId(node.id)}
                  onFocus={() => setSelectedId(node.id)}
                  aria-pressed={isSelected}
                  className={cn(
                    "group rounded-[1.75rem] border border-slate-200/70 bg-white/85 p-5 text-left shadow-sm transition dark:border-slate-800 dark:bg-slate-950/70 lg:col-span-2",
                    isSelected
                      ? "border-primary/40 bg-primary/[0.08] shadow-[0_16px_40px_rgba(37,99,235,0.12)] dark:border-primary/30 dark:bg-primary/[0.12]"
                      : "hover:border-primary/25 hover:bg-white dark:hover:bg-slate-950"
                  )}
                  whileHover={{ y: -4 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="space-y-4">
                    <div
                      className={cn(
                        "flex h-11 w-11 items-center justify-center rounded-2xl text-primary transition",
                        isSelected
                          ? "bg-primary/15"
                          : "bg-slate-100 text-slate-700 group-hover:bg-primary/10 dark:bg-slate-900 dark:text-slate-200"
                      )}
                    >
                      <node.icon className="h-5 w-5" />
                    </div>
                    <div className="space-y-1">
                      <p className="font-display text-lg font-semibold">{node.label}</p>
                      <p className="text-sm text-muted-foreground">{node.summary}</p>
                    </div>
                  </div>
                </motion.button>
                {index < architectureNodes.length - 1 ? (
                  <ArchitectureConnection delay={index * 0.3} />
                ) : null}
              </Fragment>
            );
          })}
        </div>
        <p className="text-sm text-muted-foreground">
          Hover or select a component to inspect its responsibility, contract, and boundary.
        </p>
      </div>

      <Card className="relative overflow-hidden">
        <motion.div
          className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-500 via-teal-400 to-blue-500"
          animate={{ backgroundPositionX: ["0%", "100%", "0%"] }}
          transition={{ duration: 7, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
          style={{ backgroundSize: "220% 100%" }}
        />
        <CardHeader>
          <Badge>Interactive Architecture</Badge>
          <CardTitle>{selectedNode.label}</CardTitle>
          <CardDescription>{selectedNode.summary}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <AnimatePresence mode="wait">
            <motion.div
              key={selectedNode.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.22 }}
              className="space-y-5"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <selectedNode.icon className="h-5 w-5" />
              </div>
              <p className="text-sm leading-7 text-muted-foreground">{selectedNode.description}</p>
              <div className="grid gap-3">
                {[
                  { label: "Primary Contract", value: selectedNode.contract },
                  { label: "Boundary", value: selectedNode.boundary }
                ].map((item) => (
                  <div
                    key={item.label}
                    className="rounded-2xl border border-slate-200/70 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-950/60"
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
                      {item.label}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.value}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          </AnimatePresence>
        </CardContent>
      </Card>
    </div>
  );
}
