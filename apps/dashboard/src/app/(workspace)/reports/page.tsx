import type { Metadata } from "next";
import { Suspense } from "react";

import { ReportsPage } from "@/components/workspace/reports-page";

export const metadata: Metadata = {
  title: "Reports | EcoLoop AI",
  description: "Generate executive reports from recorded EcoLoop AI simulations."
};

export default function ReportsRoute() {
  return (
    <Suspense fallback={<div className="h-[720px] rounded-3xl bg-slate-100/70 dark:bg-slate-900/50" />}>
      <ReportsPage />
    </Suspense>
  );
}
