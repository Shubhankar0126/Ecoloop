import type { Metadata } from "next";

import { BuildingsPage } from "@/components/workspace/buildings-page";

export const metadata: Metadata = {
  title: "Buildings | EcoLoop AI",
  description: "Manage building resources and baselines in EcoLoop AI."
};

export default function BuildingsRoute() {
  return <BuildingsPage />;
}
