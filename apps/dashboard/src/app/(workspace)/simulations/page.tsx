import type { Metadata } from "next";

import { SimulationsPage } from "@/components/workspace/simulations-page";

export const metadata: Metadata = {
  title: "Simulations | EcoLoop AI",
  description: "Run and compare EnergyPlus simulations through the EcoLoop AI workspace."
};

export default function SimulationsRoute() {
  return <SimulationsPage />;
}
