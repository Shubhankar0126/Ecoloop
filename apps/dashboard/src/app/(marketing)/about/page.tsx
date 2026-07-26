import type { Metadata } from "next";

import { AboutStoryPage } from "@/components/marketing/marketing-pages";

export const metadata: Metadata = {
  title: "About | EcoLoop AI",
  description: "Learn about the mission and creator behind EcoLoop AI."
};

export default function AboutPage() {
  return <AboutStoryPage />;
}
