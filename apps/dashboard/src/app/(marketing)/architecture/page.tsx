import type { Metadata } from "next";

import { ArchitectureStoryPage } from "@/components/marketing/marketing-pages";

export const metadata: Metadata = {
  title: "Architecture | EcoLoop AI",
  description: "See how the frontend respects the frozen EcoLoop backend architecture."
};

export default function ArchitecturePage() {
  return <ArchitectureStoryPage />;
}
