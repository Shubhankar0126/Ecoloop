import "@testing-library/jest-dom/vitest";
import React from "react";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
    children?: React.ReactNode;
    href: string | { pathname: string; query?: Record<string, string> };
  }) => {
    const resolvedHref =
      typeof href === "string"
        ? href
        : `${href.pathname}${href.query ? `?${new URLSearchParams(href.query).toString()}` : ""}`;

    return React.createElement("a", { ...props, href: resolvedHref }, children);
  }
}));

vi.mock("next-themes", () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
  useTheme: () => ({
    resolvedTheme: "light",
    setTheme: vi.fn()
  })
}));

vi.mock("framer-motion", async () => {
  const actualReact = await import("react");

  const motion = new Proxy(
    {},
    {
      get: (_, tag: string) =>
        actualReact.forwardRef<HTMLElement, React.HTMLAttributes<HTMLElement>>(
          ({ children, ...props }, ref) =>
            actualReact.createElement(tag, { ...props, ref }, children)
        )
    }
  );

  return {
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => children,
    motion
  };
});

vi.mock("recharts", async () => {
  const actualReact = await import("react");

  function Container({
    children,
    ...props
  }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) {
    return actualReact.createElement("div", props, children);
  }

  function NullComponent() {
    return null;
  }

  return {
    ResponsiveContainer: Container,
    AreaChart: Container,
    BarChart: Container,
    Area: NullComponent,
    Bar: NullComponent,
    CartesianGrid: NullComponent,
    Tooltip: NullComponent,
    XAxis: NullComponent,
    YAxis: NullComponent
  };
});
