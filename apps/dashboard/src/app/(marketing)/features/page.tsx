import type { Metadata } from "next";

import { FeatureHighlightsPage } from "@/components/marketing/marketing-pages";

export const metadata: Metadata = {
  title: "Features | EcoLoop AI",
  description: "Explore the premium product and dashboard features of EcoLoop AI."
};

export default function FeaturesPage() {
  return <FeatureHighlightsPage />;
}
