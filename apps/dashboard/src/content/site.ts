import type { Route } from "next";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bot,
  Building2,
  Cpu,
  Github,
  Leaf,
  LineChart,
  Linkedin,
  Mail,
  Network,
  Orbit,
  PanelsTopLeft,
  ServerCog,
  Sparkles,
  Wind
} from "lucide-react";

type NavigationItem = {
  href: Route;
  label: string;
};

type DeveloperContactConfig = {
  github: string;
  linkedin: string;
  email: string;
};

function optionalLink(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function optionalEmailLink(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return null;
  }

  return trimmed.startsWith("mailto:") ? trimmed : `mailto:${trimmed}`;
}

export const marketingNavigation = [
  { href: "/", label: "Home" },
  { href: "/features", label: "Features" },
  { href: "/architecture", label: "Architecture" },
  { href: "/ai", label: "AI" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/reports", label: "Reports" },
  { href: "/about", label: "About" }
] satisfies readonly NavigationItem[];

export const workspaceNavigation = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/buildings", label: "Buildings" },
  { href: "/simulations", label: "Simulations" },
  { href: "/ai", label: "AI Assistant" },
  { href: "/reports", label: "Reports" }
] satisfies readonly NavigationItem[];

export const demoRoute = "/demo" as const satisfies Route;

export const technologies: Array<{
  name: string;
  description: string;
  icon: LucideIcon;
}> = [
  { name: "EnergyPlus", description: "Trusted simulation engine.", icon: Building2 },
  { name: "LangGraph", description: "Multi-step planning and control loops.", icon: Orbit },
  { name: "MCP", description: "AI-callable operational tools.", icon: Network },
  { name: "Qwen3", description: "Reasoning model for optimization workflows.", icon: Sparkles },
  { name: "Ollama", description: "Local model serving foundation.", icon: Cpu },
  { name: "FastAPI", description: "Typed, production-grade backend APIs.", icon: ServerCog },
  { name: "Next.js", description: "Premium web experience and dashboard shell.", icon: PanelsTopLeft }
] as const;

export const valuePillars: Array<{
  title: string;
  description: string;
  icon: LucideIcon;
}> = [
  {
    title: "Reduce Energy Cost",
    description: "Use simulation-backed intelligence to discover lower-energy operating modes.",
    icon: LineChart
  },
  {
    title: "Increase Comfort",
    description: "Track occupant comfort alongside system efficiency instead of trading one for the other.",
    icon: Wind
  },
  {
    title: "Lower Carbon Footprint",
    description: "Translate performance gains into sustainability outcomes for executive reporting.",
    icon: Leaf
  },
  {
    title: "AI Decision Making",
    description: "Route planning, comparison, and recommendations through a dedicated AI workflow.",
    icon: Bot
  },
  {
    title: "Real-Time Analytics",
    description: "Turn simulation history into readable product dashboards and operational stories.",
    icon: Activity
  }
] as const;

export const featureGroups = [
  {
    eyebrow: "Simulation Platform",
    title: "Built around real EnergyPlus execution, not invented metrics.",
    description:
      "Every operational insight is sourced from actual simulation outputs, normalized through the platform you already froze in earlier sprints."
  },
  {
    eyebrow: "AI Workflow",
    title: "A deliberate planning loop instead of one-off prompts.",
    description:
      "The agent reasons through MCP tools, simulation feedback, and executive summaries before recommending actions."
  },
  {
    eyebrow: "Product Surface",
    title: "A modern SaaS experience for operators, engineers, and stakeholders.",
    description:
      "Marketing, analytics, reports, and AI guidance now live in one premium product shell with shared language and visual polish."
  }
] as const;

export type DeveloperLink = {
  label: string;
  href: string | null;
  icon: LucideIcon;
};

const developerContact: DeveloperContactConfig = {
  github: "",
  linkedin: "",
  email: ""
};

export const developerProfile = {
  name: "Shubhankar Pandey",
  title: "AI & ML Engineer",
  attribution: "Designed & Developed by Shubhankar Pandey",
  copyright: "\u00A9 2026 EcoLoop AI. All Rights Reserved.",
  contact: developerContact,
  links: [
    {
      label: "GitHub",
      href: optionalLink(developerContact.github),
      icon: Github
    },
    {
      label: "LinkedIn",
      href: optionalLink(developerContact.linkedin),
      icon: Linkedin
    },
    {
      label: "Email",
      href: optionalEmailLink(developerContact.email),
      icon: Mail
    }
  ] satisfies DeveloperLink[]
} as const;
