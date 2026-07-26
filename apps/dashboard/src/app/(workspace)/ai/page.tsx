import type { Metadata } from "next";

import { AiPage } from "@/components/workspace/ai-page";

export const metadata: Metadata = {
  title: "AI Assistant | EcoLoop AI",
  description: "Use the EcoLoop AI assistant for simulation-backed recommendations."
};

export default function AiRoute() {
  return <AiPage />;
}
