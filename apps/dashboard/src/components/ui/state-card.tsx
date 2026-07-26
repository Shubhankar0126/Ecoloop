import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function StateCard({
  icon: Icon,
  title,
  description,
  action
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex min-h-56 flex-col items-center justify-center gap-4 text-center">
        <div className="rounded-full bg-primary/10 p-4 text-primary">
          <Icon className="h-6 w-6" />
        </div>
        <div className="space-y-2">
          <h3 className="font-display text-xl font-semibold">{title}</h3>
          <p className="max-w-md text-sm text-muted-foreground">{description}</p>
        </div>
        {action}
      </CardContent>
    </Card>
  );
}
