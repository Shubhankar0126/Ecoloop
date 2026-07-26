"use client";

import { MoonStar, SunMedium } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <Button
      aria-label="Toggle theme"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      size="icon"
      variant="secondary"
      type="button"
    >
      {isDark ? <SunMedium className="h-5 w-5" /> : <MoonStar className="h-5 w-5" />}
    </Button>
  );
}
