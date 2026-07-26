import type { Metadata } from "next";

import { DashboardPage } from "@/components/workspace/dashboard-page";

export const metadata: Metadata = {
  title: "Dashboard | EcoLoop AI",
  description: "Workspace overview for buildings, simulations, AI insights, and reporting."
};

export default function DashboardRoute() {
  return <DashboardPage />;
}
